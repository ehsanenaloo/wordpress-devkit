# Settings API, custom save handlers and persistence

Contents: choosing the save path; Settings API lifecycle; validation and error feedback; custom admin-post and AJAX handlers; REST-backed settings; per-user and network data; secrets and sensitive values; failure symptoms; sources.

Contract reminder: a nonce proves request intent for a session, not authorization. Every write needs a capability check for the operation; nonce and capability together, in that role.

## Choosing the save path

| Need | Path |
|---|---|
| Plain site options | Settings API (`register_setting` + `options.php`) |
| Settings edited in a React/JS screen | `register_setting( ..., array( 'show_in_rest' => true ) )` and `wp.apiFetch( '/wp/v2/settings' )`, or your own REST route |
| One-off action (import, rebuild, test connection) | `admin_post_{action}` form handler or a REST route; never a GET link that mutates |
| Inline interactions without page reload | REST route preferred; `wp_ajax_{action}` for legacy code |
| Network settings (multisite) | Custom form to `edit.php?action=` via `network_admin_edit_{action}` or `admin_post_`, with `manage_network_options` |

Do not invent a save path when the Settings API or an existing REST controller already owns the data.

## Settings API lifecycle (verified)

```php
add_action( 'admin_init', static function () {
	register_setting( 'acme_options', 'acme_settings', array(
		'type'              => 'array',
		'sanitize_callback' => 'acme_sanitize_settings',
		'default'           => array( 'mode' => 'basic', 'limit' => 20 ),
		'show_in_rest'      => false,
	) );
	add_settings_section( 'acme_main', __( 'General', 'acme' ), '__return_false', 'acme-settings' );
	add_settings_field( 'acme_limit', __( 'Item limit', 'acme' ), 'acme_render_limit', 'acme-settings', 'acme_main', array( 'label_for' => 'acme-limit' ) );
} );

function acme_sanitize_settings( $input ) {
	$prev   = get_option( 'acme_settings', array() );
	$input  = is_array( $input ) ? $input : array();
	$out    = is_array( $prev ) ? $prev : array();                 // preserve previous valid data.
	$mode   = isset( $input['mode'] ) ? sanitize_key( $input['mode'] ) : ( $out['mode'] ?? 'basic' );
	if ( in_array( $mode, array( 'basic', 'advanced' ), true ) ) {   // domain validation, not only sanitizing.
		$out['mode'] = $mode;
	} else {
		add_settings_error( 'acme_settings', 'acme_mode', __( 'Mode must be basic or advanced.', 'acme' ) );
	}
	$limit = isset( $input['limit'] ) ? (int) $input['limit'] : ( $out['limit'] ?? 20 );
	if ( $limit >= 1 && $limit <= 100 ) {
		$out['limit'] = $limit;
	} else {
		add_settings_error( 'acme_settings', 'acme_limit', __( 'Limit must be between 1 and 100.', 'acme' ) );
	}
	return $out;
}
```

The page callback prints `<form method="post" action="options.php">`, then `settings_fields( 'acme_options' )` (emits the option-group hidden fields and the `_wpnonce` for `{group}-options`), `do_settings_sections( 'acme-settings' )`, `submit_button()`.

Facts checked in core and the handbook:
- `options.php` checks the nonce for the group and the capability `manage_options` by default; change it per group with the `option_page_capability_{$option_group}` filter (needed when non-admins, such as editors, manage the page, otherwise they get "not allowed" on save even though the menu is visible).
- Only options registered under the posted `option_page` group are saved (the allowed-options list); an option missing from `register_setting` silently does not save. This is the commonest "save says success but value unchanged" cause, along with a mismatched group name in `settings_fields()`.
- `sanitize_callback` is a `sanitize_option_{$option}` filter. It also runs on first `add_option`, so user notes report it can run twice on first save; keep it idempotent and make `add_settings_error` calls de-duplicated by code.
- `register_setting` `type`, `description`, `default`, `show_in_rest` matter for REST exposure; `label` added in 6.6. `show_in_rest` with `array` type needs an items schema (core calls `_doing_it_wrong` otherwise).
- Reading: `get_option( 'acme_settings', $default )` returns the registered `default` only when the option row is absent; partial arrays need `wp_parse_args()`.
- Register on `admin_init` (or `rest_api_init` too when REST-exposed; registering only in `admin_init` hides REST settings).

## Validation and feedback

- Sanitizing (`sanitize_text_field`) is not validating domain values. Reject out-of-range or unknown values and keep the previous valid value (shown above); do not erase other fields when one fails.
- Errors: `add_settings_error( $setting, $code, $message, $type )`. Pages under Settings (`add_options_page`, parent `options-general.php`) display them automatically because `admin-header.php` includes `options-head.php`, which calls `settings_errors()`. Pages under other menus (top-level, Tools) must call `settings_errors()` themselves; calling it again on a Settings subpage duplicates notices.
- The Settings API redirects back with `settings-updated=true`: show success only for that, never on a plain GET.
- After a failed validation the form re-renders from stored values, so rejected input is lost. If preserving the user's invalid input matters, keep a transient keyed by user and re-populate the fields, with the invalid fields flagged.
- Escape on output by context: `esc_attr()` for value attributes, `esc_html()` for text, `esc_textarea()`, `esc_url()`, `selected()`/`checked()`/`disabled()` helpers for state.

## Custom handlers (admin-post and AJAX)

