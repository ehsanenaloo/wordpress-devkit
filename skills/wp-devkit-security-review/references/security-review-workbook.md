# Security review workbook

Apply [the engineering contract](engineering-contract.md) first.

Contents: 1 Method | 2 Severity calibration | 3 Finding template | 4 Looks wrong but is fine | 5 Looks fine but is wrong | 6 Regression design | 7 Acceptance checks | 8 Sources

## 1. Method

1. Scope: list entrypoints for the target (see the SKILL workflow). Record WordPress, PHP, WooCommerce and plugin versions from the project, not from assumptions.
2. Per entrypoint write one line: `actor -> input -> controls on path -> sink`. A finding exists only if that line ends in an uncontrolled sink.
3. Read the helper that wraps the control (`my_plugin_can_edit()`, `Base_Controller::check()`); a grep that finds no `current_user_can` in the handler says nothing if the base class or `permission_callback` does the check.
4. Decide the actor class that matters: anonymous, subscriber/customer, contributor, author, editor, shop manager, administrator, super admin, another site in a network, an external system holding a webhook secret.
5. Decide impact by what the actor gains beyond their role: read another user's data, write an object they do not own, escalate a role, execute script in an admin's browser, reach an internal host, run code, or exhaust a resource.
6. If the path cannot be completed from the source (dynamic dispatch, config-driven callbacks, a closed-source dependency), report an insufficient-evidence candidate and name the exact missing fact.

## 2. Severity calibration

Follow contract item 5. These anchors illustrate demonstrated impact; they are not a CVSS substitute.

| Demonstrated impact | Severity |
|---|---|
| Unauthenticated or low-role code execution, arbitrary file write in a web-reachable path, SQL injection with data read or write, role escalation to administrator, authentication bypass | CRITICAL |
| Stored XSS reachable by a low role and rendered to an administrator; wrong-owner read or write of private objects (IDOR); SSRF reaching internal addresses; secrets exposed in a reachable artifact | CRITICAL when exploit path is complete, otherwise WARNING |
| CSRF on a state change that needs a victim with a privileged session; reflected XSS needing a crafted link; missing rate limit on login or reset; verbose error disclosure with limited data | WARNING |
| Defense in depth missing, no demonstrated exploit: absent security headers, `esc_html` on an already-safe integer, hard-coded fixed `include` | INFO |

Rules: authentication does not by itself downgrade a severe issue (a subscriber who can edit options is still CRITICAL). Do not raise severity for a pattern you could not complete. Do not assign a CWE to a style concern. CWE hints that fit: SQL injection CWE-89, stored/reflected XSS CWE-79, CSRF CWE-352, missing authorization CWE-862, incorrect authorization CWE-863, IDOR CWE-639, SSRF CWE-918, path traversal CWE-22, unrestricted upload CWE-434, deserialization CWE-502, open redirect CWE-601.

## 3. Finding template

```text
[SEVERITY][confidence: confirmed|probable|candidate] Short title
Location : path/file.php:LINE (and the sink at LINE)
Actor    : e.g. authenticated subscriber
Trigger  : request or event, with the controlled parameter
Path     : source -> transformations -> (missing/ineffective control) -> sink
Impact   : what the actor gains beyond their role; data or tenant affected
Evidence : what was read or run; what was NOT run
Fix      : minimal change at the failing boundary
Regression: three-actor test and expected statuses
```

Candidates use the same fields plus `Missing evidence:`. Never paste real secrets or personal data; redact to prefix and length.

## 4. Looks wrong but is fine

- `$wpdb->get_results( $sql )` with no inline `prepare()`: the query may be prepared in a helper, or built only from `$wpdb->posts` and integers cast with `absint()`. Trace the executed string. This is no automatic CWE-89; a missing `prepare` on a line is a lead only.
- `echo $var;` where `$var` is `absint()`, a boolean string, or built from an `esc_*` call earlier on the same path. Escaping at construction is acceptable when the variable is named and used as already-safe; late escaping is the preferred convention, not the vulnerability test.
- `wp_ajax_nopriv_*` or `'permission_callback' => '__return_true'` on a deliberate public read or public submission (newsletter, contact form, public search). Check abuse limits and what the handler writes, not the registration.
- `wp_verify_nonce` missing on a pure GET read, or on a REST route that uses cookie authentication, where core enforces the `X-WP-Nonce` check for cookie requests and treats failures as logged out.
- A nonce on a handler that also checks `current_user_can()` and ownership: correct layering; do not report "nonce is not authorization".
- `unserialize()` or `maybe_unserialize()` on data only the plugin itself writes and no user-controlled path reaches (verify who can write that option or meta).
- `file_get_contents( __DIR__ . '/tpl.php' )`, `include` of a fixed or allowlisted path, `wp_redirect( admin_url(...) )` to a constant destination, `wp_redirect()` after `wp_validate_redirect()`.
- Secret-shaped strings: placeholders, test fixtures, hashes, public keys, publishable keys, UUIDs. Classify before reporting.
- `eval`, `exec` or `system` in a vendored dev tool outside the shipped package.
- JSON responses containing user-controlled strings: not XSS unless a consumer injects them into the DOM as HTML.
- Admin-only `manage_options` pages echoing option values: still escape, but an administrator attacking themselves is INFO unless low-role users can write that option.

