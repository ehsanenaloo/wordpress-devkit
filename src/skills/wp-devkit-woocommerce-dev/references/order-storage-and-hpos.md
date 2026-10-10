# Order storage, HPOS and order queries

Contents: storage modes; compatibility declaration; reading and writing orders; querying orders; admin screens; synchronization and WP-CLI; large stores; test matrix; false positives.

Research date: 2026-10-08. Sources: [HPOS recipe book](https://developer.woocommerce.com/docs/features/high-performance-order-storage/recipe-book/), [HPOS overview](https://developer.woocommerce.com/docs/features/high-performance-order-storage/), [wc_get_orders() and order queries](https://developer.woocommerce.com/docs/features/orders/wc-get-orders/), WooCommerce source on GitHub (`CLIRunner.php`, `ListTable.php`, `OrdersTableDataStore.php`); re-check names against the installed version.

## Storage modes

| Option | Meaning |
|---|---|
| `woocommerce_custom_orders_table_enabled` = `yes` | HPOS tables (`wc_orders`, `wc_order_addresses`, `wc_order_operational_data`, `wc_orders_meta`) are authoritative. |
| `woocommerce_custom_orders_table_data_sync_enabled` = `yes` | Compatibility mode: writes are mirrored to the other store (`wp_posts`/`wp_postmeta`). |

HPOS is the default for new installs since WooCommerce 8.2 (Oct 2023); existing stores opt in at WooCommerce > Settings > Advanced > Features. Discover the live mode instead of assuming it: `wp option get woocommerce_custom_orders_table_enabled` and `wp wc hpos status`.

With HPOS authoritative and sync off, `wp_posts` holds only `shop_order_placehold` rows that reserve IDs. Code that reads `get_post_meta()` on an order then sees stale or no data, and code that calls `update_post_meta()` writes a record nobody reads. That is the real HPOS defect class. Sync mode can hide it in one environment and expose it in another.

## Declare compatibility (only after it is true)

```php
add_action( 'before_woocommerce_init', function () {
	if ( class_exists( \Automattic\WooCommerce\Utilities\FeaturesUtil::class ) ) {
		\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility( 'custom_order_tables', __FILE__, true );
	}
} );
```

- Put it in the main plugin file, or pass `'plugin-dir/plugin.php'` instead of `__FILE__` when declaring from elsewhere.
- Passing `false` declares incompatibility. The Plugins screen warning appears only for plugins that carry a `WC tested up to` header.
- A declaration is a claim, not evidence. Prove it with the test matrix below.
- The same function declares `'cart_checkout_blocks'` compatibility (see [checkout-blocks-and-store-api.md](checkout-blocks-and-store-api.md)).

## Read and write orders

| Legacy habit | Replacement |
|---|---|
| `get_post( $id )`, `get_post_type( $id ) === 'shop_order'` | `wc_get_order( $id )`; `OrderUtil::get_order_type( $id )`; `OrderUtil::is_order( $id, wc_get_order_types() )` |
| `get_post_meta` / `update_post_meta` / `delete_post_meta` on orders | `$order->get_meta()`, `update_meta_data()`, `add_meta_data()`, `delete_meta_data()`, then `$order->save()` |
| `wp_insert_post( [ 'post_type' => 'shop_order' ] )` | `wc_create_order()` or `new WC_Order()` plus setters and `save()` |
| `new WP_Query( [ 'post_type' => 'shop_order' ] )`, `get_posts` | `wc_get_orders()` / `WC_Order_Query` |
| `$wpdb->posts` joins for order data | CRUD getters; when SQL is unavoidable, `OrdersTableDataStore::get_orders_table_name()` and `get_meta_table_name()` instead of hard-coded `wp_wc_orders` |

```php
$order = wc_get_order( $order_id );
if ( ! $order instanceof WC_Order ) {
	return new WP_Error( 'devkit_missing_order', __( 'Order not found.', 'my-plugin' ) );
}
$order->update_meta_data( '_devkit_route_tag', sanitize_key( $tag ) );
$order->save();
```

- `save()` is relatively expensive. Batch setter calls into one save.
- In a hook that hands you an order that WooCommerce saves afterwards (classic `woocommerce_checkout_create_order`), set data on the passed object and do not save. Read the hook's docblock for each hook; do not assume.
- `save_meta_data()` persists meta only, not status or totals.
- `update_status( $status, $note )` runs transition hooks; `set_status()` alone does not persist. Use `payment_complete()` for paid orders ([payments-refunds-and-stock.md](payments-refunds-and-stock.md)).
- Compare values on a freshly loaded `wc_get_order( $id )`. The object you just modified always has the value.

Direct post-meta use on a non-order post type (a custom CPT linked to an order, products, coupons) is correct. Trace the object type before flagging.

## Query orders

```php
$orders = wc_get_orders( array(
	'limit'        => 100,
	'paged'        => $page,
	'return'       => 'ids',
	'status'       => array( 'wc-processing', 'wc-on-hold' ),
	'orderby'      => 'ID',
	'order'        => 'ASC',
	'date_created' => '2026-01-01...2026-01-31', // site timezone; timestamp forms are UTC
	'meta_query'   => array(
		array( 'key' => '_devkit_route_tag', 'value' => 'priority' ),
	),
) );
```

- Documented args: `status` (prefixed or not), `type` (`shop_order`, `shop_order_refund`), `customer`/`customer_id`, `parent`, `exclude`, `created_via`, `payment_method`, `currency`, `limit` (`-1` is unlimited), `paged`/`offset`, `return` (`objects` default, or `ids`), `paginate` (result object with `orders`, `total`, `max_num_pages`), `order`, `orderby` (`none`, `ID`, `name`, `type`, `rand`, `date`, `modified`), and date fields with `>`, `<`, `...` range syntax.
- `meta_query`, `field_query` (order properties that moved to columns) and `date_query` arrived in 8.2 and work only when HPOS is the configured store. Gate them on `OrderUtil::custom_orders_table_usage_is_enabled()` or test both modes. Prefer plain top-level args (`billing_email`, `total`) over `field_query` for simple equality.
- Meta-based `orderby` is not documented for `wc_get_orders`; do not assume `meta_key` ordering works.
- Custom query args: `woocommerce_order_query_args` is applied by `WC_Order_Query` before either data store runs. Store-specific SQL changes differ: HPOS uses `woocommerce_orders_table_query_clauses` (and `_query_sql`), the legacy store uses `woocommerce_order_data_store_cpt_get_orders_query`. Extending one store-specific filter silently breaks the other (see the hook names in the WooCommerce source).
- An unindexed `meta_query` scans `wc_orders_meta`. For a hot lookup prefer a first-class field (`transaction_id`, `customer_id`, `payment_method`) or an indexed table you own.

## Admin screens and metaboxes

- Screen id is `wc_get_page_screen_id( 'shop-order' )` under HPOS and `shop_order` on the legacy store. The metabox callback receives a `WC_Order` under HPOS and a `WP_Post` otherwise: `$order = $arg instanceof WP_Post ? wc_get_order( $arg->ID ) : $arg;`.
- List-table columns on HPOS use `manage_{$screen_id}_columns` and `manage_{$screen_id}_custom_column` (second argument is the `WC_Order`), where the screen id comes from `wc_get_page_screen_id( 'shop-order' )` (see `ListTable.php`; the recipe book itself does not name these hooks). The legacy `manage_edit-shop_order_columns` does not fire there. Custom list-table arguments go through `woocommerce_order_list_table_prepare_items_query_args`.
- A metabox save is an admin write path. Verify a nonce and `current_user_can( 'edit_shop_orders' )` (or the narrower capability) before `$order->save()`.

## Synchronization, migration and WP-CLI

From `CLIRunner.php`. `wp wc cot ...` is a deprecated alias since 8.9.0 and `verify_cot_data` became `verify_data` under `wc hpos`.

| Command | Purpose | Safe in review |
|---|---|---|
| `wp wc hpos status` | Enabled, sync and authoritative state | yes |
| `wp wc hpos count_unmigrated` | Orders awaiting sync | yes |
| `wp wc hpos verify_data --batch-size=500` | Compare HPOS rows with posts data | yes (read-only; record mismatches) |
| `wp wc hpos diff` | Differences for given orders | yes |
| `wp wc hpos compatibility-info` | Per-plugin compatibility info | yes |
| `wp wc hpos sync --batch-size=500` | Copy from the non-authoritative store | no, mutates |
| `wp wc hpos backfill` | Backfill selected properties | no |
| `wp wc hpos enable` / `disable` | Switch authoritative store | no; back up first |
| `wp wc hpos compatibility-mode enable|disable` | Toggle sync | no |
| `wp wc hpos cleanup <all|id|range>` | Remove redundant postmeta of migrated orders | no, destructive |

Documented rollback: enable compatibility mode, wait for sync to finish, select posts storage, then optionally disable compatibility mode; save between steps. Authoritative tables cannot be switched while orders are pending sync. A stalled scheduled sync restarts by re-saving the settings page with sync checked. Review never runs the mutating commands.

## Large stores

- Page with `limit` plus `paged` and `return => 'ids'`. Never `limit => -1` over a production orders table.
- Select the ID set before a repair job mutates it, or order by `ID` ascending and resume from the last processed ID. A job that filters on the value it changes skips records.
- Run bulk work in Action Scheduler batches, reload each order with `wc_get_order()`, and save once per order.
- Multisite: order tables are per site (`$wpdb->prefix`). Use the table-name helpers.

## Test matrix (regression proof)

Run the same assertions in (1) HPOS authoritative with sync on, (2) HPOS authoritative with sync off, (3) posts authoritative with sync off. In each: create an order through the real path (classic and Store API), mutate meta and status, reload via `wc_get_order()`, query via `wc_get_orders()`, refund. Passing mode (1) alone does not prove HPOS safety because the mirror can mask wrong-store reads. `wp wc hpos verify_data` passing proves the stores agree, not that your code uses CRUD.

## Looks wrong but is fine

- `get_post_meta()` on products, coupons or a custom CPT; `WP_Query` over `product`.
- The string `shop_order` as an argument to `wc_get_orders( [ 'type' => 'shop_order' ] )` or in a `wc_get_order_types()` comparison.
- A plugin that truthfully declares `false` for `custom_order_tables`.
- Postmeta reads in an explicit one-off migration script that targets legacy data by design.