```php
add_action( 'admin_post_acme_rebuild', 'acme_handle_rebuild' ); // no admin_post_nopriv_ unless the action is meant for anonymous users.

function acme_handle_rebuild() {
	if ( ! current_user_can( 'manage_options' ) ) {
		wp_die( esc_html__( 'You are not allowed to do this.', 'acme' ), '', array( 'response' => 403 ) );
	}
	check_admin_referer( 'acme_rebuild' );                       // verifies _wpnonce; dies on failure.
	$scope = isset( $_POST['scope'] ) ? sanitize_key( wp_unslash( $_POST['scope'] ) ) : 'all';
	if ( ! in_array( $scope, array( 'all', 'recent' ), true ) ) {
		wp_safe_redirect( add_query_arg( 'acme_error', 'scope', wp_get_referer() ?: admin_url( 'admin.php?page=acme' ) ) );
		exit;
	}
	// ... perform the action idempotently ...
	wp_safe_redirect( add_query_arg( 'acme_done', 1, admin_url( 'admin.php?page=acme' ) ) );  // Post/Redirect/Get.
	exit;
}
```

Form side: `<input type="hidden" name="action" value="acme_rebuild">` plus `wp_nonce_field( 'acme_rebuild' )`, posting to `admin_url( 'admin-post.php' )`.

Rules:
- `check_admin_referer()` verifies intent only (verified); it returns 1/2 for valid nonce within 12/24 hours, dies otherwise, and never checks capability. Pass an explicit action, since the default `-1` is flagged.
- `admin_post_nopriv_*` is for logged-out users and widens exposure to anonymous requests; register only when intended and validate as untrusted input.
- AJAX: `check_ajax_referer( 'acme_action', 'nonce' )` (dies with `-1`/403 on failure) then `current_user_can()`, then `wp_send_json_success()/_error()` (both exit). Register `wp_ajax_nopriv_*` only for public features.
- Destructive or state-changing links need a nonce (`wp_nonce_url()`); GET must not mutate without one.
- `wp_unslash()` before sanitizing `$_POST`/`$_GET` values; validate arrays element by element; avoid `extract()`; use `wp_safe_redirect()` for internal redirects, then `exit`.
- Bulk and long operations: do not run heavy work inside the form post. Queue it (Action Scheduler or cron), show "queued" and a status screen, and make the action safe to repeat. Disable the submit button on submit and handle a double submit server-side (idempotency, lock).

## REST-backed settings screens

With `show_in_rest`, `GET/POST /wp/v2/settings` is limited to users with `manage_options` and only to registered settings. React screens load values with `apiFetch`, keep a dirty copy, post only changed keys, and render server validation errors from the JSON body (`code`, `message`, `data.params`). Successful save: re-fetch or use the response body (it contains the stored, sanitized values) so the UI reflects what was persisted rather than what was typed.

## Per-user, network and sensitive data

- Per-user preferences (columns, per-page, dismissed notices): `update_user_meta()`/`get_user_option()` (the latter is blog-prefixed on multisite); never shared options. Dismissal AJAX still needs nonce and `is_user_logged_in()`.
- Network options: `get_site_option`/`update_site_option` and the network-admin hooks listed above.
- Secrets (API keys): do not echo stored secrets back into the HTML; show a masked placeholder and update only when a new value is submitted (empty means unchanged, with an explicit "remove" control). Prefer defining secrets in `wp-config.php`/environment and show "defined in configuration" in the UI. Keep them non-autoloaded and out of logs and exports.
- Export/import of settings: validate every key and type on import through the same sanitizer; never `unserialize()` uploaded data (use JSON).

## Failure symptoms

| Symptom | Evidence | Fix |
|---|---|---|
| "Success" but value unchanged | Option not registered under the posted group, wrong `settings_fields()` name, or sanitizer returned the old value | Align group/name; assert via `get_option` after save |
| Non-admin cannot save | `manage_options` default for `options.php` | `option_page_capability_{group}` filter or a custom handler with the right cap |
| Valid fields wiped when one is invalid | Sanitizer returns only the new input | Start from previous value, update only valid keys |
| Notices appear twice | `settings_errors()` called on a Settings subpage | Remove manual call |
| "Are you sure?" page | Nonce missing/expired, wrong action name | Same action in `wp_nonce_field` and `check_admin_referer`; page cached with stale nonce |
| Direct POST by low role succeeds | Capability checked only in the menu | Check capability in the handler |

## Sources (checked 2026-10-08)

- Settings API: https://developer.wordpress.org/plugins/settings/settings-api/
- `register_setting`: https://developer.wordpress.org/reference/functions/register_setting/
- `check_admin_referer`: https://developer.wordpress.org/reference/functions/check_admin_referer/
- `admin_post_{action}`: https://developer.wordpress.org/reference/hooks/admin_post_action/
- Core source read (trunk): `wp-admin/options.php` (`option_page_capability_{$option_page}`), `wp-admin/admin-header.php` (options-head include), `wp-admin/options-head.php`, `wp-admin/includes/template.php` (`settings_errors`).

Facts to verify in source: `option_page_capability_{$option_page}` default `manage_options` in `wp-admin/options.php`; `check_admin_referer()` returns 1/2 for a nonce generated 0-12 / 12-24 hours ago and flags the default `-1` action with `_doing_it_wrong` (`pluggable.php`); `do_action( "network_admin_edit_{$action}" )` in `wp-admin/network/edit.php`. Check `wp_safe_redirect` with `wp_get_referer()` and the `check_ajax_referer` die output on every supported version. Sources: https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-admin/options.php, https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/pluggable.php, https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-admin/network/edit.php
