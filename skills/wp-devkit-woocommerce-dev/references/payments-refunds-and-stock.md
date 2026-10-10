# Payments, refunds, stock and order status

Contents: gateway contract; order status and `payment_complete()`; stock reduction and reservation; refunds; provider-initiated events; money handling; test cases; false positives.

Research date: 2026-10-08. Sources: [Payment gateway API](https://developer.woocommerce.com/docs/features/payments/payment-gateway-api/), WooCommerce source (`class-wc-order.php` `payment_complete`, `wc-stock-functions.php`, `wc-order-functions.php` `wc_create_refund`, `OrderStatus` enum), [WooCommerce webhooks](https://woocommerce.com/document/webhooks/). Provider-specific behavior (Stripe, PayPal, Adyen...) must come from that provider's current docs; none is asserted here.

## Gateway contract

- Extend `WC_Payment_Gateway`. `process_payment( $order_id )` returns `array( 'result' => 'success', 'redirect' => $this->get_return_url( $order ) )`, or calls `wc_add_notice( $message, 'error' )` and returns `array( 'result' => 'failure' )` (documented). Throwing for expected declines is not the contract.
- Declare `$this->supports = array( 'products', 'refunds', ... )` only for features implemented; `refunds` requires `process_refund( $order_id, $amount = null, $reason = '' )` returning `true`, `false` or `WP_Error`.
- Card data must not touch the server unless the merchant is in PCI scope for it. Use provider-hosted fields or redirect flows; never log request bodies containing PAN/CVV/tokens. `error_log( print_r( $_POST, true ) )` in a gateway is a leak, not a debug aid.
- For block checkout a separate integration is needed ([checkout-blocks-and-store-api.md](checkout-blocks-and-store-api.md)).
- Gateway settings with secrets: store through the settings API; do not echo secret fields back into HTML values; do not put secrets in order meta or notes.

## Order status and `payment_complete()`

Facts from `WC_Order::payment_complete()`:

- It acts only if the current status is one of `on-hold`, `pending`, `failed`, `cancelled` (filter `woocommerce_valid_order_statuses_for_payment_complete`). In any other status (for example `processing` or `completed`) it does nothing and returns `false`. A second call after success is therefore a no-op for status, but the caller must not treat the call itself as proof that fulfillment ran once.
- It stores the transaction id, sets `date_paid` once, sets status `processing` (needs shipping/processing) or `completed` (via filter `woocommerce_payment_complete_order_status`), adds an order note, and fires `woocommerce_payment_complete` (which triggers stock reduction).
- Prefer `payment_complete( $transaction_id )` over `update_status( 'processing' )` for a captured payment; the latter skips `date_paid`, the transaction id and the payment-complete hooks.
- Use `on-hold` when payment needs manual verification, `failed` for a declined attempt on an existing order. Do not invent a custom state machine over core statuses without reading existing extensions' expectations; custom statuses must be registered through the `wc_order_statuses` filter (plus `register_post_status`) and tested in both storage modes.
- Unpaid pending orders are cancelled by the scheduled `woocommerce_cancel_unpaid_orders` job (Action Scheduler when available, WP-Cron otherwise) after `woocommerce_hold_stock_minutes`. The job is scheduled only when the hold duration is at least 1 and stock management is enabled, and the filter `woocommerce_cancel_unpaid_order` cancels by default only orders created via `checkout` or `store-api` (`wc_cancel_unpaid_orders()` in `wc-order-functions.php`). A slow gateway callback that arrives after cancellation must handle `cancelled` -> paid explicitly (it is in the valid list, which re-reduces stock).

## Stock

- Reduction runs on `woocommerce_payment_complete` and on transitions to `completed`, `processing`, `on-hold` through `wc_maybe_reduce_stock_levels()`. It checks an order-level "stock reduced" flag (data store `get_stock_reduced()`/`set_stock_reduced()`, stored as `_order_stock_reduced`) so repeated transitions do not reduce twice. Restoration (`wc_maybe_increase_stock_levels()`) runs for `cancelled` and `pending` when the flag is set; the `failed` transition was added in WooCommerce 11.0.0 per the source comment, so before 11.0.0 a failed order does not restore stock by itself. See `wc-stock-functions.php`, including `wc_reduce_stock_levels( $order_id )` and `wc_increase_stock_levels( $order_id )` (order object or id).
- Hand-rolled `$product->set_stock_quantity( $product->get_stock_quantity() - $qty )` is a read-modify-write race. Use `wc_update_product_stock( $product, $qty, 'decrease' | 'increase' )`, which issues a relative SQL update on the legacy product store.
- Duplicating that logic (manual reduce plus core reduce) double-counts. Check the flag, or use the core helpers `wc_reduce_stock_levels( $order )` and `wc_increase_stock_levels( $order )`.
- Checkout reservation: `wc_reserve_stock_for_order()` runs on `woocommerce_checkout_order_created`, holds for `woocommerce_hold_stock_minutes` (default 60), skipped when `woocommerce_hold_stock_for_checkout` is false or stock management is off. Reservation protects the last item between order creation and payment; it does not protect between add-to-cart and checkout.
- Variations may have stock managed by the parent (`get_stock_managed_by_id()`); backorders and `woocommerce_notify_*` thresholds change outcomes. Include them in tests.

## Refunds

- `wc_create_refund( array( 'order_id' => $id, 'amount' => '10.00', 'reason' => '', 'line_items' => array(...), 'refund_payment' => false, 'restock_items' => false ) )` validates the amount against `get_remaining_refund_amount()` and returns a `WP_Error` on an invalid amount.
- `refund_payment => true` calls the gateway (`wc_refund_payment()` -> `process_refund()`); a `WP_Error` from the gateway deletes the partial refund and is returned. `restock_items => true` restocks line items via core.
- Provider-initiated refund (dashboard refund arriving by webhook): call `wc_create_refund` with `refund_payment => false`. Passing `true` asks the provider to refund again.
- Idempotency: key the refund by the provider's refund id (store it on the refund via `update_meta_data`), look it up before creating, and check the remaining amount. A duplicate webhook then finds the existing refund.
- Partial refunds change totals but not necessarily the order status; do not assume `refunded` status means all items are restocked.

## Money

- Compare and bind amounts as decimals at the currency's precision: `wc_format_decimal()`, `wc_get_price_decimals()`, or integer minor units (`round( $amount * 100 )`) for the provider. Floats drift; JPY-like zero-decimal and three-decimal currencies break a hard-coded `* 100`.
- Bind every provider event to order id, order key or stored transaction id, currency and amount from authoritative order state. An event that names an order but carries a different amount or currency must not complete it.
- Tax-inclusive prices, discounts, shipping tax and rounding (`woocommerce_tax_round_at_subtotal`) change the total the provider must see; test with the store's real tax settings.

## Test cases that distinguish the failure

| Case | Pass evidence |
|---|---|
| Same success callback delivered twice | One `date_paid`, one transaction id, one fulfillment effect, stock reduced once |
| Callback after unpaid-order cancellation | Order handled by an explicit rule; stock level consistent |
| Two checkouts for the last unit | Exactly one succeeds; stock never negative unless backorders allowed |
| Duplicate provider refund event | One refund object; remaining amount correct; provider called zero extra times |
| Declined card then success on retry | Order not completed on the first attempt; one completion afterwards |
| Amount/currency mismatch in callback | Rejected and logged without data leakage; order unchanged |

Use provider sandbox and published test cards on a disposable store only. A sandbox pass does not prove production gateway behavior, live webhook delivery or tax jurisdiction rules.

## Looks wrong but is fine

- `update_status( 'on-hold' )` for manual verification flows; `failed` after a decline.
- `payment_complete()` returning `false` for an already-processing order.
- Direct `wc_update_product_stock()` calls in importers.
- `error_log` of an order id or provider event id (not card or customer data).
