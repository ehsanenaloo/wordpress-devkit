# Admin screens, assets, list tables and editor-side UI

Contents: menu registration and access; screen scoping; assets; script data and translations; React/components screens; WP_List_Table; screen options; notices; admin styling and the 7.0 color scheme; multisite; failure symptoms; sources.

## Menu registration and access (verified)

- `add_menu_page()`/`add_submenu_page()`/`add_options_page()` return the page's hook suffix; keep it. The capability argument controls menu display; core also refuses direct URL access for users lacking it (`user_can_access_admin_page()`), but this does not protect `admin-post.php`, `admin-ajax.php` or REST writes. The render callback should still check the capability for the operation, and every write handler must.
- `load-{$hook_suffix}` runs before output on that screen only: process redirects, `add_screen_option`, help tabs and enqueue decisions there, not inside the render callback (headers already sent).
- Menu slugs and hook suffixes derive from user-visible titles for submenus under Settings (`settings_page_{slug}`); use the returned value, never a hard-coded string.

## Screen scoping

Prefer the hook suffix passed to `admin_enqueue_scripts`:

```php
$hook = add_menu_page( 'Review', 'Review', 'manage_options', 'acme-review', 'acme_render_review' );
add_action( 'admin_enqueue_scripts', static function ( $current ) use ( $hook ) {
	if ( $current !== $hook ) {
		return;
	}
	$asset = include plugin_dir_path( __FILE__ ) . 'build/review.asset.php'; // dependencies + version from @wordpress/scripts.
	wp_enqueue_script( 'acme-review', plugins_url( 'build/review.js', __FILE__ ), $asset['dependencies'], $asset['version'], array( 'in_footer' => true, 'strategy' => 'defer' ) );
	wp_enqueue_style( 'acme-review', plugins_url( 'build/review.css', __FILE__ ), array( 'wp-components' ), $asset['version'] );
} );
```

- `get_current_screen()` (`->id`, `->base`, `->post_type`) is set from the `current_screen` action onward, which precedes `admin_enqueue_scripts` on normal admin screens but not in every context (for example early hooks and AJAX); the hook-suffix comparison is the dependable form. For post edit screens compare `$hook` with `'post.php'`/`'post-new.php'` and `$screen->post_type`.
- A global admin CSS rule (`.button`, `h1`, `#wpbody`) leaks across every screen. Namespace selectors under a root class or id owned by the plugin.
- Verify scoping by loading an unrelated screen (Dashboard, Plugins, a core editor) and checking that your handle is absent (`wp_script_is`, network panel) and its layout unchanged.

## Script arguments (verified on `wp_enqueue_script`)

Since 6.3 the fifth argument accepts an array: `strategy` (`defer`|`async`), `in_footer`; `fetchpriority` since 6.9; `module_dependencies` since 7.0 (requires `in_footer` true or `defer`). A bare boolean still means `in_footer`. WordPress may weaken but never strengthen the requested strategy based on the dependency tree. An unregistered dependency raises a notice and the script may not print as intended; take dependencies from the generated `*.asset.php`.

## Passing data and translations

- Data: `wp_add_inline_script( 'acme-review', 'window.acmeReview = ' . wp_json_encode( $data ) . ';', 'before' )` (JSON-encode; no string concatenation of user data) or a REST fetch. Pass only what the screen needs; never secrets or other users' data.
- REST nonce/root: depend on `wp-api-fetch` and let `apiFetch` handle root URL and nonce.
- JS strings: `wp_set_script_translations( 'acme-review', 'acme', plugin_dir_path( __FILE__ ) . 'languages' )`; extract with `wp i18n make-pot` and `make-json`. Text domain equals slug.
- Script modules (6.5+) are for `import`-style modules with `wp_register_script_module()`/`wp_enqueue_script_module()`; classic admin screens still use scripts unless you opt in.

## React / component screens

