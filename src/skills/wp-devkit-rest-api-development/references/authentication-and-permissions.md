# Authentication, permissions and exposure

Contents: authentication models; cookie + nonce behavior; Application Passwords; 401 vs 403; permission_callback patterns; object-level checks; public routes; CORS and exposure; abuse controls; looks wrong but is fine; failure symptoms; sources.

Contract reminders: a nonce is not authorization; a public route is not automatically a vulnerability; assess impact, not pattern.

## Authentication models

| Model | How the caller proves identity | Request-intent (CSRF) defence |
|---|---|---|
| Cookie (browser, wp-admin, block editor, theme JS) | WordPress login cookies | `wp_rest` nonce via `X-WP-Nonce` header or `_wpnonce` param; verified by core |
| Application Passwords (WordPress 5.6+) | HTTP Basic `username:application-password` over HTTPS | Not cookie-based, so not CSRF-prone; no nonce |
| Plugin-provided (OAuth 1.0a, JWT, mTLS, signed webhooks) | Plugin-defined, via `determine_current_user` or `rest_authentication_errors` | Plugin-defined; verify its own replay and expiry rules |
| Anonymous | none | n/a |

## Cookie authentication (verified in `rest_cookie_check_errors()`)

- Core reads `_wpnonce` from the request or the `X-WP-Nonce` header. With no nonce, core sets the current user to 0 and the request proceeds unauthenticated, even if valid login cookies were sent. A logged-in browser script that forgets the header therefore gets `401 rest_forbidden` (or sees only public data), not a CSRF error.
- With a nonce that fails `wp_verify_nonce( $nonce, 'wp_rest' )` the response is `403 rest_cookie_invalid_nonce` ("Cookie check failed"). A nonce older than its lifetime (default 12 hours with two ticks) is a common cause on long-lived pages and cached HTML: the page embeds a stale nonce.
- A good nonce is refreshed in the `X-WP-Nonce` response header; long-lived apps should adopt it.
- Custom endpoints must not re-verify `wp_rest` nonces; core already does. Add a separate nonce only for a distinct non-REST form action.
- Client wiring: in the block editor use `wp.apiFetch` (it adds the root URL and nonce middleware when the page enqueues `wp-api-fetch` and sets `wpApiSettings`/`createNonceMiddleware`); in your own script localize `wp_create_nonce( 'wp_rest' )` and send `X-WP-Nonce`. Pages served from a page cache must not bake a user-specific nonce into shared HTML.

## Application Passwords (verified)

- Available when the site is served over HTTPS or the environment type is `local` (`wp_get_environment_type()`), filterable with `wp_is_application_passwords_available` (site) and `wp_is_application_passwords_available_for_user` (user). Plain HTTP production sites do not offer them by default; do not "fix" by forcing the filter true on HTTP, because Basic credentials then travel in clear text.
- They authenticate as the user and inherit that user's capabilities. Create a dedicated least-privilege user for integrations; revoke passwords per integration; they appear in the profile screen with last-used data.
- Wrong or revoked credentials give `401` (`incorrect_password`/`invalid_username` family); a valid user lacking capability gives `403 rest_forbidden`. Different statuses are diagnostic: 401 means identity failed; 403 means identity succeeded and policy refused.
- A reverse proxy or CGI/FastCGI setup that strips the `Authorization` header is the usual cause of Application Passwords "not working" while cookies work. Confirm with a request to `/wp-json/wp/v2/users/me` and inspect whether `HTTP_AUTHORIZATION` reaches PHP; fix at the server (pass the header) rather than weakening authentication.

## 401 vs 403 (confirmed: `rest_authorization_required_code()`)

Logged-in users get 403, anonymous users get 401. Use it so clients can distinguish "authenticate" from "not allowed". Do not return 404 to hide existence unless that is a deliberate documented policy.

## `permission_callback`

- Runs after authentication, receives the `WP_REST_Request`, may return `true`, `false` (default `rest_forbidden`) or a `WP_Error` with a `status`. A missing callback skips the check (core treats an empty callback as allowed) and triggers a notice from 5.5.
- It runs before the handler but after argument validation and sanitization (`WP_REST_Server::dispatch()` validates, then `respond_to_request()` calls the permission callback), and it is skipped when validation already failed, so a malformed request gets 400 before any permission check. Do not rely on validation for authorization, and read sanitized values in the callback.
- Capability checks:
  - Type-level actions (create): `current_user_can( 'edit_posts' )` or the post type's `create_posts` capability from `get_post_type_object()->cap`.
  - Object actions: `current_user_can( 'edit_post', $id )`, `'delete_post'`, `'read_post'`, `'edit_user'`, `'edit_term'` with the object id so `map_meta_cap` applies ownership and status rules. A role/cap check on the generic capability alone (`edit_posts`) lets a contributor edit another author's post.
  - Validate that the object exists first (`get_post( $id )` returns null) to return `404` rather than a misleading `403`.
