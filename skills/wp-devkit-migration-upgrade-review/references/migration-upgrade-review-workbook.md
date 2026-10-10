# Migration and upgrade review workbook

Apply [the engineering contract](engineering-contract.md) first.

Contents: 1 Invariant and stages | 2 Severity | 3 Finding template | 4 Symptom to cause | 5 Looks wrong but is fine | 6 Looks fine but is wrong | 7 Worked sketch | 8 Acceptance checks | 9 Sources

## 1. Invariant and stages

Write three lines before judging anything: (a) the old representation, (b) the new representation, (c) the invariant that must hold after migration (for example "every row with `legacy_status` has `status` mapped by table T; no row has both empty"). A migration with no stated invariant cannot be verified.

Safe order for changes with overlapping code versions (rolling deploy, auto-update, several nodes):

1. Expand: add schema/options that old and new code tolerate.
2. Deploy code that writes both (or reads new with fallback to old).
3. Backfill existing data in bounded, resumable batches.
4. Verify with counts and sampled values; fix exceptions through the domain's rules.
5. Switch reads to the new representation.
6. Contract (drop old column/option) in a later, separately authorized release after a retention window.

A single-step migration (rename column, rewrite format, drop old) is acceptable only when there is no overlap, the data is small or the downtime is accepted, and a tested restore exists.

## 2. Severity

| Demonstrated impact | Severity |
|---|---|
| Irreversible data loss or corruption on a supported path (destructive step before verification, serialized data broken by naive replace, backfill overwrites newer data, version marked complete before work succeeded and never re-run), fatal on activation/update of a supported site, wrong-site writes on multisite | CRITICAL |
| Upgrade never runs on ordinary update, restart skips or duplicates rows, concurrent workers corrupt state, lock or DDL time makes the site unavailable at realistic volume, no tested restore for a destructive step | WARNING |
| Missing progress output, style, avoidable but safe inefficiency | INFO |

Impact is judged on the worst supported path (largest table, oldest supported version, multisite, rolling deploy), not the demo site.

## 3. Finding template

```text
[SEVERITY][confidence: reproduced|traced|candidate] Short title
Location : path/file.php:LINE (trigger) and LINE (failing step)
Scenario : starting version -> target version, data shape, volume, topology
Trigger  : install | ordinary update | auto-update | manual run | multisite | concurrent worker | interruption
Failure  : what is skipped, duplicated, overwritten, lost or left half-done
Impact   : data affected, reversibility, who notices and when
Evidence : what was run on a disposable copy; what was NOT run
Fix      : minimal change, stage affected
Regression: fixture and expected final state (counts, checksums, version marker)
```

## 4. Symptom to cause

| Symptom | Evidence | Action after confirmation |
|---|---|---|
| Upgrade never runs on update | Stored version option; which hook compares it; plugin updated via auto-update/FTP | Move the version gate to a hook that runs on every request type that can load the plugin; keep activation for install-only work |
| Fatal after update, site down | Error log at first request after file replacement; old code still resident in the update request | Make the first-run path self-contained; keep old and new schema compatible; test update from each supported version |
| Restart skips rows | Cursor vs predicate; whether rows leave the eligible set | Cursor on a stable key (`ID > last_id`), not offset |
| Restart duplicates effects | Non-idempotent writes; checkpoint saved before commit | Make each row operation idempotent; save checkpoint after durable success |
| Two workers overwrite | Lock mechanics; read-modify-write | Atomic claim (unique row, `GET_LOCK`, `add_option`) with owner and expiry |
| Site slow or locked during release | DDL on large table, long transaction, metadata lock | Online DDL algorithm, off-peak, batch via CLI; see schema reference |
| Serialized values corrupt after URL change | Raw SQL `REPLACE` on serialized strings | Serialization-aware replace (`wp search-replace`), dry run first |
| Rolled back code, data still wrong | Destructive writes not reversed | Restore data from backup; keep additive state until verified |
| Works on single site, breaks on network | `switch_to_blog` balance; network vs site options | Iterate sites in batches with restoration; per-site version markers |
| Orders missing after change | Direct post-table queries under HPOS | Use WooCommerce CRUD/query APIs |

## 5. Looks wrong but is fine

