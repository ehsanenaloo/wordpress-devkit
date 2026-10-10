# Scoped commands and operational recovery workbook

Contents: establish the behavior; decision checkpoints; symptom triage; worked decisions; looks wrong but is fine; severity guidance; verification; optional fixture; sources.

Apply [the engineering contract](engineering-contract.md) before classifying a concern. Deep topics: `command-authoring.md`, `search-replace-and-migrations.md`, `multisite-and-batch-operations.md`, `environment-safety-and-recovery.md`.

## Establish the behavior

Record: explicit environment (path, URL, alias), WP-CLI/PHP/WordPress versions (`wp --info`), command synopsis, selected tables/IDs/sites, write effects, whether the bootstrap is trusted, and recovery requirements (backup, window, rollback). Reviews inspect files and config only; they never run the command.

## Decision checkpoints

| Decision | What changes the answer |
|---|---|
| Target identity | Flags, aliases, config files in effect and DB prefix decide what is touched; verify with facts that differ per environment. |
| Operation class | Inventory vs diagnostic-with-effects (`cron event run`, `cache flush`, `eval`) vs reversible vs irreversible mutation. |
| Preview and backup | Check `wp help` for the installed flag set; dry run has zero side effects; backup is verified by restoring, not by existing. |
| Batches and failures | Validated bounds, keyed cursor with fixed upper bound, per-write and per-query error handling, truthful totals and exit status. |
| Context and repeatability | Site context restored on every path; checkpoint is not a lock or snapshot; define resume and conflict policy. |
| Recovery and delivery | Independent verification, restore rehearsal for data-loss risk, redacted logs, runbook. |
| Trust boundary | OS access is the CLI boundary; browser nonces are not required; add user policy only if promised. |

## Symptom triage

| Symptom | Evidence to gather | Action after confirmation |
|---|---|---|
| Command affected the wrong site/environment | `--path`/`--url`, alias, inherited `wp-cli.yml`, table scope | Stop; restore from backup if data changed; rerun with explicit flags. |
| Serialized data corrupted | Whether raw SQL `REPLACE` or a non-serialization-aware tool was used | Restore; redo with `wp search-replace`. |
| Old URLs remain after a move | Escaped-slash JSON, theme/config constants | Check counts; on older WP-CLI a second pass with the escaped form (newer search-replace also handles JSON-encoded strings); fix constants; verify counts. |
| Job exits 0 though some items failed | Warnings vs errors, unchecked write returns | Fail with counts. |
| Resume misses changed rows | Cursor type, upper bound, concurrent writers | Keyed cursor; reconcile unresolved rows. |
| Cron jobs stuck / late | `wp cron event list`, `DISABLE_WP_CRON`, system cron presence | Run due events from system cron; avoid overlapping runs with a lock. |
| Slowdown after "cache clear" | `wp cache flush` on shared Redis | Targeted invalidation, warm-up plan. |
| Every `wp` command fatals | Plugin/theme error | `--skip-plugins --skip-themes`, bisect. |

## Worked decisions

Documentation examples only; run nothing against an untrusted target.

### 1. Domain replacement without scope or preview

