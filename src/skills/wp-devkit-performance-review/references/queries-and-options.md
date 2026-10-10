# Queries, metadata and options

Researched 2026-10-08. Contents: 1 WP_Query arguments | 2 N+1 and priming | 3 Meta, taxonomy and search queries | 4 Counting and pagination | 5 Autoload and options | 6 Indexes and custom tables | 7 Large data and multisite | 8 WooCommerce and HPOS | 9 Review checks

## 1. WP_Query arguments

Change arguments only when the consumer does not need what is dropped.

| Argument | Effect | Use when | Risk |
|---|---|---|---|
| `fields => 'ids'` | Returns IDs; no `WP_Post` objects built (`$posts` is not populated as objects) | Consumer needs only IDs | Follow-up `get_post()`/`get_post_meta()` per ID is the N+1 you tried to avoid; prime with `_prime_post_caches()` / `update_meta_cache( 'post', $ids )` |
| `no_found_rows => true` | Skips the total-row count (`SQL_CALC_FOUND_ROWS`/count query) | No pagination or total needed | `max_num_pages`/`found_posts` become unusable |
| `update_post_meta_cache => false` | Skips meta priming | Meta is not read | Later `get_post_meta` costs one query per post |
| `update_post_term_cache => false` | Skips term priming | Terms not read | Same for `get_the_terms` |
| `cache_results => false` | Do not cache the post objects | Rare; huge one-off scans to avoid cache churn | Slower repeated reads |
| `posts_per_page` bounded | Caps rows | Always for request paths | `-1` loads everything; batch instead |
| `ignore_sticky_posts => true` | Skips sticky logic | Non-blog lists | Changes results |
| `lazy_load_term_meta` | Defers term meta loading (default true) | Leave on | - |

`posts_per_page => -1` is acceptable for bounded taxonomies or batch jobs; on request paths over unbounded post types it is a finding when the dataset can grow. Use pagination or, for jobs, keyset batching: order by `ID`, remember the last ID, and select the next batch with a bounded `LIMIT` (see the migration skill for the stable-cursor pattern).

When changing arguments on the main query via `pre_get_posts`, check `$query->is_main_query()` and `! is_admin()`, then test search, archive, feed and pagination. Do not call `wp_reset_postdata()` forgetfully after secondary loops: template tags depend on `$post`.

## 2. N+1 and priming

Core primes caches in bulk in many places: `WP_Query` primes post and term and meta caches for the page of results; `get_posts()` too; `get_users()` primes user meta when `fields` need it; `WP_Term_Query` primes term meta. N+1 appears when you step outside those paths:

- Loop over IDs calling `get_post( $id )`, `get_post_meta( $id )`, `get_the_terms( $id, ... )`, `get_userdata()`, `wc_get_product()`, `get_permalink()` (which may load parents) on uncached objects.
- Per-row `$wpdb->get_var()` inside a loop.
- Per-item remote or `switch_to_blog()` work.

Fix by one bulk query plus priming: `_prime_post_caches( $ids, $update_term_cache, $update_meta_cache )` (no longer marked private since 6.1 per its docblock, but still underscore-prefixed: guard with `function_exists` if you support older versions), `update_meta_cache( 'post', $ids )` (public, since 2.9), `update_object_term_cache( $ids, $post_type )`, `cache_users( $ids )`, `wp_cache_get_multiple()` (5.5). Or restructure to a single `WP_Query` with `post__in` and `orderby => 'post__in'`.

Evidence: Query Monitor shows duplicate and per-caller query counts. Count queries before and after rather than reasoning from the loop.

## 3. Meta, taxonomy and search queries

