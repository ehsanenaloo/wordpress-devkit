# Access control, CSRF and authentication

Research date: 2026-10-08. Contents: 1 Layers | 2 Capability and ownership | 3 Entrypoint patterns | 4 Nonces and CSRF | 5 Authentication models | 6 Privilege and role writes | 7 Multisite | 8 Review checks

## 1. Layers

Keep four questions separate; each needs its own control.

| Question | Control |
|---|---|
| Who is the caller? | Authentication: cookie session, application password, OAuth/JWT plugin, webhook signature |
| May this role do this kind of action? | Capability: `current_user_can( 'manage_options' )` |
| May they do it to this object or tenant? | Object capability or ownership: `current_user_can( 'edit_post', $id )`, `$object->user_id === get_current_user_id()` |
| Did they intend it (session-based requests)? | Nonce: CSRF defense only |

A nonce answers only the last question. WordPress documents that nonces must not be relied on for authentication, authorization or access control; they are not single-use and expire after 12 to 24 hours by default (`nonce_life`, two ticks). Logged-out visitors all share user ID 0 and receive the same nonce, so a guest nonce is no per-visitor protection.

## 2. Capability and ownership

- Check the narrowest capability that matches the action. Prefer meta capabilities that take an object ID (`edit_post`, `delete_post`, `read_post`, `edit_user`, `delete_user`, `promote_user`, `edit_term`) so `map_meta_cap` applies the post type, status, authorship and multisite rules.
- A generic capability (`edit_posts`) before editing a specific post is an IDOR candidate: any contributor passes it for any post ID.
- Custom post types: set `capability_type` and `map_meta_cap => true`, or custom `capabilities`; otherwise the CPT may map to `post` capabilities unintentionally.
- Never test roles by name (`in_array( 'administrator', $user->roles )`); roles are editable and capabilities are the contract. `is_admin()` reports the admin screen context, and is also true for `admin-ajax.php`, so it never authorizes.
- `is_super_admin()` and `manage_network_*` capabilities gate network-wide actions; `manage_options` on a single site of a network is not network authority. Core removes `unfiltered_html` from non-super-admins on multisite; code that assumes administrators can post raw HTML breaks that rule.
- Check read access too: private posts, draft previews, order data, user lists, exports and search endpoints.

## 3. Entrypoint patterns

**REST.** Every route needs `permission_callback`. Since WordPress 5.5 a missing callback raises a `_doing_it_wrong` notice; an intentionally public route uses `'permission_callback' => '__return_true'` and should still bound input and output. A callback that returns `true` for routes that read or write private objects, or that only checks `is_user_logged_in()`, is an authorization gap. `args` with `validate_callback`/`sanitize_callback` do not authorize. Cookie-authenticated requests need the `wp_rest` nonce (`X-WP-Nonce` header or `_wpnonce`); without it core treats the request as logged out, so a missing nonce breaks the request instead of opening it. Object ownership must be checked inside the callback or in a permission callback that reads the `id` param.

```php
register_rest_route( 'acme/v1', '/notes/(?P<id>\d+)', array(
	'methods'             => WP_REST_Server::EDITABLE,
	'callback'            => 'acme_update_note',
	'permission_callback' => static function ( WP_REST_Request $request ) {
		return current_user_can( 'edit_post', (int) $request['id'] );
	},
	'args'                => array(
		'id' => array( 'type' => 'integer', 'required' => true ),
	),
) );
```

**admin-ajax.** `wp_ajax_{action}` runs for logged-in users of any role; `wp_ajax_nopriv_{action}` runs for anyone. Registering only the `wp_ajax_` hook is not an access control for "admins only". The handler must check capability, nonce and ownership, then `wp_send_json_*` (which ends the request) or `wp_die()`.

**admin-post.** `admin_post_{action}` and `admin_post_nopriv_{action}`; same rules. Redirect after POST with `wp_safe_redirect()`.

**Settings and forms.** `register_setting()` with a `sanitize_callback` and the settings page capability; options saved through custom handlers need the same check as any mutation. `init`, `admin_init`, `template_redirect` and `wp_loaded` handlers triggered by `$_POST['action']` are common sources of unauthenticated writes because they run for everyone.

**Shortcodes and blocks.** Attributes are author-controlled, not attacker-controlled by default, but contributors can place shortcodes. Escape attribute values on output; do not let a shortcode attribute select a post ID, file or query without a read-permission check.

**Cron and WP-CLI.** Run without a user. Do not let them process data across tenants without scoping, and do not reuse their code path from a public handler.

## 4. Nonces and CSRF

