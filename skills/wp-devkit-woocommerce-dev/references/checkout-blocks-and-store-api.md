# Classic vs block checkout, Store API, cart totals

Contents: identify the checkout type; hook parity; validation; extra fields; extending Store API data; block payment methods; cart, fee, tax and shipping recalculation; verification; false positives.

Researched 2026-10-08. Sources: [Cart and Checkout blocks](https://developer.woocommerce.com/docs/block-development/extensible-blocks/cart-and-checkout-blocks/), [Additional checkout fields](https://developer.woocommerce.com/docs/block-development/extensible-blocks/cart-and-checkout-blocks/additional-checkout-fields/), [Extending the Store API](https://developer.woocommerce.com/docs/apis/store-api/extending-store-api/) (and its add-data and update-cart pages), [payment method integration](https://developer.woocommerce.com/docs/block-development/extensible-blocks/cart-and-checkout-blocks/checkout-payment-methods/payment-method-integration/), [hook alternatives](https://github.com/woocommerce/woocommerce/blob/trunk/docs/block-development/reference/hooks/hook-alternatives.md), [block checkout default announcement](https://developer.woocommerce.com/2023/08/18/cart-and-checkout-blocks-becoming-the-default-experience/), and Store API route source (`Routes/V1/Checkout.php`, trunk 11.3-dev).

## Identify the checkout type first

- Block checkout is the default for new stores since WooCommerce 8.3. Existing stores and any store that swapped in the `[woocommerce_checkout]` shortcode stay classic. Both can exist on one multisite network.
- Inspect the checkout page content (`wp post get <id> --field=post_content`): a `wp:woocommerce/checkout` block versus a `[woocommerce_checkout]` shortcode. Also check for an active theme template that overrides the page. Do not infer from plugin code.
- A fix that works in one type is not evidence for the other. State which type the evidence covers.

## Hook parity (most defects live here)

| Need | Classic (shortcode) | Block / Store API |
|---|---|---|
| Validate before order creation | `woocommerce_checkout_process`, `woocommerce_after_checkout_validation` | `woocommerce_store_api_cart_errors` (add to the passed `WP_Error`); `woocommerce_store_api_validate_cart_item`; field-level `woocommerce_validate_additional_field` |
| Write data to the order | `woocommerce_checkout_create_order` (before save), `woocommerce_checkout_update_order_meta` | `woocommerce_store_api_checkout_update_order_meta` (throwing an exception puts the block in a warning state and blocks checkout) |
| After order creation | `woocommerce_checkout_order_processed` | `woocommerce_store_api_checkout_order_processed`. The classic action does not fire on Store API requests. |
| First creation of the draft order | n/a | `woocommerce_store_api_checkout_order_created`. As of 10.8.0 the draft order is created at place-order time (POST), not on the first PATCH, so first-touch logic that assumed an early draft order changes behavior (confirmed by the `@since 10.8.0` docblock in `StoreApi/Routes/V1/Checkout.php`, not by a release note). |
| Add or alter fields | `woocommerce_checkout_fields` | Adding is supported through the Additional Checkout Fields API; editing core fields through the filter is not. `woocommerce_default_address_fields` has no effect. |
| Markup injected around the form (`woocommerce_review_order_*`, `woocommerce_before_checkout_form`) | works | not supported; use a block, inner block or the checkout filters |
| Cart totals hooks (`woocommerce_cart_calculate_fees`, `woocommerce_before_calculate_totals`, `woocommerce_after_calculate_totals`) | works | works (fully supported per the hook table) |

Per the hook alternatives document, `woocommerce_checkout_process` is only partially supported on blocks, `woocommerce_checkout_create_order` has no block equivalent (nothing can act just before order finalization), and `woocommerce_after_checkout_validation` is not covered there, so test it. The full per-hook table lives in the hook alternatives document. Re-read it for the installed version rather than trusting this summary for rarely used hooks.

## Validation and errors

- Classic: `wc_add_notice( $message, 'error' )` inside `woocommerce_after_checkout_validation` or throw inside order creation hooks.
- Store API: add errors to the `WP_Error` in `woocommerce_store_api_cart_errors`, or throw `\Automattic\WooCommerce\StoreApi\Exceptions\RouteException` from a route-level hook. `wc_add_notice` in a Store API path is captured and converted, but the docs prefer the `WP_Error` route.
- Server-side validation is the control; JavaScript validation is convenience. Re-validate every field the request body can supply, including `extensions` data.

## Additional Checkout Fields API (blocks)

```php
add_action( 'woocommerce_init', function () {
	woocommerce_register_additional_checkout_field( array(
		'id'       => 'my-plugin/gift-note',
		'label'    => __( 'Gift note', 'my-plugin' ),
		'location' => 'order',          // contact | address | order
		'type'     => 'text',           // text | select | checkbox | date
		'required' => false,
		'sanitize_callback' => 'sanitize_text_field',
	) );
} );
```

- Register on `woocommerce_init` or later. Earlier registration breaks initialization and translation.
- Locations: `contact` (saved to the customer account), `address` (saved to both customer and order, separate billing and shipping values; the location validation hook fires twice), `order` (saved to the order only).
- Hooks: `woocommerce_sanitize_additional_field` (filter, before validation), `woocommerce_validate_additional_field` (action, add errors to the passed `WP_Error`), `woocommerce_blocks_validate_location_{location}_fields`.
- Storage: individual meta keys prefixed `_wc_billing/`, `_wc_shipping/` or `_wc_other/`. Read with `CheckoutFields::get_field_from_object( $id, $object, $group )` (class `Automattic\WooCommerce\Blocks\Domain\Services\CheckoutFields`, resolved from `Automattic\WooCommerce\Blocks\Package::container()`) rather than raw meta. `woocommerce_register_additional_checkout_field()` throws an `Exception` for invalid options, so a bad definition surfaces as a fatal on `woocommerce_init`; wrap registration or test it. The docs do not describe classic-checkout support for these new fields (they cover only compatibility for existing shortcode-checkout fields via `woocommerce_set_additional_field_value` and `woocommerce_get_default_value_for_{$key}`); test it.
- Required fields differ between guest and logged-in flows; test both. Do not treat these values as trusted: they are customer input.

## Extending Store API responses

```php
use Automattic\WooCommerce\StoreApi\Schemas\V1\CartSchema;

add_action( 'woocommerce_blocks_loaded', function () {
	woocommerce_store_api_register_endpoint_data( array(
		'endpoint'        => CartSchema::IDENTIFIER,
		'namespace'       => 'my_plugin',
		'data_callback'   => fn() => array( 'badge' => 'express' ),
		'schema_callback' => fn() => array(
			'badge' => array( 'type' => 'string', 'readonly' => true ),
		),
		'schema_type'     => ARRAY_A,
	) );
	woocommerce_store_api_register_update_callback( array(
		'namespace' => 'my_plugin',
		'callback'  => 'my_plugin_handle_cart_update', // receives $data from extensionCartUpdate
	) );
} );
```

- Both registrations belong on `woocommerce_blocks_loaded`; the Store API container is unavailable earlier. Never `new ExtendSchema()`.
- Return an array from `data_callback` even when empty. Exceptions are logged; for shop managers with `WP_DEBUG` they surface in the front end.
- `register_update_callback` runs for `extensionCartUpdate()` from JavaScript. The docs say nothing about authorization or input validation: validate and sanitize `$data` yourself, key it by an `action` string, and keep the namespace unique (a second registration under one namespace overwrites the first). The callback return value is ignored.
- Extensions must change cart state only through `extensionCartUpdate`, not by mutating client state.

## Block payment methods

- PHP: extend `AbstractPaymentMethodType` (`initialize()` runs on every request, keep it light; `is_active()`, `get_payment_method_script_handles()`, `get_payment_method_data()`), register on `woocommerce_blocks_payment_method_type_registration` via `$registry->register()`. The `$name` must match the JavaScript `name`.
- JS: `registerPaymentMethod` / `registerExpressPaymentMethod` with `name`, `label`, `content`, `edit`, `canMakePayment`, `ariaLabel`, `supports`. `canMakePayment` runs on the storefront only and may be called repeatedly; memoize it.
- Server processing for block checkout is `woocommerce_rest_checkout_process_payment_with_context` with `PaymentContext` and `PaymentResult` (`set_status`, `set_payment_details`, `set_redirect_url`); throwing an exception reports an error. A gateway that only implements `process_payment()` for classic does not automatically appear in the block checkout. Declare `cart_checkout_blocks` compatibility only after testing it.
- Client data reaches the server through `paymentMethodData` in `onPaymentProcessing`, arriving as `payment_data`. Treat it as untrusted input.

## Totals, fees, tax and shipping

- Calculation hooks can run many times per request. A fee added with `$cart->add_fee()` in `woocommerce_cart_calculate_fees` is rebuilt each calculation; storing the fee in session and re-adding it on each run accumulates duplicates.
- Tax-inclusive vs exclusive pricing, fee tax status (`add_fee( $name, $amount, $taxable, $tax_class )`), shipping tax and rounding differ by store settings. Record them as test inputs.
- Money is computed by WooCommerce in decimals with `wc_get_price_decimals()`; avoid float comparisons for equality and use `wc_format_decimal()` / currency helpers for display and binding.
- Recalculate paths to test: add/remove item, quantity change, coupon apply/remove, shipping method change, address change, logged-in vs guest, retry after a failed payment.
- Draft orders: Store API creates a draft order (`checkout-draft`). Plugins that treat every order creation as a real sale (analytics, CRM sync) mis-count. Gate on status or on `woocommerce_store_api_checkout_order_processed`.

## Verification

- Playwright (or manual) run of the real checkout in both types where both are supported; assert order meta by reloading the order and reading the Store API response for extension data.
- `curl`-level Store API check on a disposable store: `GET /wp-json/wc/store/v1/cart` returns your `extensions.<namespace>` object.
- PHPUnit with `WC_Unit_Test_Case` for pure calculation (fees, tax) is cheap and independent of the checkout type.
- A pass proves the tested path only. Third-party express payment buttons, local pickup and subscriptions have separate code paths.

## Looks wrong but is fine

- Classic hooks present in a plugin that also registers a block integration: both surfaces are covered.
- `woocommerce_checkout_fields` used on a store that is demonstrably on the shortcode checkout.
- `wc-cart-fragments` and `wc_add_notice` usage in classic-only code paths.
