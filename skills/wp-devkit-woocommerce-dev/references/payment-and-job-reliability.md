# Webhooks, durable acceptance and Action Scheduler

Contents: two kinds of webhook; receiving a provider webhook; WooCommerce outgoing webhooks; Action Scheduler facts; failure-state acceptance; observability; false positives.

Research date: 2026-10-08. Sources: [Action Scheduler API](https://actionscheduler.org/api/), [usage](https://actionscheduler.org/usage/), [performance](https://actionscheduler.org/perf/), [WooCommerce webhooks](https://woocommerce.com/document/webhooks/), WooCommerce source (`class-wc-webhook.php`, `wc-webhook-functions.php`) and Action Scheduler source (`functions.php`, `ActionScheduler_DBStore.php`). Library behavior has changed between releases; read the installed `action-scheduler` version before relying on a detail.

## Two different webhook flows

1. Incoming: a payment provider calls your site. You own authentication, idempotency and recovery.
2. Outgoing: WooCommerce posts topic events (`order.created`, ...) to a URL the merchant configured. WooCommerce owns delivery; your receiver owns idempotency.

## Receive a provider webhook

1. Route: a REST route with `permission_callback => '__return_true'` is acceptable only because authentication is the signature check in the callback; say so in a comment. The legacy `?wc-api=` style (`woocommerce_api_{lowercase_gateway_class}`) works but the same rules apply.
2. Authenticate on raw bytes: `$request->get_body()` returns the unparsed body. Never hash `wp_json_encode( $request->get_json_params() )`. Compare with `hash_equals()`. Apply the provider's timestamp tolerance if it defines one. Fail closed on a missing secret.
3. Bind identity: the order id (or stored transaction/intent id), amount and currency come from the event and are compared with authoritative order state; the provider's event id is the idempotency identity, not an arbitrary transport header.
4. Accept durably, then acknowledge: insert into an inbox table with a unique key, then return 2xx. Do the heavy work in a worker.

```php
// Inbox row: UNIQUE KEY provider_event (provider, event_id)
$inserted = $wpdb->query( $wpdb->prepare(
	"INSERT IGNORE INTO {$wpdb->prefix}devkit_inbox (provider, event_id, payload_hash, status, received_gmt)
	 VALUES (%s, %s, %s, 'accepted', %s)",
	$provider, $event_id, hash( 'sha256', $raw_body ), gmdate( 'Y-m-d H:i:s' )
) );
if ( false === $inserted ) {
	return new WP_REST_Response( null, 500 );   // provider retries
}
$is_duplicate = ( 0 === $inserted );             // 0 rows: already accepted
```

- A duplicate must still be answered 2xx once the first delivery is durable; if the first is still `accepted` but never queued, the reconciler (below) finishes it, not the duplicate.
- Same event id with a different payload hash is an anomaly: log it, do not apply it.
- Persist the minimum payload. Redact PAN, tokens and customer fields from stored copies and logs; set a retention that covers the provider's replay window.
- `$wpdb->query( $wpdb->prepare(...) )` and the table creation via `dbDelta()` on upgrade are the ordinary tools; transients and object cache cannot guarantee uniqueness (eviction).

## WooCommerce outgoing webhooks (verified in source)

- Headers: `X-WC-Webhook-Source`, `-Topic`, `-Resource`, `-Event`, `-Signature`, `-ID`, `-Delivery-ID`. Signature is `base64_encode( hash_hmac( 'sha256', $raw_body, $secret, true ) )` over the body bytes sent (algorithm filterable; header names, the 60 second timeout, `redirection => 0` and the `> 5` failure threshold are set in `class-wc-webhook.php`).
- `X-WC-Webhook-Delivery-ID` is generated per delivery attempt, so it is not a stable business key. Deduplicate on resource id plus a content/modified-time check or the topic's own identifier.
- Delivery is queued at request shutdown and sent through Action Scheduler (`woocommerce_deliver_webhook_async`, group `woocommerce-webhooks`) with a 60 second timeout and no redirects. Any non-2xx response counts as a failure; after more than five consecutive failures (filter `woocommerce_max_webhook_delivery_failures`) the webhook is set to `disabled` and fires `woocommerce_webhook_disabled_due_delivery_failures`. A receiver that is slow or returns 5xx during a deploy silently stops receiving. Monitor webhook status.
- Ordering is not guaranteed. Treat payloads as "something changed" and fetch current state with the REST API when order matters.
- Logs: WooCommerce > Status > Logs, source `webhooks-delivery`.

## Action Scheduler facts

- Enqueue/schedule functions return the action id, or `0` on failure (error written to `error_log`). Always check: `if ( 0 === as_enqueue_async_action(...) ) { /* keep accepted state for the reconciler */ }`.
- Call them after `init` priority 1 or on `action_scheduler_init`.
- Arguments are stored as JSON and passed positionally; declare the accepted argument count in `add_action()`. Keep args small and non-sensitive (ids, not payloads). Large args are hashed and stored extended, but secrets still do not belong there.
- `$unique = true`: before Action Scheduler 4.0.0 an action was unique per hook and group only (the docblock still says so; the 4.0.0 changelog lists "action args are taken into account when scheduling unique actions" as a breaking change). From 4.0.0 args count too (atomic unique key, released when the action finishes, fails or is cancelled). Check the installed library version, treat uniqueness as "no identical pending/running action", and never use it as the only guard for an external side effect. A per-order job with `unique = true` can be silently dropped on libraries older than 4.0.0 because the order id in args does not differentiate it. Source: [Action Scheduler changelog](https://github.com/woocommerce/action-scheduler/blob/trunk/changelog.txt).
- Defaults: a WP-Cron trigger at most once per minute plus async loopback requests; 25 actions per batch, 30 second limit, one concurrent batch, stops near 90% memory. Failed actions are not retried by core; failed actions are purged after three months by default from 4.0.0 (filter `action_scheduler_retention_period_for_failed`; changelog). A low-traffic site with a broken loopback or disabled WP-Cron processes nothing. Production runners use WP-CLI: `wp action-scheduler run --batches=1 --group=my-plugin`, scheduled by system cron.
- Since WooCommerce 10.1 WooCommerce cron jobs run through Action Scheduler (developer advisory, Aug 2025): a stuck queue now delays core housekeeping too.
- Recurring actions: ensure they exist on activation and upgrade; `action_scheduler_ensure_recurring_actions` (3.9.3+) can re-assert them.
- Uninstall: unschedule only your own hooks/groups with `as_unschedule_all_actions()`.

## Worker pattern

```php
add_action( 'devkit_process_event', function ( int $inbox_id ) {
	// 1. Claim atomically: UPDATE ... SET status='processing' WHERE id=%d AND status IN ('accepted','retry')
	// 2. Re-read the order with wc_get_order(); verify status/amount/currency still allow the effect.
	// 3. Perform the effect through CRUD (payment_complete / wc_create_refund) with the provider idempotency key.
	// 4. Set status 'done' or 'retry' with attempt count and next_attempt_gmt; after N attempts 'dead' + alert.
}, 10, 1 );
```

A separate reconciler (recurring action, small batch) re-enqueues rows stuck in `accepted`/`processing` older than a threshold and rows whose enqueue returned `0`. Unknown outcome after a timeout: query the provider by idempotency key or object id before any retry that moves money.

## Failure-state acceptance

| Trigger | Required evidence |
|---|---|
| Duplicate or simultaneous event | One inbox row, one effect; duplicate answered 2xx |
| Crash before enqueue | Row stays `accepted`; reconciler enqueues it |
| `as_enqueue_async_action` returns 0 | Row not lost; alert; reconciler retries |
| Crash after provider effect | Reconciliation finds the effect; no second charge or refund |
| Out-of-order event | Transition follows provider rules, not arrival order |
| Failed one-off action | Visible `failed` status, bounded retry or dead-letter, operator path |
| No site traffic | System-cron runner advances the queue; lag measured |
| Old replay | Retention covers the replay horizon; replay does not reapply |

## Observability

Expose queue lag (oldest pending `scheduled_date_gmt` per group), failed count, inbox rows by status/age, and webhook status. Alert on thresholds rather than reading logs. Log event ids, order ids and outcomes, never bodies.

## Looks wrong but is fine

- `__return_true` permission callback on a signature-verified webhook route.
- Returning 2xx for a duplicate event.
- A single queued action with no retry when the operation is idempotent and a reconciler exists.
- `wp_schedule_event` for a lightweight non-critical task with no external side effect.