## 5. Looks fine but is wrong

- `check_ajax_referer()` as the only guard on a state change: any logged-in user, including a subscriber, holds a valid nonce.
- `is_admin()` as an authorization check: it only reports whether an admin screen is requested; `admin-ajax.php` also returns true for anonymous callers.
- `current_user_can( 'edit_posts' )` when the code then edits a specific post: check `current_user_can( 'edit_post', $id )` so ownership and status map correctly.
- `sanitize_text_field()` on a value later concatenated into SQL or used as an ID or path.
- `esc_attr()` around a URL, or `esc_html()` inside a `<script>`, `href="javascript:"` or inline event handler: wrong context.
- `$_FILES['f']['type']` used for validation; the client sets it.
- `wp_remote_get( $user_url )` guarded by a regex on the hostname; compare `wp_safe_remote_get`, redirects and resolved address policy.
- `hash == $given` for HMAC or token comparison: use `hash_equals()`.
- Admin-post or AJAX handler that returns early with `wp_send_json_error()` but does not `wp_die()`/`return` before the write.
- REST `sanitize_callback` treated as validation, or `args` declared but `permission_callback` returns `true` for a private object.

## 6. Regression design

Prefer an integration test (PHPUnit with the WordPress test suite, or a REST dispatch via `rest_do_request()`), otherwise Playwright, otherwise WP-CLI `wp eval` in a disposable site.

1. Owner: valid request succeeds and the record changes as intended.
2. Wrong owner (same role, other object, or lower role): expected 401/403 (REST) or `wp_die` 403; assert the record is unchanged, not just that an error text appeared.
3. Anonymous: expected rejection, or the documented public behavior only.
4. Valid nonce with the wrong actor still fails.
5. Injection markers that are harmless and distinctive: `"'<img src=x onerror=window.__xss=1>` for output sinks, a value with a quote and non-ASCII for SQL; assert the marker is escaped in the response and that no executable sink saw it.
6. For multisite, repeat steps 2 and 3 across sites.

Test-owned data may be reset; production and shared fixtures follow their own recovery policy.

## 7. Acceptance checks

| Check | Command or method | Passing proves | Does NOT prove |
|---|---|---|---|
| PHPCS security sniffs | `phpcs --standard=WordPress-Extra` (WordPress Coding Standards includes escaping, nonce and prepared-SQL sniffs) | Flagged patterns reviewed or fixed | Absence of authorization defects; sniffs are heuristic |
| Static analysis | `phpstan analyse` with the project config | Type-level contract holds | Security; types do not model permissions |
| Dependency audit | `composer audit --locked`, `npm audit --omit=dev` | No known advisories in the audited locks at that date | Reachability, WordPress plugin advisories, zero-days |
| Core integrity | `wp core verify-checksums`, `wp plugin verify-checksums --all` | WordPress.org-hosted files unmodified | Premium/custom plugins, database malware, stolen credentials |
| Three-actor regression | PHPUnit or Playwright | The specific path is closed | Other paths to the same sink |
| Staged DAST | Allowlisted host, bounded requests | Reachability of probed paths | Coverage of logic flaws |

Record tool versions, exit status and the unexecuted checks.

## 8. Sources

Research date: 2026-10-08. [Security principles](https://developer.wordpress.org/apis/security/) | [Nonces](https://developer.wordpress.org/apis/security/nonces/) | [Escaping](https://developer.wordpress.org/apis/security/escaping/) | [REST authentication](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/) | [register_rest_route](https://developer.wordpress.org/reference/functions/register_rest_route/) | [OWASP Top 10](https://top10.owasp.org/2025) | [CWE](https://cwe.mitre.org/).
