# Administrative screens and save behavior workbook

Contents: establish the behavior; decision checkpoints; symptom triage; worked decisions; looks wrong but is fine; severity guidance; verification; sources.

Apply [the engineering contract](engineering-contract.md) before classifying a concern. Deep topics: `settings-and-save-flows.md`, `screens-assets-and-lists.md`, `admin-accessibility-and-verification.md`.

## Establish the behavior

Record screen ID/hook suffix, actor role and capability, option/meta owner, save path (Settings API, `admin-post`, AJAX, REST), the rendered form, the actual save request (method, action, fields, nonce), asset handles, and the observed vs expected result. Reproduce with the role that fails, not only an administrator.

## Decision checkpoints

| Decision | What changes the answer |
|---|---|
| Permission | Menu capability controls display and direct URL access to the page only; each write handler (admin-post, AJAX, REST) needs its own capability check for the operation and object. |
| Setting contract | Option group, registered name, type, default and sanitizer must match the posted fields; invalid input must keep the previous valid value. |
| Intent | Settings API forms carry the group nonce via `settings_fields()`. Custom handlers need `check_admin_referer`/`check_ajax_referer` plus a capability check. Nonce is not permission. |
| Assets | Scope to the hook suffix; take dependencies from `.asset.php`; namespace CSS. |
| Feedback | Show persisted success, actionable errors, loading and empty states; preserve input and focus on failure. |
| Data class | Per-user preferences are user meta; shared settings are options; secrets are not echoed back. |
| Long work | Queue and report status; do not hold a form post open. |

## Symptom triage

| Symptom | Evidence to gather | Action after confirmation |
|---|---|---|
| Save reports success but value is unchanged | Posted field names vs registered option, group in `settings_fields()`, sanitizer return value | Register the option in the posted group; fix the sanitizer; assert with `get_option`. |
| Editor/Shop manager sees page but save fails | `options.php` default `manage_options` | `option_page_capability_{group}` filter or a custom handler with the proper capability. |
| One invalid field erases the rest | Sanitizer starts from `$input` only | Start from stored value; reject only the invalid key. |
| Other admin screens look broken | Network tab for your handles; selector scope | Scope enqueue by hook suffix; namespace selectors. |
| Request succeeds for a role without menu access | Direct POST under that role | Capability check in the handler. |
| "Are you sure you want to do this" | Nonce action name mismatch or expired/cached nonce | Align action names; avoid cached nonce HTML. |
| Notices appear twice / not at all | Parent menu of the page; manual `settings_errors()` | Settings subpages: do not call; other parents: call once. |
| Screen blank with React | Console, missing dependency handles | Use generated asset file; check handle registration. |

## Worked decisions

Independently written illustrations, not executed tests.

### 1. Stylesheet loaded on every admin screen

Problem: `admin_enqueue_scripts` enqueues `acme-console` unconditionally; its `.button` rules restyle core screens. Fix: capture the hook suffix returned by `add_menu_page()` and enqueue only when `$hook` equals it; namespace selectors under `.acme-console`. Verify: load the target and two unrelated screens, assert handle presence/absence and screenshot parity for the unrelated ones.

### 2. Menu hidden, handler open

```php
add_action( 'admin_post_acme_purge', function () {
	check_admin_referer( 'acme_purge' );
	acme_purge_cache();
	wp_safe_redirect( admin_url( 'admin.php?page=acme' ) );
	exit;
} );
```
The page is only in the menu for administrators, and the nonce is per user and action, so the exposure depends on whether a lower-privileged user can obtain a nonce for `acme_purge` (for example if it is printed on a screen or an AJAX response they can load, or the action name is shared with a widely printed nonce). Establish that path before assigning severity; the missing capability check is the defect either way because the nonce only proves intent. Fix: add `current_user_can( 'manage_options' )` before the nonce check and keep `exit`. Severity follows what purge does: usually WARNING (availability/performance abuse); CRITICAL if the action destroys user data. Regression: POST as subscriber with a valid nonce returns 403 and no state change.

### 3. Sanitizer wipes sibling settings

`return array( 'limit' => absint( $input['limit'] ) );` drops `mode` on every save. Fix: merge into the stored array and validate keys independently, using `add_settings_error` for rejects. Regression: submit only `limit`; `mode` persists; submit `limit=0`; stored limit unchanged and an error shown.

### 4. Settings API form with no handwritten nonce (benign)

A form using `settings_fields( 'acme_options' )` posting to `options.php` is protected by core's group nonce and capability check. Missing a custom `wp_nonce_field` is not a finding. Verify the group name matches, the capability filter (if non-admin), and sanitizer behavior.

### 5. Dynamic notices with no status role (accessibility)

A React "Saved" toast appended to the body is not announced. Fix: `wp.a11y.speak( __( 'Settings saved.', 'acme' ), 'polite' )` or a `role="status"` live region present before the update. Regression: with a screen reader (or the accessibility tree in Playwright) the message is exposed after save; error variant uses assertive and moves focus.

## Looks wrong but is fine

- A top-level menu with a lower capability than the underlying settings (the handler enforces the stricter capability).
- Settings API pages without custom nonces; `options.php` as the form action.
- Using `$hook === $page_hook` comparisons instead of `get_current_screen()`.
- `wp_ajax_nopriv_` absent on authenticated-only actions.
- Inline `<style>` limited to one screen's output.
- Unescaped constants/integers in output where the value is a cast integer or a literal.

## Severity guidance

CRITICAL: a reachable state-changing handler available to an unintended role with destructive or privilege-affecting impact; stored XSS in admin screens reachable by lower roles. WARNING: missing capability on lower-impact handlers, global CSS/JS leakage, settings that can be silently reset, inaccessible save feedback on the primary task, non-queued long work. INFO: copy, layout, optional refactors. Report as candidate or insufficient evidence when the save path, version or role set cannot be established.

## Verify the outcome

- Role matrix on the real handlers; stored state asserted after denied requests.
- Invalid and incomplete input keeps prior state with an error message tied to the field.
- Keyboard-only run, double submit, failed request, empty and loading states; 320 px and 200 percent zoom.
- Unrelated screens unchanged (handles absent, screenshots stable).
- Axe on each state; one manual screen reader pass for the primary task.

A pass proves the tested roles, browser, viewport and WordPress version; it does not prove other roles, multisite super-admin behavior, browsers, or assistive technology combinations.

## Delivery evidence

Explain the practical result, changed owner and remaining limits; list executed vs unexecuted checks with command and exit status.

## Sources (checked 2026-10-08)

- Settings API: https://developer.wordpress.org/plugins/settings/settings-api/
- `register_setting`: https://developer.wordpress.org/reference/functions/register_setting/
- `add_menu_page`: https://developer.wordpress.org/reference/functions/add_menu_page/
- `check_admin_referer`: https://developer.wordpress.org/reference/functions/check_admin_referer/
- `admin_post_{action}`: https://developer.wordpress.org/reference/hooks/admin_post_action/
- `admin_enqueue_scripts`: https://developer.wordpress.org/reference/hooks/admin_enqueue_scripts/
