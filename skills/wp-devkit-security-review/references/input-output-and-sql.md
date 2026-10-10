# Input, output, SQL and serialization

Researched 2026-10-08. Contents: 1 Input handling | 2 SQL | 3 Escaping by context | 4 DOM and JavaScript sinks | 5 HTML allowlists | 6 Serialization | 7 Review checks

## 1. Input handling

- Validate first (type, range, enum, length, existence, ownership), then sanitize what you accept, then escape at output. Validation rejects; sanitization normalizes. Neither authorizes.
- `$_GET`, `$_POST`, `$_REQUEST` and `$_COOKIE` are slashed by WordPress at load. Use `wp_unslash()` before sanitizing values read directly from them. Do not unslash values that arrive parsed through the REST API (`$request->get_param()`), `get_option()` or `get_post_meta()`; repeated unslashing strips legitimate backslashes. `$_SERVER` and `$_FILES` are not slashed.
- Pick the sanitizer that matches the data: `sanitize_text_field` (single line), `sanitize_textarea_field` (keeps newlines), `sanitize_email`, `sanitize_key`, `sanitize_title`, `sanitize_file_name`, `sanitize_url` (restored in WordPress 5.9 after a deprecation in 2.8; `esc_url_raw` on older versions), `absint`/`(int)`, `wp_kses_post` for allowed HTML. Numeric strings from forms: cast, then range-check.
- Enumerations: `in_array( $v, $allowed, true )` with strict comparison; loose comparison turns `0 == 'abc'` surprises into bypasses on PHP 7.
- Arrays: sanitize each element and the keys; `array_map( 'sanitize_text_field', wp_unslash( $_POST['ids'] ) )` fails if the value is a string (check `is_array`).
- REST: declare `args` with `type`, `enum`, `minimum`/`maximum`, `format`, and `sanitize_callback`/`validate_callback` per argument. Core JSON-schema validation runs before the callback; keep object ownership checks in the permission callback.
- `register_meta()`/`register_setting()` take `sanitize_callback`; use them so REST and `update_*_meta` share one path.

## 2. SQL

Bind values with `$wpdb->prepare()`; sanitization is not a substitute. Placeholders: `%d`, `%f`, `%s`, and `%i` for identifiers (WordPress 6.2+; `$wpdb->has_cap( 'identifier_placeholders' )` tells you at runtime). Do not quote placeholders; do not pass fewer or more arguments than placeholders; write literal percent signs as `%%`.

```php
// Values.
$rows = $wpdb->get_results( $wpdb->prepare(
	"SELECT id, label FROM {$wpdb->prefix}acme_items WHERE owner_id = %d AND status = %s",
	$owner_id,
	$status
) );

// LIKE: escape the user text, add wildcards to the argument, not the query.
$like = '%' . $wpdb->esc_like( $term ) . '%';
$rows = $wpdb->get_results( $wpdb->prepare(
	"SELECT id FROM {$wpdb->prefix}acme_items WHERE label LIKE %s",
	$like
) );

// IN list: one placeholder per element.
$ids          = array_map( 'absint', $ids );
$placeholders = implode( ',', array_fill( 0, count( $ids ), '%d' ) );
$rows         = $wpdb->get_results( $wpdb->prepare(
	"SELECT id FROM {$wpdb->prefix}acme_items WHERE id IN ($placeholders)",
	$ids
) );
```

Identifiers (column, table, sort direction) cannot be bound as values. Allowlist them (`$col = in_array( $col, array( 'created', 'label' ), true ) ? $col : 'created';`) or, on WordPress 6.2+, use `%i`. If the plugin supports older WordPress, use the allowlist. An empty IN list produces invalid SQL: guard it.

Convenience methods `$wpdb->insert()`, `update()`, `delete()` and `replace()` escape values and accept format arrays; `where` keys are column names that must come from code. `$wpdb->prepare()` returns `null` on invalid use (for example one argument used both as identifier and value) and raises a notice; treat a notice from `prepare()` as a defect and do not pass its result unchecked into query helpers in security-critical paths.

`WP_Query` and `get_posts()` arguments are parameterized internally, but `orderby` and `meta_key` from user input need an allowlist, and `suppress_filters`, `posts_where`/`posts_clauses` filters that concatenate request data are SQL sinks.

Review notes. Dynamic table names from `$wpdb->prefix . $constant` are safe. A query that uses `$wpdb->posts` with a prepared value is safe. Echoing a SQL error (`$wpdb->last_error`, `show_errors()`) is an information disclosure, separate from injection. A string built with `esc_sql()` is a weaker, context-dependent control than `prepare()`: report the missing parameterization only if you can show a context (unquoted numeric position, identifier, `LIKE` wildcard) where `esc_sql()` does not protect.

## 3. Escaping by context

Escape at the final sink, matching the context. Do not escape on save to "pre-protect" output.