- CSRF requires an authenticated browser session that the attacker can ride. Assess against the real session model: cookie-authenticated admin-post/AJAX needs a nonce; Bearer/application-password API calls are not CSRF-prone because the browser does not attach them automatically.
- Create with `wp_create_nonce( 'acme_save_note_' . $id )` or `wp_nonce_field()`; verify with `check_admin_referer()` / `check_ajax_referer()` / `wp_verify_nonce()`. `wp_verify_nonce()` returns 1 or 2 (tick) or false; test with `false === ...`, not truthiness of a stored value. Bind the action string to the object so a nonce for one record is not valid for another.
- `check_ajax_referer( 'action', 'nonce', false )` returns false instead of dying; the handler must stop itself.
- GET requests that change state (delete links) need a nonce too (`wp_nonce_url()`).
- Nonce checks cannot be turned into idempotency or replay protection. A repeated valid request succeeds for the nonce lifetime.
- Cached pages that embed a nonce (full-page cache, CDN) serve stale nonces to other users; test with the cache enabled.
- Guest forms: the shared guest nonce gives no CSRF value; use rate limits, honeypot/captcha and idempotency keys as abuse controls, and say so instead of reporting a "nonce bypass".

## 5. Authentication models

- Application passwords (WordPress 5.6) work with Basic Auth over HTTPS and are scoped to a user, not a capability subset; plugins can restrict them. Review who can create them and whether routes assume cookie-only callers.
- Token/JWT plugins: check signature algorithm pinning (`alg` fixed, no `none`), expiry, audience, revocation, and that tokens are not logged.
- Webhooks: verify an HMAC over the raw body with `hash_hmac()`, compare with `hash_equals()`, check a timestamp window and replay identifier, and use a per-integration secret. Do not authenticate by IP alone unless the provider documents stable ranges.
- Passwords: since WordPress 6.8 core hashes new passwords with bcrypt (SHA-384 pre-hash) and keeps verifying legacy phpass hashes; application passwords and reset keys moved to BLAKE2b via sodium. Do not report a phpass hash on an old row as a defect; do report custom `md5`/`sha1` password handling.
- Login/reset/registration: look for user enumeration (different messages, REST `/wp/v2/users` exposure, author archives `?author=N`), predictable reset tokens (use core `get_password_reset_key`), and missing throttling. Mark enumeration by author archive as INFO unless usernames are also credentials.
- Session handling: `wp_set_auth_cookie()` called from custom login code needs the same safeguards as `wp_signon()` (rate limiting, 2FA hooks). `wp_set_current_user()` in a request handler is an impersonation primitive: confirm the identity source.

## 6. Privilege and role writes

High-impact sinks: `wp_insert_user`/`wp_update_user` with a request-supplied `role`, `$user->set_role()`, `add_cap`, `update_user_meta( $id, 'wp_capabilities', ... )`, `update_option( 'default_role', ... )`, `users_can_register`. Any path where a non-administrator controls those values is CRITICAL. Registration forms must fix the role server side; a hidden `role` field is attacker-controlled. Meta-update endpoints must allowlist keys (`update_user_meta( $id, $_POST['key'], ... )` allows capability writes).

Mass assignment: REST/AJAX handlers that loop over request keys into `update_post_meta`/`update_option` need an allowlist of keys and per-key capability.

## 7. Multisite

- Resolve the site once and keep the context: `switch_to_blog()` without `restore_current_blog()` (including on early return) leaks context into later code; nested switches must unwind in order.
- Capability checks inside a switched context apply to the switched site; check before switching when the actor's rights on the target site matter.
- Network-wide options (`get_site_option`) vs site options: a site admin must not modify network options. Super-admin-only actions need `is_super_admin()` or `manage_network_options`.
- Cache keys, transients and upload paths must include the blog ID; a shared key serves one site's data to another.
- Test cross-site access with a user who is administrator on site A and has no role on site B.

## 8. Review checks

1. Every state-changing entrypoint has: authentication assumption, capability or ownership, and (for cookie sessions) intent.
2. Object IDs from the request are authorized as objects, not as role.
3. `permission_callback` is never `__return_true` for private data or writes.
4. No role names, no `is_admin()` as authorization.
5. Webhook and token verification is constant-time and replay-aware.
6. Regression: owner passes; wrong owner with a valid nonce fails with the record unchanged; anonymous fails or gets only the public behavior.

Sources: [Nonces](https://developer.wordpress.org/apis/security/nonces/) | [REST authentication](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/) | [register_rest_route](https://developer.wordpress.org/reference/functions/register_rest_route/) | [WP 6.8 bcrypt](https://make.wordpress.org/core/2025/02/17/wordpress-6-8-will-use-bcrypt-for-password-hashing/) | [Checking capabilities](https://developer.wordpress.org/plugins/security/checking-user-capabilities/). | [core capabilities.php (unfiltered_html)](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/capabilities.php) | [core pluggable.php (wp_hash_password)](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/pluggable.php)