- `meta_query` joins `wp_postmeta` once per clause; two or three `OR`/`AND` clauses on large meta tables multiply rows. `wp_postmeta` is indexed on `post_id` and `meta_key` only; comparisons on `meta_value` (`LIKE`, `CAST AS NUMERIC`, `BETWEEN`, ordering by `meta_value_num`) cannot use an index for the value. Cost scales with the number of rows per `meta_key`.
- Alternatives, ordered by effort: (1) narrow first with an indexed filter (post type, taxonomy, date), (2) store a denormalized, indexed value in a custom table or a taxonomy term for facets and booleans, (3) cache the result with correct invalidation, (4) move search to a dedicated engine (Elasticsearch/OpenSearch via ElasticPress-style integration).
- Orderby on meta in a paginated list: expect a full scan of matching rows plus filesort; verify with `EXPLAIN`.
- `tax_query` with many terms or `NOT IN`, nested relations, and `include_children` can produce expensive joins; check term counts. Prefer `post__in` from a precomputed ID list when facets are stable.
- `post__not_in` with a large array and `s` (core search uses `LIKE '%word%'` across title/excerpt/content): index-unfriendly by design; limit scope or use a search engine. Leading-wildcard `LIKE` on custom tables is the same.
- `WP_Query` `suppress_filters => true` skips `posts_*` filters and many plugins' query alterations: only use it when you know the filters are not needed (multilingual and access-control plugins use them).

## 4. Counting and pagination

- Counts: `wp_count_posts()` (cached, by status), `count_users()`, term counts (`wp_term_taxonomy.count`, maintained by core), `WP_Query` with `fields => 'ids'` and `found_posts` only when `no_found_rows` is false. `count( get_posts( ... -1 ) )` loads everything.
- Deep `OFFSET` pagination degrades linearly. For feeds and exports use keyset pagination with a cursor on an indexed unique column.
- `SQL_CALC_FOUND_ROWS` is deprecated as of MySQL 8.0.17 but core `WP_Query` has used it for found-row calculation; that is why `no_found_rows` matters on large tables. Read the query text in Query Monitor on the installed version rather than assuming how the count is done.

## 5. Autoload and options

- Options flagged for autoload are read in one query at bootstrap and held in the `alloptions` cache; their combined size is paid by every request, including REST, cron and AJAX. WordPress 6.6 Site Health reports a critical issue when autoloaded data exceeds 800 KB (filter `site_status_autoloaded_options_size_limit` changes the threshold). The Performance Lab plugin adds a detail table.
- WordPress 6.6 changed the `autoload` argument of `add_option()`/`update_option()`: the default is now `null` (core decides), `true`/`false` set it explicitly, and the legacy `'yes'`/`'no'` strings are deprecated as of 6.7. Stored values are `on`, `off`, `auto`, `auto-on`, `auto-off` (plus legacy `yes`/`no`); `wp_autoload_values_to_autoload()` returns the values treated as autoloaded (`yes`, `on`, `auto-on`, `auto` by default). Options not given an explicit value and larger than 150,000 bytes (filter `wp_max_autoloaded_option_size`) are no longer set to autoload. Do not hard-code `autoload = 'yes'` in SQL when auditing on 6.6+; use the function's value list.
- Audit SQL for 6.6+: `SELECT option_name, LENGTH(option_value) AS bytes FROM wp_options WHERE autoload IN ('yes','on','auto-on','auto') ORDER BY bytes DESC LIMIT 20;` On older versions the condition is `autoload = 'yes'`. WP-CLI: `wp option list --autoload=on --format=total_bytes`.
- Fix patterns: pass `false` for rarely used or large options when writing them; never store logs, queues, caches, big serialized arrays or license payloads in autoloaded options; use a custom table, transient, or a non-autoloaded option. Changing autoload of an existing option: `wp_set_option_autoload( $option, false )` (WordPress 6.4+, returns true when modified), run through a reviewed script on staging first; on older cores use `update_option()` with the autoload argument. Back up the option value before changing it.
- `update_option()` with an unchanged value performs no write; with changed values it writes and refreshes `alloptions`. Writing on every page view is a finding.
- Transient and cron data live in `wp_options` without a persistent object cache; orphaned expired transients accumulate. Core deletes expired ones inconsistently; `wp transient delete --expired` is the maintenance command. Transient names must be 172 characters or fewer.
- Serialized arrays that grow forever (append to option) are both a size and a concurrency (lost update) problem.

## 6. Indexes and custom tables