| Output context | Function |
|---|---|
| Text between tags | `esc_html()`, `esc_html__()`, `esc_html_e()` |
| Attribute value | `esc_attr()`, `esc_attr__()` |
| URL in `href`/`src`/`action` | `esc_url()`; stored URL: `esc_url_raw()` |
| `<textarea>` | `esc_textarea()` |
| Inline JS string | `wp_json_encode()` / `wp_add_inline_script()` with `wp_json_encode` data; `esc_js()` only for legacy inline handler strings |
| Data for scripts | `wp_localize_script()` (core runs `html_entity_decode` on scalar values, then `wp_json_encode` with `JSON_HEX_TAG`; it does not entity-encode, so it is safe only for data you never print as HTML later) or `wp_add_inline_script( $h, 'const cfg = ' . wp_json_encode( $data ) . ';', 'before' )` |
| Allowed rich HTML | `wp_kses( $html, $allowed )`, `wp_kses_post()`, `wp_kses_data()` |
| XML | `esc_xml()` |

Wrong-context examples worth catching: `esc_html()` inside an attribute that contains a URL (does not block `javascript:`); `esc_attr()` inside `<script>`; `echo '<a href="' . esc_url( $u ) . '" onclick="go(\'' . esc_js( $x ) . '\')">'` mixes two contexts (prefer a data attribute and external JS). `esc_url()` rejects non-allowed protocols; it does not make a URL an allowed destination.

Translations: `printf( esc_html__( 'Hello %s', 'td' ), esc_html( $name ) )` escapes both; `echo __( 'x' )` leaves translator-controlled markup unescaped, and translations can come from community packs.

Output via templating: `get_the_title()` and `the_content()` are already filtered; `get_the_title()` is not escaped for attributes, use `the_title_attribute()` or `esc_attr()`. Block `render_callback` output is the plugin's responsibility. `wp_kses_post` on attacker-controlled HTML for contributors is acceptable; for lower roles use a smaller allowlist.

## 4. DOM and JavaScript sinks

- Reportable sinks: `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, jQuery `.html()`/`.append( string )`, React `dangerouslySetInnerHTML`, `eval`/`new Function`, `setTimeout( string )`, `location = userValue`, `window.open`. Source: URL parameters, `location.hash`, `postMessage` without origin check, REST values, localStorage, and server-printed data.
- Use `textContent`/`.text()` for text, build nodes, or sanitize with a vetted library before inserting HTML. Validate URL schemes (`http:`, `https:`, `mailto:`) before assigning to `href`.
- Block editor: block attributes are data; the saved HTML and `render_callback` are the sinks. `RawHTML`/`dangerouslySetInnerHTML` of attribute values in `edit` is editor-only XSS and still matters when a lower role can author the block.
- `postMessage` listeners must check `event.origin` and not use `*` as the target for sensitive payloads.

## 5. HTML allowlists

`wp_kses()` with an explicit element/attribute array is a real allowlist. Keep `style`, `on*` attributes and `javascript:` protocols out; the `style` attribute is filtered by `safecss_filter_attr()` but is still rarely needed. A filter such as `kses_allowed_protocols` or `wp_kses_allowed_html` that adds `data:` or `script` widens the policy for all callers: review such filters globally. Users with `unfiltered_html` bypass kses on post content; single-site administrators and editors have it by default, which is why stored XSS by those roles is usually INFO, while stored XSS from contributors or authors on multisite is not.

## 6. Serialization

- Never `unserialize()` untrusted input. PHP's manual states `allowed_classes` does not make it safe for untrusted input. For data that must be revived, use JSON. `unserialize( $s, array( 'allowed_classes' => false ) )` plus `max_depth` (PHP 7.4+) limits damage for internal data; the second argument must be an options array, not a boolean.
- `maybe_unserialize()` passes no options, so it can instantiate any loaded class. It is fine for core-written option and meta values; it is a PHP object injection candidate when the serialized string comes from a request, an import file, a comment/user meta field a low role can write, or a remote service. Gadget chains then depend on the classes in the autoloader (vendor libraries, WooCommerce, other plugins), so show a reachable `__destruct`/`__wakeup`/`__toString` gadget or label the finding probable.
- `serialize()` output stored in meta is not a trust boundary by itself; HMAC-sign values that cross one.
- Search-and-replace tooling must use serialization-aware routines (see the migration skill).

## 7. Review checks

1. Every `$_*` read has a validation and sanitizer matching its use; `wp_unslash()` applied exactly once for superglobals.
2. Every dynamic SQL part is a bound value, an allowlisted identifier or a `%i` placeholder.
3. Every echo, attribute and JS sink uses the escaper for its context at the sink.
4. No untrusted `unserialize`; no HTML sink fed by unescaped request, REST or storage data.
5. Regression: harmless markers (`"'<svg onload=window.__xss=1>`) do not execute and appear escaped; a quote in a SQL value returns correct rows and no error.

Sources: [Escaping](https://developer.wordpress.org/apis/security/escaping/) | [wpdb::prepare](https://developer.wordpress.org/reference/classes/wpdb/prepare/) | [Sanitizing data](https://developer.wordpress.org/apis/security/sanitizing/) | [PHP unserialize](https://www.php.net/manual/en/function.unserialize.php) | [REST routes and endpoints](https://developer.wordpress.org/rest-api/extending-the-rest-api/routes-and-endpoints/).
