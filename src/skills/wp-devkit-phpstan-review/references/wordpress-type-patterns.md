# Typing WordPress boundaries without hiding bugs

Researched 2026-10-08. Contents: 1 Principle | 2 Return unions | 3 Hooks | 4 Options, meta and request data | 5 Database and queries | 6 Classes, globals and dynamic properties | 7 WooCommerce | 8 Generics and array shapes | 9 Review checks

## 1. Principle

A diagnostic is either a discovery problem (PHPStan cannot see a symbol), a documentation problem (the code is right, the contract is not written), or a real defect (a path can pass the wrong type). Fix in that order of suspicion reversed: look for the real defect first. Silencing with a cast, `@var` or ignore is correct only when you can state why the value cannot take the other types, ideally by narrowing in code (`is_wp_error()`, `is_string()`, `instanceof`, early return), because narrowing is checked and a cast is not.

## 2. Return unions

Many WordPress functions return a value or an error/false/null. Handle each member:

```php
$response = wp_remote_get( $url, array( 'timeout' => 5 ) );
if ( is_wp_error( $response ) ) {
	return $response;                // WP_Error: stop or translate
}
$code = wp_remote_retrieve_response_code( $response );   // int|string depending on stubs; cast after validation
if ( 200 !== (int) $code ) {
	return new WP_Error( 'acme_http', 'Unexpected status.' );
}
```

Common unions: `wp_remote_*` returns `array|WP_Error`; `wp_insert_post()` and `wp_update_post()` return `int|WP_Error` (on failure `0` when `$wp_error` is false, `WP_Error` when true); `get_post()` returns `WP_Post|array|null` by `$output`; `get_term()` `WP_Term|WP_Error|array|null`; `get_userdata()` and `get_user_by()` `WP_User|false`; `get_permalink()` `string|false`; `wp_get_attachment_image_src()` `array|false`; `get_option()`, `get_post_meta()`, `get_transient()` `mixed` (`false` when missing). Use `is_wp_error()` (the extension specifies the narrowing) rather than `instanceof` loops, and narrow `false|T` with an explicit check. `wp_die()`, `wp_send_json()` and `wp_nonce_ays()` terminate: the stubs and extension tell PHPStan, so code after them is unreachable; if a custom function ends the request, document it with `@return never`.

## 3. Hooks

- The extension validates hook callbacks and uses the first `@param` of the docblock above `apply_filters()` as the return type. Write the docblock accurately (types, array shapes), or the extension asserts the wrong type. For your own hooks, document each `@param` and keep the first param's type exactly the filtered value's type.
- Callback signatures: a callback registered with `add_filter( 'the_content', 'cb' )` must accept the declared number of args and return the filtered type; PHPStan can flag mismatches with the extension's rules. Specify `$accepted_args` (the fourth argument) when the callback takes more than one parameter.
- Closures and `[ $this, 'method' ]` callbacks are checked; string callables to functions defined conditionally may be reported unknown; `callable-string` types help.
- Untyped `apply_filters()` results are `mixed`: validate before use (`is_array()` and shape checks), because third-party code can return anything. That validation is correct runtime behavior, not noise.

## 4. Options, meta and request data

`get_option()`, `get_post_meta( $id, $key, true )`, `$_GET`/`$_POST`, `$request->get_param()` are `mixed`. At a boundary, validate and narrow once, then pass typed values inward:

```php
$raw   = get_option( 'acme_limit', 10 );
$limit = is_numeric( $raw ) ? max( 1, (int) $raw ) : 10;
```

Prefer small typed accessors (`acme_get_limit(): int`) so the narrowing sits in one place and the rest of the code is typed. For superglobals read through `wp_unslash()` and a sanitizer, or `filter_input()` with a filter; do not `(string)` a `mixed` that may be an array (PHP warns, PHPStan reports at higher levels). `register_meta()` / `register_setting()` with `type` and `sanitize_callback` give a single typed path.

## 5. Database and queries

