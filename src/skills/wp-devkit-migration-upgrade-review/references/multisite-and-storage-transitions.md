# Multisite, WooCommerce storage and serialized-data transitions

Research date: 2026-10-08. Contents: 1 Multisite upgrades | 2 New sites | 3 WooCommerce HPOS | 4 Serialized data and search-replace | 5 Options, meta and post-type changes | 6 Review checks

## 1. Multisite upgrades

- Per-site data (`$wpdb->prefix` tables, site options, post types) needs a per-site version marker; network-wide data (`$wpdb->base_prefix` tables, `*_site_option`) needs a network marker. A single marker for both lets one site skip another site's upgrade.
- Network-activated plugins load on every site; the lazy approach is to upgrade each site on its first request after the update (version gate per site). That spreads the cost but leaves unvisited sites unmigrated and cron/CLI contexts on old data: ensure code tolerates unmigrated sites or provide an explicit network runner.
- Explicit network runner: iterate `get_sites( array( 'number' => N, 'offset' => O, 'fields' => 'ids' ) )` in pages, `switch_to_blog( $id )`, run the idempotent step, `restore_current_blog()` in a `finally`, record per-site progress; for networks flagged by `wp_is_large_network()` use a queue, not one request. `switch_to_blog` resets and swaps caches; keep the number of switches proportionate.
- Core itself upgrades the network database with `wp core update-db --network` (WP-CLI) or the Network Admin upgrade screen; `--dry-run` compares versions without changing anything.
- Super admin versus site admin: a site administrator must not trigger or alter network-scope migrations.
- Test matrix: single site, network with 3 sites, subdirectory and subdomain, a site created after the update, an archived or deleted site (skipped), a site with a different prefix.

## 2. New sites

A site created after the plugin is installed needs the plugin's tables and defaults. Use `wp_initialize_site` (WordPress 5.1+, parameters `WP_Site $new_site, array $args`) to create the site's tables and defaults; the older `wpmu_new_blog` action is deprecated since 5.1.0 in favour of it (core still fires it for back-compat when a callback exists). Activation on the network runs `register_activation_hook` once with `$network_wide = true` and does not cover sites created later. On deletion, `wp_uninitialize_site` and `wp_delete_site` handle per-site cleanup; plugin tables in a deleted site's prefix are removed by core only for core tables, so a plugin should drop its own (`wp_uninitialize_site` or `wpmu_drop_tables` filter).

## 3. WooCommerce HPOS

- High-Performance Order Storage keeps orders in dedicated tables (`wc_orders` and related). It is enabled by default for new installations since WooCommerce 8.2; existing stores opt in. Legacy storage in `wp_posts` can still be selected. WooCommerce documents no removal date for legacy storage in the pages reviewed here: check the current developer documentation before stating one.
- Code must use the CRUD layer: `wc_get_order()`, `wc_get_orders()` / `WC_Order_Query`, `$order->get_meta()`, `$order->update_meta_data()` then `$order->save()`, and `OrderUtil` helpers (`OrderUtil::custom_orders_table_usage_is_enabled()`, `OrderUtil::get_order_type()`, `OrderUtil::is_order()`). Direct `wp_posts`/`wp_postmeta` SQL or `get_post_meta( $order_id )` returns wrong or stale data when HPOS is authoritative.
- Declare compatibility on `before_woocommerce_init` with `FeaturesUtil::declare_compatibility( 'custom_order_tables', __FILE__, true )` (guard with `class_exists`); declare `false` if not compatible. Admin screens differ (order edit screen ID via `wc_get_page_screen_id( 'shop-order' )`).
- Synchronization (compatibility mode) writes to both stores so plugins can transition. WP-CLI: `wp wc hpos status`, `wp wc hpos enable [--with-sync]`, `wp wc hpos disable` (refused while orders are pending sync), `wp wc hpos count_unmigrated`, `wp wc hpos sync`, `wp wc hpos verify_data` (`--re-migrate` can overwrite data), `wp wc hpos diff <order_id>`, `wp wc hpos backfill`, `wp wc hpos cleanup` (removes legacy order data; requires HPOS enabled and compatibility mode off). The `wp wc cot` namespace is deprecated since WooCommerce 8.9.0, and `verify_data` is the new name of `verify_cot_data` (WooCommerce `CLIRunner.php`). Check `--help` on the installed version.
- Large stores: enable sync, run `sync` until `count_unmigrated` is zero, run `verify_data`, soak, then disable sync gradually; interrupting the sync job is documented as safe; do not disable sync immediately after the job completes.
- Review migration code that touches orders: reads and writes via CRUD, tolerance of both storage modes, no assumption that the order ID is a post ID outside legacy mode, custom meta moved with `save()` once per flow (save is relatively expensive; batch changes).

