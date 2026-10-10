# Meta queries, storage cost and field migrations

Contents: what the meta tables can and cannot do; meta_query rules; alternatives when a query is hot; renaming and moving fields; backfill script pattern; rollback and verification; false positives.

Researched 2026-10-08. Sources: WordPress core `wp-admin/includes/schema.php` and `class-wp-meta-query.php` (master, 7.2-alpha), [WP_Query](https://developer.wordpress.org/reference/classes/wp_query/), [ACF update_field](https://www.advancedcustomfields.com/resources/update_field/), [ACF Repeater](https://www.advancedcustomfields.com/resources/repeater/), [WP-CLI handbook](https://make.wordpress.org/cli/handbook/).

## What the tables give you

`wp_postmeta` has `meta_id`, `post_id`, `meta_key varchar(255)`, `meta_value longtext`, with indexes on `post_id` and on `meta_key` (prefix length only). `meta_value` is not indexed. A `meta_query` therefore joins `postmeta` per clause and filters unindexed long text. `termmeta`, `usermeta` and `commentmeta` have the same shape.

Consequences for ACF-driven data:

- Each `meta_query` clause is another self-join. Several clauses plus a meta `orderby` on a large `post_type` is the typical slow archive.
- The default meta `type` is `CHAR`, so comparisons are string comparisons: `'10' < '9'`. Numeric, date and decimal comparisons need `'type' => 'NUMERIC' | 'DECIMAL(10,2)' | 'DATE' | 'DATETIME' | 'SIGNED' | 'UNSIGNED'`. Casting disables index use on the value anyway.
- Dates must be stored in a sortable form. ACF Date Picker always stores `Ymd` (for example `20261008`; [Date Picker docs](https://www.advancedcustomfields.com/resources/date-picker/)), which sorts correctly as a string and as a number; Date Time Picker always stores `Y-m-d H:i:s` ([docs](https://www.advancedcustomfields.com/resources/date-time-picker/)); a field with a custom save format, or mixed formats from imports, breaks range queries. Check the stored value (`wp post meta get <id> <name>`), not the displayed one.
- Booleans/true-false store `1`/`0`; an unset value may mean "no meta row". Query with `EXISTS`/`NOT EXISTS` deliberately.
- Repeater and flexible-content sub-values are separate meta rows with indexed names (`rows_0_title`). Matching them needs wildcard keys or `LIKE`, which cannot use the key index and cannot express "same row" constraints. Serialized arrays (multi-select, checkbox, relationship fields storing arrays) match with `LIKE '"123"'` patterns that can match unrelated values. Treat these queries as functional and performance risks, not features.
- Relationship fields store IDs (single or serialized/multiple). "Which posts reference X" via `LIKE` is slow and can false-match; maintain a reverse index (taxonomy, a lookup table, or a second meta key) when that query is core to the product.

## Review a query

1. Find the page or endpoint and its traffic. A meta query on a low-traffic admin report is not the same as one on a category page.
2. Count participating posts (`wp post list --post_type=x --format=count`) and meta rows (`SELECT COUNT(*) FROM wp_postmeta WHERE meta_key = '...'` on a staging copy; use `$wpdb->postmeta` table names when scripting).
3. Capture the SQL (Query Monitor, `SAVEQUERIES` on staging) and `EXPLAIN` it. Note rows examined and whether a filesort/temporary table appears.
4. Check key presence, type casts, formats and whether `NOT EXISTS` clauses are being used on large sets.
5. Report impact with numbers where available; otherwise report "unmeasured".

## Alternatives when the query is hot or the set is large

| Need | Option | Trade-off |
|---|---|---|
| Filter by a shared category | Taxonomy | Indexed relationships; needs term management |
| Single-value numeric/date sort at scale | Dedicated column in a custom table, or a denormalized scalar meta key kept in sync on `acf/save_post` | Write-time maintenance; migration |
| Faceted search | Search service or custom index table | Operational cost |
| Expensive aggregated view | Cache the assembled result (transient with persistent object cache, invalidated on save) | Staleness policy; transients without an object cache hit the options table |
| One-off reporting | WP-CLI/SQL on a replica | Not for request time |

Do not move data out of meta without a consumer inventory. Tables you create need `dbDelta`, uninstall handling, multisite per-site prefixes and backups.

## Renaming or moving a field (the safe sequence)

Renaming a field name in the ACF UI does not move stored values. The old meta key remains and the new name reads nothing. Sequence:

1. Add the new field (new name, final key) alongside the old; deploy it with the JSON/PHP schema.
2. Backfill raw values from old to new, including the reference meta `_newname` = new field key. Use the new field key so formatting works.
3. Dual-read in templates (`get_field( 'new' ) ?: get_field( 'old' )`) until backfill is verified, if deployment is not atomic.
4. Switch writers to the new field; verify; remove the old field after one release.
5. Delete old meta only after verification and a backup (`wp post meta delete` per post, or a documented SQL on a snapshot).

Repeater/flexible renames also need the row-count meta and every `{old}_{i}_{sub}` key (and their references). Prefer reading with ACF (`get_field( 'old', $id, false )` for nested raw arrays) and writing with `update_field( 'field_new', $rows, $id )` rather than hand-copying meta keys; it rebuilds row meta and references correctly.

## Backfill script pattern (idempotent, resumable, dry-run by default)

```php
if ( defined( 'WP_CLI' ) && WP_CLI ) {
	WP_CLI::add_command( 'site-schema backfill-capacity', static function ( $args, $assoc ) {
		global $wpdb;
		$apply = isset( $assoc['apply'] );
		$size  = max( 1, (int) ( $assoc['batch-size'] ?? 200 ) );
		$last  = (int) ( $assoc['after-id'] ?? 0 );          // resume cursor
		$seen = $copied = $skipped = 0;

		do {
			$ids = $wpdb->get_col( $wpdb->prepare(
				"SELECT DISTINCT post_id FROM {$wpdb->postmeta} WHERE meta_key = %s AND post_id > %d ORDER BY post_id ASC LIMIT %d",
				'old_capacity', $last, $size
			) );
			foreach ( $ids as $post_id ) {
				$last = (int) $post_id;
				++$seen;
				if ( metadata_exists( 'post', $post_id, 'event_capacity' ) ) {
					++$skipped;                               // idempotent
					continue;
				}
				$raw = get_post_meta( $post_id, 'old_capacity', true );
				if ( $apply ) {
					update_field( 'field_65a1b2c3d4e5f', absint( $raw ), $post_id );
				}
				++$copied;
			}
			WP_CLI::log( sprintf( 'last_id=%d seen=%d copied=%d skipped=%d', $last, $seen, $copied, $skipped ) );
			if ( function_exists( 'wp_cache_flush_runtime' ) ) {
				wp_cache_flush_runtime();                     // keep memory flat in long runs
			}
		} while ( $ids );

		WP_CLI::success( ( $apply ? 'Applied' : 'Dry run' ) . ": copied={$copied} skipped={$skipped}" );
	} );
}
```

Properties to keep: dry run unless `--apply`; cursor on the immutable ID; skip rows already migrated; no `LIMIT -1`; log progress and the resume ID; run on staging first; take a database backup before `--apply` in production; run per site on multisite (`wp --url=... site-schema ...`, or `wp site list --field=url | xargs -I% wp --url=% ...`). `wp_cache_flush_runtime()` exists since WordPress 6.0.0 ([reference](https://developer.wordpress.org/reference/functions/wp_cache_flush_runtime/)).

## Verify and roll back

- Counts: rows with old key, rows with new key, rows with both and different values (expect 0 after verification). Sample 20 posts through the rendered page and through REST.
- Rollback before old-key deletion: switch readers back to the old key; the old data is intact. After deletion the rollback is a restore from backup; state this in the change plan.
- Pass criteria prove the sampled rows and counts. They do not prove that other consumers (feeds, exports, search index, GraphQL schema) were updated; list those and check each.

## Looks wrong but is fine

- A `meta_query` with one indexed-by-key equality clause on a small post type.
- `LIKE` on serialized data in a one-time migration or admin-only tool.
- `get_post_meta( $id, 'old', true )` raw reads in a migration script.
- Unformatted `get_field( ..., false )` in code that deliberately compares stored values.