- `register_activation_hook` present without an update path: fine if the schema is created only at install and later changes go through a version-gated updater that exists elsewhere. Missing activation hook while a `plugins_loaded` version check exists is also fine.
- Offset-based paging over a stable, read-only set (a report or an export that does not change eligibility).
- `START TRANSACTION` around DML-only batches on InnoDB tables: valid; the DDL-in-transaction claim applies only to DDL.
- `dbDelta()` run on every `plugins_loaded` guarded by a version check: normal; unguarded, it is a performance finding, not a data-safety one.
- Dropping a temporary or cache table created by the same plugin version.
- `ALTER TABLE ... ADD COLUMN` on a table of a few thousand rows.
- Direct SQL on a custom table the plugin owns.
- `delete_option` of the plugin's own options in `uninstall.php` (not in deactivation).
- Backfill that skips rows by design (documented eligibility rule) and logs them.

## 6. Looks fine but is wrong

- Completion marker updated at the start or after a loop that swallows errors.
- Batch loop `while ( $rows = get_posts( paged ) )` that updates the field it filters on: rows drop out and offset pages skip survivors.
- Checkpoint stored as the last offset instead of the last committed key.
- `dbDelta()` expected to drop columns, rename columns, or convert data; it only creates tables and adds columns/indexes.
- Default value silently substituted for unparsable historic data (data erasure without a record).
- `maybe_unserialize` then `str_replace` then `serialize`, which breaks string-length prefixes in nested objects when done by hand.
- Migration run on `admin_init` for administrators only: front-end requests, cron and REST run new code against unmigrated data.
- Long migration inside an HTTP request relying on `set_time_limit`.
- `uninstall.php` that drops data on plugin deletion while a documented "keep my data" setting is ignored.
- Idempotency claimed because "the option is checked", but two requests pass the check simultaneously.

## 7. Worked sketch

Operation order for a version-gated runner (not a replacement for the project's runner):

```text
on plugins_loaded:
  if stored_version >= TARGET: return
  if not acquire_lock(owner, ttl): return        # atomic; owner token; expiry
  try:
    expand_schema()                               # additive, idempotent
    loop: batch = next_batch(after_id = checkpoint, limit = N, time_budget)
          apply(batch)                            # idempotent per row
          save checkpoint = last committed id
    verify_invariant()                            # counts / sampled values
    set stored_version = TARGET                   # only now
  finally: release_lock(owner)
```

A failure at any step leaves `stored_version` unchanged, so the next request resumes. Contract steps are separate releases.

## 8. Acceptance checks

| Check | Method | Passing proves | Does NOT prove |
|---|---|---|---|
| Fresh install | Install target version on empty DB | Target schema correct | Upgrade path |
| Upgrade matrix | Restore a fixture at each supported previous version, upgrade | Final state matches invariant | Production-sized volume |
| Repeat run | Run twice | Idempotent | Concurrency |
| Interrupt | Kill after N rows, before/after checkpoint; resume | Resume safe | Crash during DDL |
| Concurrency | Two workers on the same data | Lock/claim works | Behavior under extreme load |
| Invalid historic rows | Fixture with nulls, malformed serialized data, orphan rows | Exceptions recorded, none erased | Unknown shapes |
| Multisite | 3 sites + network activation + new site creation | Scoped correctly | Very large networks |
| Verification queries | Counts, checksums, sampled values | Invariant on that data | Hidden edge cases |
| Restore rehearsal | `wp db export` then import to an isolated DB, compare | Backup usable, restore time known | Backups taken later |

Record commands, WordPress/PHP/DB versions, fixtures and exit status. Production execution is not part of a review.

## 9. Sources

Research date: 2026-10-08. [Creating tables with plugins](https://developer.wordpress.org/plugins/creating-tables-with-plugins/) | [dbDelta](https://developer.wordpress.org/reference/functions/dbdelta/) | [MySQL implicit commit](https://dev.mysql.com/doc/refman/8.0/en/implicit-commit.html) | [InnoDB online DDL](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) | [upgrader_process_complete](https://developer.wordpress.org/reference/hooks/upgrader_process_complete/). | [WooCommerce HPOS CLI source](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/src/Database/Migrations/CustomOrderTable/CLIRunner.php) | [core wpdb](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/class-wpdb.php) | [GET_LOCK](https://dev.mysql.com/doc/refman/8.0/en/locking-functions.html)
