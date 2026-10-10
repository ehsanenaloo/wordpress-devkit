---
name: wp-devkit-woocommerce-dev
description: "Build, debug or review WooCommerce extensions: HPOS order access, classic vs block checkout and Store API, gateways, refunds, stock, payment webhooks, Action Scheduler jobs and template overrides. Generic plugin or REST issues go to the plugin and REST skills."
---

# WooCommerce behavior and reliable order work

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, store mutations, mutating WP-CLI (`wp wc hpos sync|enable|cleanup`), or running untrusted code. Use the implementation path only when the request authorizes changes.

## Inputs to establish (from the project first, then ask)

WooCommerce, WordPress and PHP versions; order storage (`woocommerce_custom_orders_table_enabled`) and sync option; checkout type (block or shortcode); active gateways and their provider contract; tax-inclusive setting and currencies; Action Scheduler runner (WP-CLI, loopback, WP-Cron); installed extensions touching orders or checkout; whether a disposable store exists.

## Route the task

| Symptom or goal | Start with |
|---|---|
| Order data lost, wrong, slow; HPOS warning; `wc_get_orders` args; metabox or list column on order screens | `references/order-storage-and-hpos.md` |
| Field, fee, validation or markup works in one checkout only; Store API data; block payment method | `references/checkout-blocks-and-store-api.md` |
| Double charge/fulfillment, status wrong, stock off, refund mismatch, gateway code | `references/payments-refunds-and-stock.md` |
| Provider or Woo webhook, stuck jobs, retries, missing events | `references/payment-and-job-reliability.md` |
| Template override outdated, cart fragments, sessions, product queries, slow shop | `references/templates-sessions-and-performance.md` |

Hand off: exploitable authorization/XSS/SQLi in general plugin code to `wp-devkit-security-review`; REST route design to `wp-devkit-rest-api-development`; lifecycle or uninstall to `wp-devkit-plugin-development`; measured slowness beyond Woo internals to `wp-devkit-performance-review`; data upgrades to `wp-devkit-migration-upgrade-review`.

## Code Review Workflow

1. Reproduce or describe the journey. Record checkout type and storage mode; a finding is scoped to the modes evidenced.
2. Trace each order read and write to its object: order CRUD, product CRUD, or a different post type. Direct post-meta use on non-orders is fine.
3. Follow the money path: amount, currency, tax, shipping, coupon, refund. Identify who is authoritative (provider event, order state) at each step.
4. For callbacks and jobs, find the authentication step, the durable acceptance point, the idempotency key and the recovery path for a crash between steps.
5. Compare overrides and extension points with the installed version (template diff, hook table, Store API route source).
6. Confirm each candidate with a code path and, when possible, a runtime check on a disposable store. Otherwise report it as a candidate with the missing evidence.

Insufficient evidence is a valid outcome: report what could not be established (provider behavior, live runner, tax jurisdiction) and the check that would settle it.

## Implementation workflow

1. State the expected behavior, the affected boundary and the storage/checkout modes in scope.
2. Reproduce the failure first (a failing test or a recorded manual run) on a disposable store.
3. Use CRUD and supported extension APIs; declare compatibility only after the test matrix passes.
4. Keep money, stock and identity decisions server-side and idempotent. Do not regenerate baselines or weaken checks to get green.
5. Run the acceptance checks below. Report any unavailable check as unexecuted.
6. Publishing, deployment and live maintenance (data sync, cleanup) need their own task scope.

## Search Patterns for Quick Detection

Read-only leads; matches are candidates, not findings.

```sh
rg -n -g '*.php' -g '!vendor' -g '!node_modules' -e 'get_post_meta|update_post_meta|wp_insert_post|shop_order|post_type.*shop_order' .
rg -n -g '*.php' -g '!vendor' -e 'process_payment|payment_complete|hash_hmac|hash_equals|wc_create_refund|set_stock_quantity|reduce_order_stock' .
rg -n -g '*.php' -g '*.js' -g '!vendor' -g '!node_modules' -e 'woocommerce_checkout_(process|fields|create_order|order_processed)|woocommerce_store_api|registerPaymentMethod|woocommerce_register_additional_checkout_field' .
rg -n -g '*.php' -g '!vendor' -e 'as_(enqueue|schedule)_|wp_schedule_event|wc-cart-fragments|wc_session_expir' .
```

Exit 0 = match, 1 = none, 2 = error. No match does not prove absence: helpers, multi-line calls and generated code defeat grep. Confirm the object type and reachable path before reporting.

## Acceptance checks (discover the project's own commands first)

- Storage: run the HPOS test matrix from `references/order-storage-and-hpos.md`; `wp wc hpos status` and `wp wc hpos verify_data` are read-only evidence.
- Checkout: Playwright or manual journey in each supported checkout type; Store API `GET /wp-json/wc/store/v1/cart` for extension data.
- Payments/webhooks: duplicate, out-of-order and crash-between-steps cases from the failure-state table; sandbox only.
- Static: `phpcs` with WordPress and WooCommerce rules, PHPStan with `php-stubs/woocommerce-stubs`, PHPUnit via `WC_Unit_Test_Case` where the project has it.
- Queue: `wp action-scheduler` runner output, pending/failed counts and oldest-pending age.

A pass proves the tested modes, versions and fixtures. It does not prove production gateway behavior, live webhook delivery, tax jurisdiction rules, third-party extension interaction or untested storage modes.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: severity per the contract, file:line, actor, trigger, reachable path, impact (money/stock/data), confidence, minimal fix, regression test. Keep candidates and "not verified" items in a separate list.

Implementation: changed boundaries, behavior before/after, storage/checkout modes covered, commands run with exit status, checks not run, residual risk, rollback note (flag or revert path; data changes need a backup/restore plan).

## References

- `references/order-storage-and-hpos.md`: read for order CRUD, queries, admin screens, sync and CLI.
- `references/checkout-blocks-and-store-api.md`: read for hook parity, fields, Store API, block payments, totals.
- `references/payments-refunds-and-stock.md`: read for gateway contract, statuses, stock, refunds, money.
- `references/payment-and-job-reliability.md`: read for webhooks, inbox/outbox, Action Scheduler.
- `references/templates-sessions-and-performance.md`: read for overrides, fragments, sessions, products.