- Use the WordPress packages (`@wordpress/components`, `@wordpress/element`, `@wordpress/data`, `@wordpress/api-fetch`, `@wordpress/i18n`) built with `@wordpress/scripts`, externalized via the dependency extraction plugin so React and packages are not bundled twice. Pin versions in `package.json`; check peer expectations before upgrading, since component APIs evolve (for example default sizes and `__next*` props are being retired across releases).
- Do not introduce a second UI framework or global CSS reset for one small screen.
- `@wordpress/dataviews` (DataViews/DataForm) is the core direction for list-like admin screens; WordPress 7.0 added layouts (Activity, Details) and a Field API for third-party field types. The `@wordpress/dataviews` changelog lists a breaking change in 11.0.0 (2025-11-26): `groupByField` became `groupBy.field`; check the package changelog before upgrading (https://github.com/WordPress/gutenberg/blob/trunk/packages/dataviews/CHANGELOG.md).
- In WordPress 7.0 the post editor is iframed when every block inserted in the post uses block API version 3+ (the 7.0 check looks at inserted blocks, not all registered blocks; a v2 block in the content falls back to the non-iframe editor, and the iframe is not enforced in 7.0; the handbook says the post editor always iframes from 7.1 / Gutenberg 23.6). Editor-side code that reaches into `document` for editor DOM breaks. Use editor APIs (`useBlockProps`, `@wordpress/editor` slots such as `PluginSidebar`, `PluginDocumentSettingPanel`, `registerPlugin`).
- Loading, empty and error states are part of the screen: show a spinner with an accessible label, an explanatory empty state and a retry on error.

## WP_List_Table (verified caveats)

The class is marked private and subject to change; test against each beta/RC. Subclass requirements: `get_columns()`, `prepare_items()` (call `set_pagination_args()`, populate `$this->items`, define `$this->_column_headers = array( $columns, $hidden, $sortable, $primary )` if not provided by `parent`), `column_default()`, optionally `get_sortable_columns()`, `get_bulk_actions()`, `column_cb()`. Declare properties explicitly; dynamic properties are deprecated since 6.4.

Hardening points:
- Allow-list `orderby`/`order` against `get_sortable_columns()` before building queries; use `$wpdb->prepare` with `%d` for `LIMIT/OFFSET`; read the search term with `wp_unslash` + `sanitize_text_field`.
- Bulk actions: core outputs the `bulk-{plural}` nonce field; verify with `check_admin_referer( 'bulk-' . $this->_args['plural'] )`, then capability per item (`current_user_can( 'delete_post', $id )`), not a single role check. Handle the action in `load-{$hook}` and redirect (PRG) with a result count.
- Row actions that mutate: nonce-protected links (`wp_nonce_url`), capability per row.
- Large tables: do not `SELECT *` for everything; paginate in SQL; avoid per-row queries in `column_*`.
- Item per page: `add_screen_option( 'per_page', ... )` on `load-{hook}` and the `set_screen_option_{$option}` filter (5.4.2+; the older `set-screen-option` still applies to option names ending `_page`) returning the validated integer (clamp 1-200) to save; returning false skips saving.

## Notices

Use `wp_admin_notice( $message, array( 'type' => 'error', 'dismissible' => true, 'id' => '...' ) )` (6.4+; `paragraph_wrap` default true; `additional_classes`, `attributes`) or the classic `<div class="notice notice-error is-dismissible"><p>...</p></div>`. Core moves notices placed on `admin_notices` below the first `h1`/`.wp-header-end`; add `<hr class="wp-header-end">` to custom screens. Keep notices scoped to the relevant screen, actionable and dismissible (directory guideline) and escape the message by context.

## Styling

Use admin CSS custom properties such as `--wp-admin-theme-color` (present in trunk `wp-admin/css/colors/_admin.scss`; check the installed version) rather than fixed colors so user color schemes work. WordPress 7.0 adds a "Modern" admin color scheme and view transitions between admin screens (disabled under reduced motion): re-check custom headers, hard-coded colors and animations. Respect `prefers-reduced-motion` in your own transitions.

## Multisite

Network admin screens use `network_admin_menu` and `manage_network_options`/`manage_network` capabilities; per-site screens inside Network Admin do not exist. Capability names differ: use `is_super_admin()` only when the product truly means super admin. Settings that apply network-wide use site options.

## Failure symptoms

| Symptom | Evidence | Fix |
|---|---|---|
| Other admin pages restyled | Global selector or unscoped enqueue | Scope by hook suffix and namespaced CSS |
| Script runs but components missing | Dependencies not taken from `.asset.php` / not externalized | Use generated asset file |
| Sorting/ordering injection or errors | Raw `orderby` | Allow-list |
| Page reachable by direct URL for low role | Hidden registration without capability, or custom route | Capability on registration and handler |
| Bulk action does nothing | Missing `process_bulk_action` call or wrong nonce action | Match `bulk-{plural}` and redirect |
| "Headers already sent" on redirect | Redirect inside the render callback | Move to `load-{hook}` |

## Sources (checked 2026-10-08)

- `add_menu_page`: https://developer.wordpress.org/reference/functions/add_menu_page/
- `wp_enqueue_script`: https://developer.wordpress.org/reference/functions/wp_enqueue_script/
- `WP_List_Table`: https://developer.wordpress.org/reference/classes/wp_list_table/
- `wp_admin_notice`: https://developer.wordpress.org/reference/functions/wp_admin_notice/
- WordPress 7.0 field guide: https://make.wordpress.org/core/2026/05/14/wordpress-7-0-field-guide/
- Core source read (trunk): `wp-admin/includes/plugin.php` (`user_can_access_admin_page`).

Confirmed in trunk source (2026-10-08): `set_screen_options()` in `wp-admin/includes/misc.php` (filter `set-screen-option` applies only to options ending `_page` or `layout_columns`; `set_screen_option_{$option}` since 5.4.2; returning false skips saving), `wp_enqueue_script` args (`strategy`/`in_footer` 6.3, `fetchpriority` 6.9, `module_dependencies` 7.0), DataViews `groupBy` rename, iframe rule. Check the notice relocation script behavior, the `--wp-admin-theme-color` introduction version and the `@wordpress/components` API for the target version. Sources: https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-admin/includes/misc.php, https://make.wordpress.org/core/2026/02/24/iframed-editor-changes-in-wordpress-7-0/, https://developer.wordpress.org/block-editor/reference-guides/block-api/block-api-versions/block-migration-for-iframe-editor-compatibility/
