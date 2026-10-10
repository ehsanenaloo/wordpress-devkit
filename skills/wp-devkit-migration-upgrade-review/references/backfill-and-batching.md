# Backfills, batching and resumable runners

Research date: 2026-10-08. Contents: 1 Selection and cursor | 2 Batch bounds | 3 Idempotency and conflicts | 4 Checkpoints and completion | 5 Concurrency control | 6 Runners | 7 Invalid and unexpected data | 8 Verification | 9 Review checks

## 1. Selection and cursor

Define eligibility (which rows need work), the stable ordering key and an upper bound captured at start (max ID or timestamp) so rows created during the run are handled by the new write path, not by the backfill.

- Cursor on a unique, indexed, monotonic key: `WHERE id > %d AND id <= %d ORDER BY id ASC LIMIT %d`. Persist the last processed `id`.
- Offset paging (`LIMIT 500 OFFSET n`, `paged`) is wrong when the batch changes whether rows remain eligible (they drop out and the next page skips survivors) and gets slower as the offset grows. It is acceptable for read-only passes over a frozen set.
- For posts, order by `ID`; do not order by `post_modified` or other columns the batch itself updates.
- Re-run safety: a second pass over the same range must be a no-op.

```php
$last = (int) get_option( 'acme_backfill_last_id', 0 );
$ids  = $wpdb->get_col( $wpdb->prepare(
	"SELECT ID FROM {$wpdb->posts} WHERE post_type = %s AND ID > %d AND ID <= %d ORDER BY ID ASC LIMIT %d",
	'acme_item', $last, $max_id, $batch_size
) );
```

## 2. Batch bounds

Bound by rows and by time (stop when `microtime( true ) - $start > $budget`) and by memory (`memory_get_usage()` against `WP_MEMORY_LIMIT`). Typical starting points: a few hundred rows per batch for light updates, tens for heavy ones; tune from measured duration and lock time, not from rules of thumb. Keep each batch's transaction short (InnoDB): long transactions hold locks and bloat undo. In long loops free memory: avoid accumulating results, call `wp_cache_flush_runtime()` (6.0+) between batches in CLI so the in-memory object cache does not grow, and avoid `SAVEQUERIES`.

Write through APIs only when their side effects are wanted: `wp_update_post()` fires hooks, revisions and modified timestamps, and other plugins react; direct SQL or `update_post_meta` avoids that but also bypasses validation and caches (clean caches: `clean_post_cache( $id )`). State which one the migration uses and why. Suspend noisy hooks deliberately (for example `wp_defer_term_counting( true )`) and restore them.

## 3. Idempotency and conflicts

- Each row operation computes the new value from the old row and the mapping, and skips rows already in the target form (`WHERE new_col IS NULL`, or check a marker meta). Use `UPDATE ... WHERE id = X AND new_col IS NULL` so a concurrent user edit that set the new value is not overwritten.
- Writes that race with user edits: decide the winner (user edit wins), and use conditional updates or compare-and-set with the original value.
- Non-idempotent side effects (emails, API calls, counters incremented) must not live in the loop, or must be guarded by a per-row "done" marker written atomically with the data change.
- Deleting source data is the last step and optional until verification passes.

## 4. Checkpoints and completion

- Checkpoint = last committed key, written after the batch's writes are durable. Checkpoint before commit lets a crash skip rows; checkpoint after is safe only with idempotent rows.
- Checkpoint is not completion. Completion is: no eligible rows remain (query returns zero), the verification queries pass, and only then the version marker moves. Record progress counters (processed, skipped, failed) for the report.
- Where to store state: an option (non-autoload) for small state; a custom table for per-row status in very large jobs. Avoid one serialized option that rewrites a growing array each batch.
- Failures: record failed IDs with reason in a table or log, continue or stop per policy, and never mark success while failures remain unexplained. A failing batch retried forever is a backlog, so cap attempts.

## 5. Concurrency control

Several requests can trigger the same upgrade; cron and CLI can overlap. Use one runner at a time: an atomic claim with owner token and expiry, such as a unique-key row, `add_option( 'acme_migrate_lock', $owner, '', false )` (fails if it exists; store the timestamp and treat stale locks by expiry), or MySQL `GET_LOCK( name, timeout )` on a dedicated connection. Release only if you still own it; do not delete a successor's lock after your own expiry. Object-cache-based locks are not authoritative if the cache can evict. If two workers must exist, partition ranges so they cannot overlap.

## 6. Runners

- WP-CLI: best for large volumes (no web time limits, controllable memory): a `WP_CLI::add_command` with `--batch-size`, `--dry-run`, `--resume`, progress bar (`\WP_CLI\Utils\make_progress_bar`), and exit codes. Provide a `--dry-run` that counts and samples without writing.
- Action Scheduler or WP-Cron: one action per batch that schedules the next only after success (chained), with unique args, retry limits and visible failure state. WP-Cron timing is best-effort and events can overlap (see the performance background reference).
- Web request: only for small data; show progress in admin, enforce a time budget, and keep old behavior working until done.
- Always make the new code tolerate partially migrated data until the verification step passes (reads fall back to the old representation).

## 7. Invalid and unexpected data

Real data contains nulls, empty strings, malformed serialized values, orphaned rows, rows from deleted plugins, mixed encodings and values from older versions. Do not substitute empty or default values merely to finish a batch. For each unparsable row: log the ID and reason, leave the source untouched, and report counts for domain decision. Serialized/JSON handling: attempt a strict parse (`is_serialized()`, `json_decode( ..., true )` with `JSON_ERROR_NONE` check); `unserialize` untrusted historical data with `allowed_classes => false` unless classes are required (see the security skill).

## 8. Verification

Compare before and after with queries that do not rely on the migration code: row counts per status, `COUNT(*) WHERE new IS NULL AND old IS NOT NULL` equals zero, checksum or sampled equality between source and target mapping (`SELECT MD5(GROUP_CONCAT(...))` on a bounded range), related-record integrity (orphans, duplicates), and a few real records inspected manually. Run verification both before the switch and after a soak period. For order data under HPOS use the WooCommerce verification command (multisite and storage reference).

## 9. Review checks

1. Stable cursor, upper bound, idempotent rows, conditional updates.
2. Time/row/memory bounds and a short transaction per batch.
3. Checkpoint after durable work; completion defined independently of the checkpoint.
4. Single runner enforced; stale-lock recovery defined.
5. Invalid rows reported, not erased; no destructive step before verification.
6. Dry run and progress reporting exist; the runner works from WP-CLI.
7. Regression: interrupt mid-run and resume; run twice; two workers; row edited during backfill; malformed row. A pass on small fixtures does not prove production timing or lock behavior; rehearse on a production-sized copy.

Sources: [dbDelta and plugin tables](https://developer.wordpress.org/plugins/creating-tables-with-plugins/) | [Action Scheduler performance](https://actionscheduler.org/perf/) | [WP-CLI commands cookbook](https://make.wordpress.org/cli/handbook/guides/commands-cookbook/) | [WP_Object_Cache](https://developer.wordpress.org/reference/classes/wp_object_cache/).
