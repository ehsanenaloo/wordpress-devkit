---
name: wp-devkit-migration-upgrade-review
description: "Plan, debug, implement or review WordPress schema and data upgrades: dbDelta tables, versioned migrations, batched backfills, partial failures, multisite and HPOS transitions, search-replace, PHP/WordPress version upgrades and rollback readiness."
---

# Data transition and recoverable upgrades

Read `references/engineering-contract.md` first. A review request is read-only: inspect code, schema and plans; do not run migrations, backfills, search-replace or restores, and do not touch live data. Implement only when the user authorizes changes, and run migrations only on a disposable copy.

Hand off: WP-CLI runbook mechanics to `wp-devkit-wpcli-and-ops`; plugin activation/hook lifecycle design to `wp-devkit-plugin-development`; WooCommerce order API details to `wp-devkit-woocommerce-dev`; release pipeline and rollback of packages to `wp-devkit-ci-cd-and-release-engineering`; query speed of the backfill to `wp-devkit-performance-review`.

## Inputs

Current and target schema/data versions, the data owner and authoritative storage, supported old/new code overlap (rolling deploy, auto-updates, multiple web nodes), row volume and growth, database engine and version, multisite scope, existing runner and checkpoints, and a verified backup/restore path with a known restore time. If any is missing, list it as an assumption; do not guess volume.

## Code Review Workflow

1. State the invariant: what must be true of the data after migration, and the old and new representations. Identify authoritative storage, site scope, concurrent writers and readers (old code, new code, WP-CLI, cron, REST).
2. Find the trigger and the completion marker. Activation hooks do not run on ordinary updates; the update path must compare a stored version on a hook that runs for updates (typically `plugins_loaded` or `init`) and also covers manual, auto-update and multisite paths. Record the version only after the invariant holds.
3. Check schema changes: additive and compatible during overlap, `dbDelta` formatting, resulting indexes/types, engine behavior, lock time on the real table size. DDL commits implicitly in MySQL/MariaDB, so a transaction wrapper is not rollback.
4. Check the backfill: stable selection and cursor, bounded batch by rows and time, resumability, idempotency, behavior when eligibility changes during the run, treatment of invalid historic values, concurrency control (lock with owner/expiry), progress persisted after committed work.
5. Check cutover and recovery: dual read/write or compatible reads until verified; verification queries (counts, checksums, sampled values); what restoring old code does (nothing to data); backup/restore rehearsal; contract phase deferred to a later release.
6. Check scope: multisite (per-site vs network), HPOS vs legacy order storage, serialized data, uninstall behavior, and the supported WordPress/PHP range.
7. Report findings with a reproduction on a disposable dataset where possible; otherwise classify as candidate with the missing evidence.

Read `references/migration-upgrade-review-workbook.md` for severity, the finding template, false positives and acceptance checks.

## Implementation workflow

1. Write the invariant, the stages (expand, backfill, verify, switch, contract), the rollback plan and the verification queries before code.
2. Implement one stage per release when old and new code overlap. Version-gate on a stored schema version; keep the runner idempotent and resumable.
3. Test on a disposable database: fresh install, upgrade from each supported previous version, repeated run, interruption before and after checkpoint, two concurrent workers, invalid historic rows, multisite, and a real restore.
4. Provide a dry-run or count-only mode and a progress report. Use WP-CLI for large volumes; web-request migrations need hard time budgets.
5. Never destructively contract (drop column/table/option) in the same release as the switch. Report unavailable checks as unexecuted. Production execution is a separate, explicitly authorized task.

## Search Patterns for Quick Detection

Read-only leads from the first-party root; candidates, not findings. Exit codes: 0 match, 1 none, 2 error.

```sh
scan() { rg -n -g '*.{php,sql,sh,ps1,md}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e "$1" "${2:-.}"; }
scan 'db_version|schema_version|get_option\(\s*.[a-z_]*version|version_compare|register_activation_hook|upgrader_process_complete|plugins_loaded'   # triggers, version gates
scan 'dbDelta|ALTER\s+TABLE|CREATE\s+(UNIQUE\s+)?(INDEX|TABLE)|DROP\s+(TABLE|COLUMN|INDEX)|START\s+TRANSACTION|ROLLBACK'   # schema operations
scan 'checkpoint|cursor|last_id|offset|LIMIT\s+\d|batch|chunk|as_(schedule|enqueue)|wp_schedule_(single_)?event'   # backfills, batches
scan 'search-replace|maybe_unserialize|unserialize\(|serialize\(|str_replace|preg_replace|json_decode'   # serialized-data handling
scan 'switch_to_blog|restore_current_blog|is_multisite|get_sites|wpmu_new_blog|wp_initialize_site|wc_get_orders?|shop_order|wc_orders|custom_orders_table|OrderUtil'   # scope and storage
scan 'backup|restore|rollback|retry|GET_LOCK|add_option\(|delete_option|update_option|uninstall|register_uninstall_hook'   # recovery, locks, cleanup
```

Typical benign hits: `register_activation_hook` alongside a separate version-gated update path, `ALTER TABLE` inside a reviewed one-off runner with a checkpoint, `offset` in a read-only report.

## Task-selected resources

- `references/schema-and-dbdelta.md`: dbDelta rules and limits, collation, indexes, online DDL cost, schema versions, expand/contract. Read for any table or column change.
- `references/backfill-and-batching.md`: cursors, batch sizing, idempotency, locks, checkpoints, verification, Action Scheduler and WP-CLI runners. Read for data rewrites and large tables.
- `references/multisite-and-storage-transitions.md`: network vs site upgrades, new-site hooks, HPOS migration, serialized data and search-replace, option/meta/post-type changes. Read when scope is multisite, WooCommerce orders or URL/domain changes.
- `references/platform-upgrades-and-rollback.md`: WordPress/PHP/MySQL version upgrades, auto-update rollback limits, backups and restore drills, uninstall and downgrade policy. Read for upgrade planning and recovery.

## Output Format

Lead with the verdict and reviewed scope. Per finding: severity, `file:line`, trigger (install, update, manual run, multisite, concurrent worker), failure path, data impact, confidence, minimal remediation and a regression. Separate candidates and missing evidence. List executed checks (command, exit status) and unexecuted ones (production-size run, real restore, concurrent workers). For implementation, add stages, verification queries and results, and rollback instructions. "Code can be rolled back" is never a data-recovery claim.