- Index for the query you run: equality columns first, then range, then sort; composite indexes can serve `WHERE a = ? AND b = ? ORDER BY c`. Verify with `EXPLAIN`; keep index length within engine limits (utf8mb4 on older row formats has a 191-character prefix limit for unique/indexed varchar).
- Adding an index on a large table is a migration with lock/time cost (see the migration skill); do not add indexes in the request path or on every `plugins_loaded`.
- Custom tables: define charset/collation from `$wpdb->get_charset_collate()`, primary key, and the indexes your queries need; avoid `LONGTEXT` JSON columns that you filter on.
- Beware `SELECT *` over wide tables, `ORDER BY RAND()`, `NOT IN (subquery)` on large sets, and functions on indexed columns (`WHERE DATE(created) = ...` cannot use the index; use ranges).

## 7. Large data and multisite

- Design for the 95th-percentile site: millions of postmeta rows, 100k+ users or orders, thousands of sites. Test with generated data (`wp post generate`, `wp user generate`, WooCommerce data generators or a sanitized production copy).
- User queries: `get_users()` without `number` loads everything; `search` with leading wildcard; capability filtering via usermeta is heavy. Use `number`, `fields`, and `count_total => false`.
- Multisite: `get_sites()` pages with `number`/`offset`; `wp_is_large_network()` flags large networks (core disables some expensive counts/lists then); `switch_to_blog()` is costly in loops because it resets and swaps caches; prefer a single SQL across blogs only via supported tables, or batch per site through a queue. Object-cache group names and keys include the blog ID; confirm `wp_cache_switch_to_blog()` behavior in the drop-in.

## 8. WooCommerce and HPOS

- Orders: use `wc_get_orders()` / `WC_Order_Query` and the CRUD API, not `get_posts( 'shop_order' )` or direct `wp_posts`/`wp_postmeta` SQL. With High-Performance Order Storage (default for new stores since WooCommerce 8.2) orders live in `wc_orders`, `wc_orders_meta` and related tables with purpose-built indexes; direct post-table queries return nothing or stale data when HPOS is authoritative.
- Declare HPOS compatibility with `FeaturesUtil::declare_compatibility( 'custom_order_tables', __FILE__, true )` on `before_woocommerce_init`; detect with `OrderUtil::custom_orders_table_usage_is_enabled()`.
- Products: avoid loading full product objects for lists where `wc_get_products( array( 'return' => 'ids' ) )` suffices; product meta lookup tables (`wc_product_meta_lookup`) back price and stock filters; avoid `meta_query` on `_price`/`_stock_status` when lookup-table APIs exist.
- Cart, checkout and account pages must bypass full-page caching; do not "fix" speed by caching them.
- Scheduled work in WooCommerce uses Action Scheduler: see the background reference.

## 9. Review checks

1. Result contract recorded (filters, order, visibility, pagination, totals) and unchanged by the fix.
2. Query count and time before/after on production-shaped data; `EXPLAIN` for the changed statement.
3. No unbounded query on a request path over a growing table.
4. Autoload set within budget; large values not autoloaded.
5. Passing does not prove: other parameter values, other tables' growth, or behavior under a different DB version.

Sources: [WP_Query](https://developer.wordpress.org/reference/classes/wp_query/) | [update_meta_cache](https://developer.wordpress.org/reference/functions/update_meta_cache/) | [Options API autoload (6.6)](https://make.wordpress.org/core/2024/06/18/options-api-disabling-autoload-for-large-options/) | [WP-CLI option list](https://developer.wordpress.org/cli/commands/option/list/) | [WooCommerce HPOS recipes](https://developer.woocommerce.com/docs/features/high-performance-order-storage/recipe-book/) | [WP-CLI profile](https://developer.wordpress.org/cli/commands/profile/). | [WP_Query source](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/class-wp-query.php) | [MySQL FOUND_ROWS deprecation](https://dev.mysql.com/doc/refman/8.0/en/information-functions.html) | [MySQL EXPLAIN ANALYZE](https://dev.mysql.com/doc/refman/8.0/en/explain.html)
