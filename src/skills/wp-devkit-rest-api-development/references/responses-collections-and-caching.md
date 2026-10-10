# Responses, errors, collections, caching and idempotency

Contents: response objects; errors; status code map; collections and pagination; global parameters; caching; writes, retries and idempotency; large data; client wiring; failure symptoms; sources.

## Response objects

- Return data or a `WP_REST_Response` (`rest_ensure_response( $data )` wraps arrays). Return a `WP_Error` for failures; core converts it to JSON with `code`, `message`, `data.status`. Do not `echo`, `wp_send_json_*()` or `die` inside a REST callback (breaks batch, headers, filters such as `rest_post_dispatch`).
- Set status and headers on the response: `$response = new WP_REST_Response( $data, 201 ); $response->header( 'Location', rest_url( ... ) );`.
- JSON is not an HTML sink. Do not `esc_html()` values stored for later rendering by a JSON consumer; escape at the point of output (React escapes by default; `dangerouslySetInnerHTML`/`innerHTML` sinks need sanitization). Return rendered HTML fields only when the field is documented as HTML and already passed through `wp_kses_post` or the content filters.
- Never serialize secrets, password hashes, nonces for other users, internal paths or stack traces. Whitelist fields in `prepare_item_for_response()` rather than returning raw objects or `$wpdb` rows.
- Use `context` (`view`, `edit`, `embed`) for fields that only editors may see; `filter_response_by_context()` removes fields from a schema.

## Error shape

`new WP_Error( 'acme_invalid_state', __( 'Event is already published.', 'acme' ), array( 'status' => 409 ) )`. Without `status` the default is 500 (verified), which wrongly signals a server fault for a client mistake. Keep error `code` strings stable: clients branch on them. Add `params`/`details` for field-level errors in the same shape core uses (`rest_invalid_param` with `params` and `details`).

## Status code map

| Situation | Status |
|---|---|
| Created | 201 plus `Location` |
| Deleted (body returned) | 200; or 204 with no body |
| Invalid/missing input | 400 (`rest_invalid_param`, `rest_missing_callback_param`) |
| Not authenticated / not allowed | 401 / 403 (`rest_authorization_required_code()`) |
| Object not found | 404 |
| State conflict, stale `If-Match`, duplicate key | 409 / 412 |
| Unprocessable but syntactically valid | 422 (use consistently if chosen) |
| Rate limited | 429 + `Retry-After` |
| Upstream failure | 502/503/504, never 200 with an error body |

Preserve the status semantics of an existing public API even when they differ from this table.

## Collections and pagination (verified)

- `per_page` is an integer 1-100 (core controller default 10, maximum 100); `page` starts at 1; `offset` is supported on core collections. `X-WP-Total` and `X-WP-TotalPages` headers carry totals; core exposes them (and `Link`) to browsers through CORS expose-headers.
- A page beyond the last returns `400 rest_post_invalid_page_number` on core post collections; define the equivalent for your own, and return an empty array (not an error) for an in-range empty result so clients can tell "no data" from "failure".
- Cap `per_page` in your schema (`maximum`), cap `search` length, and allow-list `orderby`/`order` values (`enum`); never interpolate `orderby` into SQL.
- Totals require a count query. For huge tables, drop exact totals (`no_found_rows => true` in `WP_Query`) and offer cursor pagination (`after_id`) with a `next` link; document the trade-off.
- Stable ordering: always add a unique tiebreaker (`ID`) so pages neither repeat nor skip rows.
- Draft/private visibility: enforce status filters by capability in the query, not by post-filtering a page (post-filtering breaks totals and leaks existence via counts).

## Global parameters (verified)

`_fields` (limits response properties; nested meta keys supported since 5.3), `_embed` (embeds linked resources; relation limiting since 5.4), `_method` / `X-HTTP-Method-Override` (use only with POST), `_envelope`, `_jsonp` (legacy; core disables JSONP via `rest_jsonp_enabled` filter, check). `_fields` filters after `prepare_item_for_response()` unless the controller uses `get_fields_for_response()` to skip expensive field computation; implement that for costly fields. Without pretty permalinks use `?rest_route=/ns/v1/...`.

## Caching

- Core sends no-cache headers to logged-in users (`rest_send_nocache_headers` defaults to `is_user_logged_in()`; also forced on failed cookie nonce checks). Anonymous responses carry no explicit cache lifetime unless you set one.
- Private or per-user responses must not be stored by shared caches: send `Cache-Control: private, no-store` (set through `$response->header()`), and make sure CDN/page-cache rules do not cache `/wp-json/` for authenticated or cookie-bearing requests. Test with two identities against the same URL.
- Public cacheable responses: set `Cache-Control: public, max-age=...`, add `ETag`/`Last-Modified`, and vary on the headers that change the body (`Vary: Origin` already added by core for CORS; add `Accept-Language` if localized).
- Server-side: cache expensive collection queries in the object cache with a version key bumped on writes; cache the item schema in the controller.

## Writes, retries and idempotency

- `PUT` and `DELETE` are idempotent by definition; `POST` creating objects is not. Retrying a timed-out `POST` creates duplicates. For payments, orders, emails and imports require a client-supplied `Idempotency-Key` header (stored with the result for a retention window, unique-indexed) and return the original response for a replay.
- Wrap multi-step writes so that partial failure does not leave half-applied state: validate everything first, then write; on failure roll back what you created (custom tables can use transactions on InnoDB; posts/meta cannot) and return an error whose status reflects the cause.
- Optimistic concurrency for edits: accept `If-Match` with the modified timestamp/revision and return `412`.
- Re-read the object after write when returning it so the response matches stored state (filters can alter saved values).
- Nonces provide request-intent for cookie sessions, not once-only processing.

## Large data and uploads

Stream or batch exports rather than building giant arrays in memory; background heavy work (Action Scheduler) and return `202 Accepted` with a status URL. File uploads: validate with `wp_check_filetype_and_ext`, use `wp_handle_upload`/`media_handle_sideload`, require `upload_files`, and bound size.

## Client wiring

`wp.apiFetch( { path: '/acme/v1/events?per_page=20' } )` handles root URL and nonce when `wp-api-fetch` is a dependency. Request with `parse: false` to read headers (`X-WP-TotalPages`). Handle the JSON error body (`code`, `message`, `data.status`), not only HTTP status; show actionable messages and keep user input on failure.

## Failure symptoms

| Symptom | Evidence | Fix direction |
|---|---|---|
| Client sees HTML or `0` | Handler used `wp_send_json`/`echo`, a notice printed before JSON, or the request hit admin-ajax | Return REST responses; fix notices |
| Every error is 500 | `WP_Error` without `status` | Add status |
| Drafts or private items in a public collection | Status filter missing or applied after pagination | Enforce visibility in the query |
| Another user sees cached private data | CDN caches `/wp-json/` with cookies | Cache-Control private + CDN bypass; test with two users |
| Duplicates after retry | Non-idempotent POST | Idempotency key |
| Slow collection | Unbounded `per_page`, per-item queries, `_embed` of heavy relations | Cap, batch-prime caches (`_prime_post_caches`, `update_post_meta_cache`), `_fields` aware fields |

## Sources

Research date: 2026-10-08.

- Pagination: https://developer.wordpress.org/rest-api/using-the-rest-api/pagination/
- Global parameters: https://developer.wordpress.org/rest-api/using-the-rest-api/global-parameters/
- Custom endpoints (WP_Error status): https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/
- Core source read (trunk): `class-wp-rest-server.php` (`rest_send_nocache_headers`, CORS expose headers), `class-wp-rest-controller.php` (`get_collection_params`).