- Return granular errors: `new WP_Error( 'acme_forbidden', __( '...', 'acme' ), array( 'status' => rest_authorization_required_code() ) )`.

```php
'permission_callback' => static function ( WP_REST_Request $request ) {
	$post = get_post( (int) $request['id'] );
	if ( ! $post || 'acme_event' !== $post->post_type ) {
		return new WP_Error( 'acme_not_found', __( 'Not found.', 'acme' ), array( 'status' => 404 ) );
	}
	return current_user_can( 'edit_post', $post->ID )
		? true
		: new WP_Error( 'acme_forbidden', __( 'You cannot edit this event.', 'acme' ), array( 'status' => rest_authorization_required_code() ) );
},
```

## Object-level checks inside the handler

Authorize every referenced object, not only the route id: a payload `parent_id`, `author`, `attachment_id`, `term_ids` or `user_id` also needs a capability check, and an author/owner change needs `edit_others_posts`/`promote_users`-style capability. Re-read the object after the write attempt in tests to prove denied calls changed nothing.

## Public routes

`__return_true` is correct for data that is public by design. Assess: what is exposed (does the response include drafts, emails, internal IDs, user enumeration), what side effects exist (writes, emails, remote calls, expensive queries), and abuse controls. Public writes (forms, webhooks) need their own control: signature verification for webhooks (HMAC over the raw body with a timestamp, constant-time compare via `hash_equals`), CAPTCHA/honeypot or rate limiting for forms, payload size limits, idempotency keys.

## Exposure and CORS

- Core's `/wp/v2/users` exposes public author data (slug, name) to anonymous callers when the user has published posts; this is deliberate core behavior. Treat enumeration concerns as hardening, not as a defect in your plugin, unless your own endpoint leaks more.
- To restrict all REST to authenticated users, hook `rest_authentication_errors`: return the incoming error unchanged if it is not null; otherwise return a `WP_Error` with `status` 401 when `! is_user_logged_in()`. This breaks public features (block editor previews are authenticated; the front-end search, oEmbed discovery, contact forms and many plugins use public routes), so scope it by route namespace.
- CORS (confirmed in `rest_send_cors_headers()`): core echoes any request `Origin` in `Access-Control-Allow-Origin` and sends `Access-Control-Allow-Credentials: true`. That is tolerable only because cookie-authenticated REST calls need the `wp_rest` nonce, which a foreign origin cannot read. Consequences: any custom authentication that accepts cookies or ambient credentials without an unguessable per-session token turns this into a cross-origin read/write hole; do not add it. For cross-origin clients use Application Passwords or token auth, and to restrict origins, replace core's `rest_send_cors_headers` callback on `rest_pre_serve_request` with your own allow-list (`rest_allowed_cors_headers` only filters the allowed request headers, not origins).
- `rest_endpoints` filter can unset routes; `show_in_index => false` is not access control.

## Abuse controls

Core has no rate limiting. Apply limits at the edge (WAF/reverse proxy) or with a keyed transient/object-cache counter (`wp_cache_incr` with expiry) on expensive or unauthenticated writes; cap `per_page`; avoid unbounded `search` queries; validate array sizes (`maxItems`).

## Looks wrong but is fine

- `__return_true` on a read-only route returning already-public data.
- No nonce check in a custom endpoint called with cookies (core verifies).
- `current_user_can( 'read' )` on a route that returns only the caller's own data derived from `get_current_user_id()`.
- Application Password requests carrying no `X-WP-Nonce`.
- `403` for a logged-in user, `401` for anonymous.

## Failure symptoms

| Symptom | Evidence | Fix direction |
|---|---|---|
| Logged-in script gets 401 | Missing `X-WP-Nonce` (user forced to 0) | Send the nonce; refresh from response header |
| 403 `rest_cookie_invalid_nonce` | Stale nonce from cached page | Do not cache nonce-bearing HTML; refresh nonce |
| Basic auth 401 only through the proxy | `Authorization` not forwarded | Server config; not a code change |
| User edits another user's object | Generic cap or none in permission callback | `edit_post` with id; re-read after denied call |
| Different object edited than authorized | Permission reads URL id, handler reads body id | Read the id one way (parameter order is body-first) |

## Sources

Research date: 2026-10-08.

- Authentication: https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/
- `rest_authentication_errors`: https://developer.wordpress.org/reference/hooks/rest_authentication_errors/
- Custom endpoints (permission callbacks): https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/
- Core source read (trunk): `rest_cookie_check_errors`, `rest_authorization_required_code`, `wp_is_application_passwords_supported`.
