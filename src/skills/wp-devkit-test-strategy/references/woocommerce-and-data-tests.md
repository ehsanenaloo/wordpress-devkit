# WooCommerce and data-heavy tests

Contents: [HPOS storage matrix](#hpos-storage-matrix) - [Order and stock invariants](#order-and-stock-invariants) - [Webhooks and gateways](#webhooks-and-gateways) - [Checkout paths](#checkout-paths) - [Background jobs and Action Scheduler](#background-jobs-and-action-scheduler) - [Migrations and large data](#migrations-and-large-data) - [Caching and multisite](#caching-and-multisite) - [Privacy and GDPR](#privacy-and-gdpr) - [Sources and unverified items](#sources-and-unverified-items)

Applies when the code reads or writes orders, products, stock, subscriptions, customers or any large table. Pair with `wp-devkit-woocommerce-dev` for domain correctness.

## HPOS storage matrix

High-Performance Order Storage (custom order tables) is the default for new WooCommerce installs since 8.2 and is controlled by options `woocommerce_custom_orders_table_enabled` (HPOS authoritative) and `woocommerce_custom_orders_table_data_sync_enabled` (compatibility mode: synchronize posts and order tables). Stores in the field run in three modes, and a plugin that touches orders needs a test for each it claims to support:

| Mode | Authority | Sync | What breaks |
| --- | --- | --- | --- |
| Legacy | posts/postmeta | off | Code using HPOS-only APIs |
| HPOS with sync | order tables | on | Code that writes to posts directly and is overwritten, or reads stale posts data |
| HPOS without sync | order tables | off | Anything that uses `get_post()`, `get_post_meta()`, `WP_Query` on `shop_order`, or raw SQL against `wp_posts` for orders |

Mechanics:

- Declare support only after auditing: `FeaturesUtil::declare_compatibility( 'custom_order_tables', __FILE__, true )` inside a `before_woocommerce_init` callback, guarded by `class_exists( '\Automattic\WooCommerce\Utilities\FeaturesUtil' )`. A static test can assert the declaration; the matrix proves the claim.
- Use order CRUD only: `wc_create_order()`, `wc_get_order()`, `$order->update_meta_data()`, `$order->save()`, `wc_get_orders()`. Branch raw SQL with `OrderUtil::custom_orders_table_usage_is_enabled()`.
- Switch modes in the test bootstrap, not inside a running test, so every test in a run sees one mode. Filtering `pre_option_*` is simple; confirm in your WooCommerce version that the data store is selected after the filter is added (add it in `muplugins_loaded`, before WooCommerce loads):

```php
<?php
// tests/bootstrap.php excerpt: choose storage mode for the whole run.
$hpos = getenv( 'WC_TEST_HPOS' ); // 'legacy', 'hpos-sync' or 'hpos'.
tests_add_filter(
	'muplugins_loaded',
	static function () use ( $hpos ) {
		if ( 'legacy' !== $hpos ) {
			add_filter( 'pre_option_woocommerce_custom_orders_table_enabled', static fn() => 'yes' );
			add_filter(
				'pre_option_woocommerce_custom_orders_table_data_sync_enabled',
				static fn() => 'hpos-sync' === $hpos ? 'yes' : 'no'
			);
		}
	},
	1
);
```

Run the suite once per mode in the CI matrix and assert the active mode at the start of the run (`OrderUtil::custom_orders_table_usage_is_enabled()`) so a misconfigured job cannot pass silently. WooCommerce's own test helpers differ by version; if you prefer them, read the installed version first.

## Order and stock invariants

- Create orders through CRUD with fixtures that include line items, taxes, shipping, coupons, refunds and a guest customer; assert totals after `calculate_totals()`.
- Status transitions: assert side effects of `woocommerce_order_status_changed` exactly once (email, stock reduction, license issue), including `pending` to `processing` to `completed` and `cancelled`/`refunded` reversals.
- Stock: reduction once per order, restock on cancel/refund, backorders, variable products. The last unit under two simultaneous checkouts needs a concurrency test (separate processes), not a sequential one.
- Refund replay: processing the same refund request twice must not refund twice.
- Currency and rounding: test with a zero-decimal currency and with tax-inclusive prices.

## Webhooks and gateways

Each inbound webhook route needs these tests, using recorded or hand-built payloads and never real credentials:

1. Valid signature accepted and effect applied once.
2. Missing, malformed and wrong signature rejected with no effect and no secret in the log.
3. Replay of the same event id is a no-op (idempotent).
4. Out-of-order events (refund before capture) end in a consistent order status.
5. Amount or currency mismatch against the order is rejected.
6. Gateway timeout or 5xx on the outbound call leaves the order in a recoverable state and is retried or flagged, not silently marked paid.

Mock the outbound HTTP with `pre_http_request` (see [wordpress-test-recipes.md](wordpress-test-recipes.md)); run provider sandbox tests in a separate, secrets-protected job. A mocked gateway proves your handling of the provider's documented responses, not the provider.

## Checkout paths

The classic shortcode checkout and the block-based Checkout (Store API under `wc/store/v1`) are different code paths. Cover each the store uses: validation messages, required fields added by filters, shipping method change recalculation, coupon failure, payment failure retry, double-click on Place order, session expiry. Browser tests live in [browser-and-e2e-tests.md](browser-and-e2e-tests.md); keep the logic-level cases at the integration layer.

## Background jobs and Action Scheduler

- Assert scheduling with `as_has_scheduled_action( $hook, $args, $group )` or `as_get_scheduled_actions()`; run the callback directly rather than waiting for the queue runner.
- Cases: duplicate scheduling prevented (unique), failure marks the action failed and is visible, retry limit, batch continues from a cursor, long-running action respects time/memory budget, job cleans up its own group.
- `as_has_scheduled_action( $hook, $args, $group )` (since Action Scheduler 3.3.0) and `as_get_scheduled_actions( $args, $return_format )` are documented at actionscheduler.org/api; confirm against the installed Action Scheduler version (bundled with WooCommerce).

## Migrations and large data

- Seed realistic volume where the behavior depends on it (WP-CLI `wp post generate`, a factory loop, or SQL fixtures). Assert bounded queries rather than elapsed time: count queries with `$wpdb->num_queries` or `SAVEQUERIES` before and after and fail when a per-item query appears (N+1).
- Backfill and upgrade routines: sparse and deleted ids, empty table, batch-size boundaries (n-1, n, n+1), resume from a checkpoint after interruption between write and checkpoint, two workers running at once, rerun after success, restore from backup then rerun.
- Never assert on wall-clock timing in CI; assert algorithmic bounds (batches processed, rows touched).
- Destructive upgrades need a dry-run assertion (reports what it would change, changes nothing) and an explicit rollback or restore note in the report.

## Caching and multisite

- Transients and object cache: write, read, invalidate on change; a cold cache and a warm cache give the same result; user-specific data is keyed by user; keys include blog id on multisite. Run cache-sensitive classes once with a real persistent backend (Redis service) because the default test cache is non-persistent and the transaction does not roll back the external store.
- Multisite: `switch_to_blog()` restored in `finally`; option and table-prefix assumptions (`$wpdb->get_blog_prefix()`); network-activated plugins; per-site uninstall.

## Privacy and GDPR

If the feature stores personal data, test the core privacy tools integration: registered exporters (`wp_privacy_personal_data_exporters`) return the data with a `done` flag and pagination; erasers (`wp_privacy_personal_data_erasers`) remove or anonymize it and report `items_removed`/`items_retained`; retention jobs delete what policy says; logs and test fixtures contain no real personal data.

## Sources and unverified items

Reviewed 2026-10-08.

- [WooCommerce HPOS documentation](https://developer.woocommerce.com/docs/features/high-performance-order-storage/): default for new installs since 8.2, option names, compatibility mode
- [HPOS extension recipe book](https://developer.woocommerce.com/docs/features/high-performance-order-storage/recipe-book/): `declare_compatibility`, avoid direct posts access, test with sync on and off
- [pre_http_request](https://developer.wordpress.org/reference/hooks/pre_http_request/)
- Confirmed: HPOS default for new installs since 8.2, option `woocommerce_custom_orders_table_enabled`, `before_woocommerce_init` + `FeaturesUtil::declare_compatibility( 'custom_order_tables', __FILE__, true )`, `OrderUtil::custom_orders_table_usage_is_enabled()`; the docs name `woocommerce_custom_orders_table_data_sync_enabled` as the sync option but give no test procedure for sync on/off. Action Scheduler: [API](https://actionscheduler.org/api/).
- Unverified here, check against installed versions: the `pre_option_*` approach to switching HPOS in a test bootstrap, Action Scheduler helper signatures, WooCommerce's internal test helper names, Store API route details.
