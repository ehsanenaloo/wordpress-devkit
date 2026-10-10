# Templates, cart fragments, sessions, products and performance

Contents: template overrides; hooks first; cart fragments; sessions; product data and queries; admin and extension load; measurement; false positives.

Research date: 2026-10-08. Sources: [Template structure](https://developer.woocommerce.com/docs/theming/theme-development/template-structure/), [Developer advisory: session management and cron jobs in 10.1](https://developer.woocommerce.com/2025/08/08/developer-advisory-changes-to-session-management-and-cron-jobs-in-woocommerce-10-1/), [10.3 empty-session advisory](https://developer.woocommerce.com/2025/10/06/experimental-clearing-empty-sessions-10-3/), WooCommerce source (`class-wc-frontend-scripts.php`, `class-wc-widget-cart.php`, `wc-core-functions.php`).

## Template overrides

- Override path: `{theme}/woocommerce/<path without templates/>`; a file `woocommerce.php` in the theme takes priority over `woocommerce/archive-product.php`. Block themes use block templates; PHP overrides do not apply to them.
- Core templates change; overrides do not follow. WooCommerce > Status > System status > Templates lists overrides whose `@version` header is behind core. The header is advisory: updating the number without merging the change hides the problem. Diff against the core template of the installed version and merge.
- `wc_get_template()` resolves theme overrides before plugin defaults and caches the located path in the object cache per WooCommerce version. `WC_TEMPLATE_DEBUG_MODE` makes the locator ignore theme overrides, which isolates an override bug.
- Verify an override still contains the hooks core fires (`do_action`/`apply_filters` count). A copy that dropped a hook breaks extensions that depend on it. Counting hooks is a lead; read the diff.
- A template override duplicated only to change text or reorder output is usually replaceable with a hook or filter, which survives upgrades. Do not recommend removing an override that changes structure.
- Escape in templates: `esc_html`, `esc_attr`, `esc_url`, `wp_kses_post`; never echo order or customer fields raw (billing names and notes are customer input).
- Emails: override under `woocommerce/emails/`; custom email classes extend `WC_Email` and register through the `woocommerce_email_classes` filter. Test with a real email render (WooCommerce > Settings > Emails preview) and plain-text variants.

## Cart fragments

`wc-cart-fragments` is registered by core (`class-wc-frontend-scripts.php` registers it and does not enqueue it) and enqueued by the mini-cart widget (`WC_Widget_Cart`) and by themes/plugins that call `wp_enqueue_script( 'wc-cart-fragments' )`. It issues a `get_refreshed_fragments` AJAX call (a `WC_AJAX` endpoint) to keep a header cart count in sync, which also hurts full-page caching.

Before dequeuing: find the consumer (`rg "wc-cart-fragments|get_refreshed_fragments|widget_shopping_cart_content"`), confirm the header widget has another update path, and test add-to-cart on cached pages. Dequeuing it on a theme that renders a mini-cart count is a regression. Not enqueuing it is not a defect.

## Sessions

- The 10.1 advisory states: maximum session length is capped at 30 days (a filter that exceeds it is reduced and logged); defaults were 7 days for logged-in users and 2 days for guests; logged-in sessions are stored only in the session table; the `woocommerce_migrate_guest_session_to_user_session` filter controls guest-to-user merge at login; WooCommerce cron jobs moved to Action Scheduler.
- Code that raises `wc_session_expiration` / `wc_session_expiring` beyond 30 days does nothing past the cap. Persist long-lived data (saved carts, preferences) as user meta or a dedicated table, not in the session.
- Sessions are created for visitors who add to cart or hit certain endpoints. Large guest/bot traffic grows `wp_woocommerce_sessions`; cleanup runs through the `woocommerce_cleanup_sessions` event (a recurring Action Scheduler action every 12 hours, scheduled in `class-woocommerce.php`). The "clear empty sessions" feature (added in 10.3) was experimental and off by default; check the installed version.
- Never store personal data or tokens in the session beyond what core does; sessions are accessible to anything running in the request.

## Product data and queries

- Use `wc_get_product()`, `wc_get_products()` / `WC_Product_Query`, and product CRUD setters (`set_regular_price`, `set_stock_quantity`) followed by `save()`. Direct `update_post_meta( $id, '_price', ... )` skips lookup-table sync (`wc_product_meta_lookup`), transient/cache invalidation and hooks, so sorting, filtering and cached prices disagree with the stored value.
- Product listing sorted or filtered by price/stock/rating is indexed through the lookup tables (`wc_product_meta_lookup`, `wc_product_attributes_lookup`). `WP_Query` on raw `_price` meta bypasses them and does not scale. `WP_Query` on products for simple content queries is still valid.
- Variable products: loading all variations (`get_children()` + `wc_get_product()` per child) in a loop is the classic N+1; request only IDs or use `get_available_variations()` knowingly (it is expensive on large variation sets).
- `wc_get_products( array( 'limit' => -1 ) )` on a large catalog is a memory risk; paginate, and pass `return => 'ids'` when objects are not needed.
- Custom product types: register via the `product_type_selector` and `woocommerce_product_class` filters and keep the data store; test add-to-cart, REST (`wc/v3/products`) and Store API serialization.

## Admin and extension load

- Autoloaded options: list with `wp option list --autoload=on --fields=option_name,size_bytes` and look for large values and large transients; Woo extensions often add large autoloaded blobs.
- Hooks that run on every request (`init`, `wp_loaded`) should not query orders or call remote APIs. Cache remote data with a short transient, and set a timeout on `wp_remote_*`.
- Query Monitor (staging) shows duplicated queries, hooks by time and HTTP calls. A single profile on a warm cache proves little; compare cold and warm cache and with a persistent object cache.

## Measurement and acceptance

- Record the baseline: query count, slow queries, TTFB for shop, product, cart and checkout on a staging copy with realistic catalog and order volume.
- After a change, rerun the same measurement and the functional journey (add to cart, coupon, checkout). A performance fix that changes totals, stock display or fragments is a regression.
- Passing does not prove production behavior with real traffic, CDN or full-page cache rules.

## Looks wrong but is fine

- Template override whose `@version` is current and which retains every core hook.
- `wc-cart-fragments` enqueued on pages that display a mini-cart.
- `WP_Query` against `product` for a blog-style listing without price filters.
- Session or transient used for short-lived checkout state.