`$wpdb->get_results()` returns `array|object|null` depending on `$output` (`OBJECT` default, `ARRAY_A`), `get_row()` `object|array|null`, `get_var()` `string|null`, `get_col()` `array`, `query()` `int|bool`, `insert()` `int|false`. Narrow with explicit checks and document row shapes: `@var list<object{id: numeric-string, label: string}>` after a `get_results( $sql, OBJECT )`; remember that MySQL numeric columns arrive as strings. `$wpdb->prepare()` may return `null`/`false`-like values on misuse in some versions: do not feed its result unchecked in security-sensitive code. `WP_Query::$posts` is `WP_Post[]|int[]` depending on `fields`; use `fields => 'ids'` to narrow (and check the array shape explicitly).

## 6. Classes, globals and dynamic properties

- `global $wpdb;` and `global $post;` are untyped to PHPStan unless annotated: add `/** @var wpdb $wpdb */` at the declaration (or prefer injecting dependencies). A global may legitimately be null (`$post` outside the loop): check it.
- PHP 8.2 deprecates dynamic properties: declare properties, or use `#[\AllowDynamicProperties]` for legacy classes, or `WeakMap` for data attached to objects you do not own. PHPStan reports undefined properties at level 2+.
- Singletons and static instances: declare return types as `static` or the class name; `@var` on `private static ?self $instance`.
- `$wp_filter`, `$wp_query` and similar globals are internals: avoid; if used, annotate.
- Legacy `compact()`/`extract()` hide variables from analysis; replace with explicit arrays.

## 7. WooCommerce

With the Woo stubs loaded, `wc_get_order()` returns `WC_Order|WC_Order_Refund|false`: check `instanceof WC_Order` before order-only methods; `wc_get_product()` returns `WC_Product|false|null`; `wc_get_orders()` is documented as `WC_Order[]|stdClass` (a `stdClass` with the orders and page counts when `paginate` is true) so narrow by the arguments you pass; `$order->get_meta()` is `mixed`. HPOS-safe code uses the CRUD objects, which also makes PHPStan's types useful. Hooks in Woo often pass loosely typed values: guard rather than cast.

## 8. Generics and array shapes

Since PHPStan 2.0 missing iterable and generic types are reported by identifier (`missingType.iterableValue`, `missingType.generics`) at level 6 and above. Express the real shape:

```php
/**
 * @param array{id: int, label?: string} $item
 * @return list<string>
 */
function acme_labels( array $item ): array { /* ... */ }
```

Useful types: `list<T>`, `non-empty-list<T>`, `array<string, T>`, `non-empty-string`, `numeric-string`, `positive-int`, `int<1, 100>`, `callable-string`, `class-string<T>`, `value-of<>`, `key-of<>`. Use `@phpstan-type` / `@phpstan-import-type` for shared shapes, `@template` for container classes, and `@phpstan-assert` / `@phpstan-assert-if-true` on validator helpers so narrowing flows to callers.

## 9. Review checks

1. Every `|false|null|WP_Error` return is handled by a branch, not a cast.
2. Hook docblocks are accurate; callbacks declare `$accepted_args`.
3. Boundaries (options, meta, request, remote data) narrow once into typed accessors.
4. Deliberate `@var`/`@phpstan-ignore` have identifiers, comments and a stated reason.
5. Regression: for each real defect fixed, a test or a PHPStan fixture that fails before and passes after. A clean run does not prove that narrowing logic is correct, only that types agree.

Sources: [phpstan-wordpress README](https://github.com/szepeviktor/phpstan-wordpress) | [extension.neon](https://github.com/szepeviktor/phpstan-wordpress/blob/2.x/extension.neon) | [PHPStan rule levels](https://phpstan.org/user-guide/rule-levels) | [PHPStan 2.0 upgrading notes](https://github.com/phpstan/phpstan/blob/2.1.x/UPGRADING.md) | [PHPDoc types](https://phpstan.org/writing-php-code/phpdoc-types) | [PHP 8.2 deprecations](https://www.php.net/manual/en/migration82.deprecated.php). | [WooCommerce wc-order-functions.php](https://github.com/woocommerce/woocommerce/blob/trunk/plugins/woocommerce/includes/wc-order-functions.php) | [WordPress post.php](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/post.php)
