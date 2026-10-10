# Hooks, callbacks and request context

Contents: load order; priority and arguments; filter contract; removal; recursion; custom hooks and BC; request-context detection; translations timing; debugging; looks wrong but is fine; sources.

## Load order that decides most timing bugs

mu-plugins -> `muplugins_loaded` -> network-active plugins -> active plugins -> `plugins_loaded` -> `setup_theme` -> `after_setup_theme` -> `init` -> `wp_loaded` -> then request specific: `rest_api_init`, `admin_menu`/`admin_init`, `wp_enqueue_scripts`/`admin_enqueue_scripts`, `template_redirect`.

- Register post types, taxonomies, blocks and shortcodes on `init`. Add other plugins' integration code on `plugins_loaded` (or later) so their symbols exist; core functions such as `current_user_can()` need the user, which is available from `init` (not at plugin load).
- Do not call `wp_get_current_user()`, `is_user_logged_in()` or `current_user_can()` at file load or on `plugins_loaded`; the user may not be determined yet.
- Do not translate (`__()`, `esc_html__()`) before `init` (see below).

## Priority and accepted arguments

- Default priority is 10, default `accepted_args` is 1. Lower numbers run first; equal priorities run in registration order.
- A callback that needs more than the first argument must declare the count: `add_filter( 'the_title', 'acme_title', 10, 2 )`. Without it PHP raises an `ArgumentCountError` for required parameters (PHP 7.1+), or the extra data is absent.
- Do not pick extreme priorities (`PHP_INT_MAX`, `-1`) to win ordering fights without recording why; they hide a dependency. Prefer a documented hook of your own.

## Filter contract

- A filter callback must return the value (or a deliberate replacement) on every path, including early returns. A missing `return` yields `null` downstream.
- Preserve the input type. A filter documented to receive an array must return an array; validate untrusted shapes (`is_array`) before appending.
- Actions ignore return values. Returning from an action callback is dead code, not a bug.
- Shape (broken vs fixed):

```php
add_filter( 'body_class', static function ( $classes ) {
	if ( is_singular( 'acme_event' ) ) {
		$classes[] = 'acme-event';
	}
	return $classes; // every branch returns.
} );
```

## Removing callbacks

`remove_action()`/`remove_filter()` succeed only when hook name, callback identity and priority all match the registration, and when the removal runs after the add and before the hook fires.

| Registered as | Remove with |
|---|---|
| Named function `'acme_cb'` | `remove_action( 'init', 'acme_cb', $priority )` |
| Static method `array( 'Acme', 'run' )` or `'Acme::run'` | the same array/string |
| Instance method `array( $obj, 'run' )` | the same instance (store it or expose an accessor); `new Acme()` creates a different object and removes nothing |
| Closure / arrow function | Only with a reference you kept. Anonymous closures from a third party cannot be removed; do not register closures for hooks that others may need to unhook |
| Class-based callback inside another plugin | find the instance via the plugin's public accessor or `$wp_filter` inspection as a last resort, and document it |

`has_action( $hook, $callback )` returns the priority when found (an integer, possibly `0`) or `false`; compare with `false === `, not truthiness.

## Recursion and re-entrancy

`save_post`, `updated_option`, `wp_insert_post_data` and meta hooks fire from the functions the callback often calls. Updating the same object inside the callback loops.

```php
function acme_on_save( $post_id, $post ) {
	if ( wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) ) {
		return;
	}
	remove_action( 'save_post_acme_event', 'acme_on_save', 10 );
	wp_update_post( array( 'ID' => $post_id, 'menu_order' => 5 ) );
	add_action( 'save_post_acme_event', 'acme_on_save', 10, 2 );
}
add_action( 'save_post_acme_event', 'acme_on_save', 10, 2 );
```

Prefer a post-type-specific hook (`save_post_{$post_type}`), check autosave/revision/capability/nonce for admin forms, and write with `$wpdb->update` or direct meta APIs only when the side effects of `wp_update_post` are not wanted.

## Custom hooks and backwards compatibility

- Prefix hook names (`acme_`); document parameters in a docblock (`@param`, `@since`).
- A public hook is API. When renaming, keep the old hook firing through `do_action_deprecated()`/`apply_filters_deprecated( $old, $args, $version, $replacement )`, which also notifies developers in debug mode.
- Adding a parameter to an existing hook is backward compatible; changing the type or position is not.
- Do not make behavior depend on hooks that third parties may remove; do not fire public hooks before `init` unless documented.

## Request-context detection

- `is_admin()` is true for `admin-ajax.php` and `admin-post.php` requests, including unauthenticated ones. It is not an authorization check and is false for REST.
- Use `wp_doing_ajax()`, `wp_doing_cron()`, `defined( 'WP_CLI' ) && WP_CLI`, and for REST `wp_is_serving_rest_request()` (since 6.5, valid only after `parse_request`; for earlier code use hooks like `rest_api_init`). `REST_REQUEST` is unreliable at plugin load time.
- Gate admin-only code by hook (`admin_init`, `admin_menu`), not by a global `is_admin()` branch that also excludes REST callers who need the same service.

## Translation timing (6.7+)

Translating before `init` triggers a `_doing_it_wrong` notice for `_load_textdomain_just_in_time` in WordPress 6.7 and later. Common causes: translated strings in constants/properties at file load, `get_plugin_data()` without `$translate = false`, and early class constructors that call `__()`. Fix by deferring to `init` or later, or using `get_plugin_data( $file, false, false )` when only the version is needed. `load_plugin_textdomain()` is no longer required for WordPress.org-hosted plugins that support 4.6+; call it on `init` (not `plugins_loaded`) if you keep it. Find the caller with a `doing_it_wrong_run` hook that prints a backtrace for that function name, or with Query Monitor.

## Debugging checklist

1. Is the callback registered? `has_action( 'hook', 'callback' )` in a test or `wp eval` on a disposable site.
2. Did the hook fire? `did_action( 'hook' )`; is it currently firing? `doing_action()`.
3. Fired but empty? Check priority, a later callback overwriting the value, and the `accepted_args` count.
4. Which callbacks exist? Inspect `$GLOBALS['wp_filter']['hook']` (Query Monitor shows this).
5. Record the expected vs observed value at each priority before editing.

## Looks wrong but is fine

- A procedural plugin with a unique prefix and no classes or namespaces.
- Closures as callbacks on private, never-unhooked hooks.
- A callback with no `return` on an action hook.
- `add_action( 'init', ... )` directly in the main file (it is a valid timing).
- Direct `ABSPATH` guards missing in files that only declare classes/functions (a convention, not a vulnerability); guard files that execute code at load.

## Regression recipe for a hook fix

Assert the callback is attached at the intended priority, that the output changes only under the intended condition, that other callbacks on the same hook still run (register a second probe callback), that repeat registration does not double-fire, and that removal by the documented method works.

## Sources

Research date: 2026-10-08.

- Hooks: https://developer.wordpress.org/plugins/hooks/
- i18n changes in 6.7: https://make.wordpress.org/core/2024/10/21/i18n-improvements-6-7/
- `wp_is_serving_rest_request()`: https://developer.wordpress.org/reference/functions/wp_is_serving_rest_request/