## 4. Serialized data and search-replace

- PHP serialized strings store byte lengths (`s:5:"hello"`). Replacing text in the raw string changes the length and corrupts the value. Never use plain SQL `REPLACE()` or `sed` on a database dump for URL/domain changes where serialized data exists.
- Use `wp search-replace <old> <new>` (WP-CLI): it handles serialized data (PHP processing for columns containing it; `--precise` forces PHP for every column; `--recurse-objects` is on by default). Always `--dry-run` first and compare the report; `--skip-columns=guid` to leave GUIDs unchanged (post GUIDs are identifiers, not URLs to be rewritten); `--skip-tables` with wildcards; `--all-tables-with-prefix` or `--all-tables` for custom tables not registered with `$wpdb`; `--network` for multisite; `--regex` is much slower; `--export=file.sql` writes a transformed dump without touching the database. Primary keys are never changed and tables without a primary key are skipped.
- JSON stored in meta/options (block attributes, page builders) may contain escaped URLs (`https:\/\/`); search for both forms and verify by loading representative pages. Block comments in `post_content` contain JSON attributes: replace is safe for URLs but check for length-bounded fields.
- When writing custom replacement code: detect with `is_serialized()`, `unserialize` with `allowed_classes => false` unless required, replace recursively over arrays/objects values only (not keys unless intended), re-`serialize`, and compare round trips. Never unserialize untrusted data with classes enabled.
- Verification: count occurrences of the old string before and after (`wp db query "SELECT COUNT(*) FROM wp_options WHERE option_value LIKE '%old%'"`), load representative front-end and admin pages, and compare a sample of decoded values.

## 5. Options, meta and post-type changes

- Renaming an option: read old, write new, keep reading old as fallback until contract; `delete_option` later. `update_option` returns false when the value is unchanged (not an error).
- Renaming a meta key or moving it between objects: batch with a key predicate, keep both keys during overlap, and update registered meta (`register_post_meta`) and REST exposure.
- Changing a post type slug or taxonomy name: `UPDATE ... SET post_type` for rows, term relationships and rewrite rules; flush rewrite rules once (`flush_rewrite_rules()` after registration, never on every request); update capabilities, menus, widgets and block references; redirect old URLs.
- Changing the data format stored in `post_content` (block markup, shortcodes): provide a validator that reports unconvertible posts; keep a revision; test the editor loading converted content.
- Changing roles/capabilities: `add_role`/`remove_role` writes to the database once per role (`wp_user_roles` option); run on version change, not every request; capability removal needs verification that no user loses access unintentionally.
- Uninstall and data retention: `uninstall.php` (guard with `WP_UNINSTALL_PLUGIN`) or `register_uninstall_hook` removes data when the plugin is deleted, not on deactivation; on multisite deleting per-site data across all sites in one request is expensive; provide a "keep data" setting and honor it.

## 6. Review checks

1. Per-site vs network markers; new-site initialization; context restoration on every path.
2. Orders accessed through CRUD and compatible with both storages; HPOS declaration present; sync and verification plan for existing stores.
3. No raw replace on serialized data; dry-run and verification queries listed.
4. Old and new names co-exist until contract; rewrite rules flushed once.
5. Regression: multisite fixture with a late-created site; HPOS on and off (and sync on) with a representative order and custom meta; serialized option containing the old URL still unserializes correctly after replacement.
6. A pass does not prove behavior with third-party plugins that read the same data or with very large networks and stores.

Sources: [wp search-replace](https://developer.wordpress.org/cli/commands/search-replace/) | [wp core update-db](https://developer.wordpress.org/cli/commands/core/update-db/) | [wp_initialize_site](https://developer.wordpress.org/reference/hooks/wp_initialize_site/) | [HPOS overview](https://developer.woocommerce.com/docs/features/high-performance-order-storage/) | [HPOS recipe book](https://developer.woocommerce.com/docs/features/high-performance-order-storage/recipe-book/) | [HPOS CLI tools](https://developer.woocommerce.com/docs/features/high-performance-order-storage/cli-tools/) | [Uninstall methods](https://developer.wordpress.org/plugins/plugin-basics/uninstall-methods/).
