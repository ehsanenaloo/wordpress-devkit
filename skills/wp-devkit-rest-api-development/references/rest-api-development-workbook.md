# REST contracts and request boundaries workbook

Contents: establish the behavior; decision checkpoints; symptom triage; worked decisions; looks wrong but is fine; verification recipes; severity guidance; sources.

Apply [the engineering contract](engineering-contract.md) before classifying a concern. Deep topics: `route-registration-and-schema.md`, `authentication-and-permissions.md`, `responses-collections-and-caching.md`.

## Establish the behavior

Record namespace/route, method, caller identity and authentication model (cookie, Application Password, custom), request and response examples, target WordPress version, protected-object policy, and consumers (block editor, theme JS, mobile app, partner). Write expected status, body and side effects before reading code. A grep hit is a lead.

## Decision checkpoints

| Decision | What changes the answer |
|---|---|
| Contract | Namespace, route, method, fields, error codes, headers and pagination are public API. Do not add an endpoint to bypass a failing one. |
| Actor and policy | Authenticate with the supported model, then authorize the object and action. Intentional public submissions can be valid; assess exposure, side effects and abuse controls. |
| Input | Schema type/enum/range at the route; custom `sanitize_callback` removes implicit validation; the identifier must be read one way (body-first parameter order). |
| Output | Whitelisted fields, correct `context`, stable error `code`, explicit `status`. |
| Collections | Cap `per_page`, stable order, visibility in the query, totals vs cursor. |
| Caching | Private data never in shared cache; verify with two identities. |
| Mutations | Retry semantics, partial failure, denied calls change nothing. |

## Symptom triage

| Symptom | Evidence to gather | Action after confirmation |
|---|---|---|
| Authenticated browser call returns 401 | Is `X-WP-Nonce` sent? (missing nonce means user 0) | Send/refresh nonce; do not make the route public. |
| 403 `rest_cookie_invalid_nonce` | Age of embedded nonce, page cache | Stop caching nonce-bearing HTML; refresh from response header. |
| Application Password 401 on production only | `Authorization` header reaching PHP, HTTPS/`local` environment | Fix proxy/server or TLS; do not force-enable over HTTP. |
| User edits an object they do not own | Permission callback capability and object id | Use `edit_post` with the id; re-read after a denied call. |
| Valid payload rejected | `type`, union order, `enum`, coercion for form-encoded bodies | Correct schema or caller; keep validation. |
| Invalid payload accepted | `sanitize_callback` without `validate_callback` | Add `rest_validate_request_arg`. |
| Drafts in public list / slow list | Query args, `per_page` cap, per-item queries | Enforce visibility; cap; prime caches. |
| Duplicate records after timeout | Retried POST | Idempotency key. |
| Different object than authorized | Permission and handler read the id differently | Single accessor. |

## Worked decisions

Independently written illustrations, not executed tests.

### 1. Permission callback checks login but not the object

Problem: `'permission_callback' => static function () { return is_user_logged_in(); }` on a route that edits a post by id. Any subscriber can edit any post the handler touches. Fix: `current_user_can( 'edit_post', (int) $request['id'] )` and a 404 for missing objects. Verify with owner, other author, anonymous and subscriber; assert the post is unchanged after denied calls. Severity follows reachable impact (usually CRITICAL for content tampering by a low-privilege authenticated user); the fact that login is required does not reduce it.

### 2. Custom `sanitize_callback` silently disables schema validation

```php
'per_page' => array( 'type' => 'integer', 'maximum' => 100, 'sanitize_callback' => 'absint' ),
```
`500000` is accepted because only `absint` runs. Fix: add `'validate_callback' => 'rest_validate_request_arg'` (as core's collection params do) or remove the custom sanitizer so `rest_parse_request_arg` applies. Regression: request `per_page=500` expects `400 rest_invalid_param`.

### 3. Body-shadowed identifier

Permission callback uses `$request['id']` (body-first), handler uses `$request->get_url_params()['id']`. `PUT /acme/v1/events/5` with JSON `{"id": 9}` authorizes event 9 but edits 5, or the reverse. Fix: one accessor and declare `id` in `args` with `type: integer`. Regression: send conflicting URL and body ids; both must resolve to the same object or be rejected.

### 4. Public submission endpoint (benign pattern)

`'permission_callback' => '__return_true'` on `POST /acme/v1/contact`. Not a finding by itself. Review: payload bounds, spam/rate controls, no sensitive echo, email header injection safe (`wp_mail` with sanitized `Reply-To`), storage cap. If those are present, record the route as intentionally public. If none, report a WARNING for abuse exposure with the observed gap, not for the missing authentication.

### 5. Webhook receiver

Public route, signature required. Verify HMAC over the raw body (`$request->get_body()`) with `hash_equals`, timestamp window, replay store, then process asynchronously. A missing signature check on a state-changing webhook is a CRITICAL candidate; confirm the effect before labelling.

## Looks wrong but is fine

- `__return_true` on public read-only data; absent nonce validation in a custom handler under cookie auth; no `X-WP-Nonce` for Application Password calls; `WP_Error` returned (not thrown); unescaped strings in JSON; `permission_callback` that calls only `current_user_can( 'manage_options' )` for an admin-only action with no object; `403` to logged-in and `401` to anonymous callers.

## Verification recipes

- Unit/integration (preferred): `WP_UnitTestCase` (WordPress test suite) with `rest_do_request( new WP_REST_Request( 'PUT', '/acme/v1/events/' . $id ) )` and `wp_set_current_user()`; assert `->get_status()`, `->get_data()`, then re-read the object. Include anonymous, wrong-role, wrong-owner, malformed JSON (`set_body` + header), boundary values, and `per_page=101`.
- HTTP: `curl -i -H 'X-WP-Nonce: ...' --cookie ...` or `curl -u user:app-password https://site/wp-json/acme/v1/...` in a disposable site; check status, `Cache-Control`, `X-WP-Total*`, `Vary`.
- Route inventory: `wp eval 'foreach ( rest_get_server()->get_routes() as $r => $h ) { ... }'` on a disposable site prints `permission_callback` presence (execution loads project code; do not run untrusted bootstrap).
- Browser: Playwright request fixture (`@wordpress/e2e-test-utils-playwright` `RequestUtils`) for logged-in flows with the real nonce.
- Static: PHPCS WordPress ruleset, PHPStan with `szepeviktor/phpstan-wordpress`.

A pass shows the tested actors, inputs and WordPress version behave as asserted; it does not show other roles, multisite subsites, object-cache/CDN behavior or untested versions.

## Severity guidance

CRITICAL: reachable unauthorized write/read of protected data, privilege escalation, or an unauthenticated state-changing route with demonstrated impact. WARNING: schema bypass, unbounded collection, cache leakage risk, non-idempotent critical write, wrong status codes breaking clients. INFO: naming, optional fields. Missing authentication on intended public data is not a finding. Use candidate/insufficient evidence when auth model or CDN rules are unknown.

## Delivery evidence

Report actor/method/URL/body/status/response for each check, objects re-read after denied calls, executed vs unexecuted checks, and limits.

## Sources

Research date: 2026-10-08.

- Custom endpoints: https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/
- Authentication: https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/
- Schema: https://developer.wordpress.org/rest-api/extending-the-rest-api/schema/
- Controllers: https://developer.wordpress.org/rest-api/extending-the-rest-api/controller-classes/