Problem: `wp search-replace old.example new.example --all-tables` touches every table in the database (also other applications' tables) including `guid`, with no preview.

Better:

```sh
wp search-replace 'old.example' 'new.example' --path=/srv/site --url=https://old.example \
  --all-tables-with-prefix --skip-columns=guid --dry-run --report-changed-only
```

Then, after a verified backup and review, the same command without `--dry-run`. On multisite add `--network` deliberately; `--all-tables-with-prefix` can still include other subsites' tables, so narrow to explicit tables when only one site moves. Verification: export and count remaining occurrences, test sample URLs, admin login, and a restore rehearsal for risky moves.

### 2. Maintenance command with truthful exit status

A batch command that logs a warning on each failed `update_post_meta` and ends with `WP_CLI::success()` hides data loss. Fix: count failures; after the loop `WP_CLI::error( sprintf( '%d of %d failed', $failed, $total ) )` (non-zero exit). Regression: simulate a write failure with a filter on `update_post_metadata` returning false; assert non-zero exit and exact counts.

### 3. Multisite loop that leaves the wrong site active

`switch_to_blog()` without `finally` and an early `WP_CLI::error()` inside leaves later logic on the wrong site (or aborts mid-loop with partial work). Fix: `try/finally { restore_current_blog(); }` or one process per site via `--url`. Regression: inject a failure on the second site and assert the first site's result, the failure report and the final blog ID.

### 4. Resumable job misses rows

`LIMIT 100 OFFSET n` over rows being deleted/updated by the job skips every other batch. Fix: `WHERE ID > cursor AND ID <= upper ORDER BY ID LIMIT n`, checkpoint after the verified batch. Regression: run, kill mid-way, resume; compare processed set with expected set; add rows during the run and document whether they are reconciled.

### 5. Trusted local command without nonce (benign)

A command that deletes expired exports and has no nonce or capability check is not a vulnerability: the actor already has shell access. Review instead its scope, dry run, exit codes and logging. Add a capability check only if the command's contract says it acts as a WordPress user.

### 6. `wp eval` in a runbook (needs scrutiny, not automatic finding)

`wp eval 'delete_option("x");'` in a runbook is an irreversible-class command written as a one-liner: check the target, the quoting (shell expansion of `$` and quotes in the PHP string), who approves it and how it is undone. Prefer a reviewed `eval-file` or a real command.

## Looks wrong but is fine

- `--skip-columns=guid` in URL moves (intentional).
- `--all-tables-with-prefix` with `--dry-run`.
- A command with no WordPress user check.
- Flags like `--yes` in CI where scope is fully specified and tested.
- `wp cron event run --due-now` from system cron (documented, overlapping runs guarded by the `doing_cron` transient).
- A progress or inventory command that loads WordPress, in a trusted environment.

## Severity guidance

CRITICAL: a default-reachable path that can destroy or corrupt production data (unscoped replace/reset/delete without backup or preview, raw SQL replace of serialized data, mutation without target confirmation in an automation that can reach production). WARNING: dry run with side effects, exit status that hides failures, offset pagination over mutating data, missing locks on overlapping jobs, unrestored site context, flush with large blast radius. INFO: output formatting, naming. Use candidate/insufficient evidence when the target, WP-CLI version or backup state is unknown.

## Verify the outcome

- Malformed arguments fail before any write; dry run writes nothing (compare rows, options, cache keys before and after).
- Empty data succeeds; database, write and cache failures exit non-zero with counts; interruption resumes within the declared policy.
- Selected multisite and table scope verified from the log and the data.
- Backup restored on a scratch database when loss is possible.

A pass proves the tested versions, fixtures and scope; it does not prove behavior on production data volume, concurrent writers, other WP-CLI versions or object-cache backends.

## Optional fixture

[operations-cache-prime-fixture.php](operations-cache-prime-fixture.php)

The fixture registers `wp devkit-fixture report-warmup`. It validates a batch size from 1 to 1000, uses a stable ID cursor and an initial upper bound, and stops on database and cache errors. Its dry run writes no cache entries. It is not resumable and is not a snapshot of concurrent edits. Entries survive the process only with a persistent object cache. Load it only in an inspected disposable WordPress environment; the skill never loads it automatically.

## Delivery evidence

Explain the practical result, changed owner and remaining limits. Separate confirmed findings, candidates, executed and unexecuted checks. Do not claim successful operations from source review.

## Sources

Research date: 2026-10-08.

- Search-replace: https://developer.wordpress.org/cli/commands/search-replace/
- Commands cookbook: https://make.wordpress.org/cli/handbook/guides/commands-cookbook/
- Config reference: https://make.wordpress.org/cli/handbook/references/config/
- Command reference pages cited in the four topic references (db, cron, cache, site, plugin, maintenance-mode).
