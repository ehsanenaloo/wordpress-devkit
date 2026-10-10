# Forms, validation, authentication and status messages

Contents: [Labels and instructions](#labels-and-instructions) - [Validation and error handling](#validation-and-error-handling) - [Server-rendered WordPress example](#server-rendered-wordpress-example) - [Autocomplete and input purpose](#autocomplete-and-input-purpose) - [Authentication](#authentication) - [Multi-step and checkout forms](#multi-step-and-checkout-forms) - [Status messages](#status-messages) - [Checks](#checks) - [Sources](#sources)

## Labels and instructions

- Every control has a persistent visible label tied by `for`/`id` or by nesting. Placeholder text vanishes on input and often fails contrast; use it only for a format hint.
- Group radios, checkboxes and multi-part answers (date of birth, address lines that read as one question) with `<fieldset><legend>`. Keep legends short; a long question goes in the legend with the hint in `aria-describedby`.
- The accessible name must contain the visible text. A visible "Search" button named "Go" by `aria-label` breaks voice control.
- Mark required fields in text, not color alone, and use `required` or `aria-required="true"` consistently. Say what "*" means before the form.
- Format hints, character limits and password rules belong before the field and in `aria-describedby`.
- Do not use `title` as the only label or hint; it is inconsistent across devices.
- Use the right `type` (`email`, `tel`, `number` with care, `search`) and `inputmode`; avoid `type="number"` for identifiers such as postcodes or card numbers.

## Validation and error handling

1. Identify the field and the problem in text ("Email address: enter an address like name@example.com"), not by color or icon alone.
2. Set `aria-invalid="true"` on the invalid control only after validation, and connect the message with `aria-describedby`.
3. Preserve what the user typed. Never clear the form on a server error.
4. On failed submit move focus to an error summary (an element with `tabindex="-1"` and a heading) or to the first invalid field. The summary links to each field by `href="#field-id"` and the link moves focus into the input. Do both rather than relying on a toast.
5. Suggest a correction when it is known (format, allowed range), unless that exposes security information.
6. For inline validation on blur, announce through the field's described-by text; do not fire a live announcement per keystroke.
7. Native browser bubbles (`reportValidity`) are acceptable for simple forms but vary by browser and cannot show a summary; if you rely on them, test each target browser with a screen reader, or add `novalidate` and own the pattern end to end.
8. Legal, financial or data-deleting submissions need a way to review, correct or reverse (confirm step, undo, or edit-after-submit).

## Server-rendered WordPress example

Pattern for a plugin form handled by `admin-post.php` that redisplays errors. It shows the structure; sanitization, nonce and capability checks are placeholders to adapt, and the nonce is not an authorization check.

```php
<?php
/**
 * Render a text field with an optional error message.
 *
 * @param string $id      Field id and name.
 * @param string $label   Visible label.
 * @param string $value   Current value.
 * @param string $error   Error text or ''.
 * @param string $hint    Hint text or ''.
 */
function myplugin_render_field( $id, $label, $value, $error = '', $hint = '' ) {
	$described = array();
	if ( '' !== $hint ) {
		$described[] = $id . '-hint';
	}
	if ( '' !== $error ) {
		$described[] = $id . '-error';
	}
	?>
	<p>
		<label for="<?php echo esc_attr( $id ); ?>"><?php echo esc_html( $label ); ?></label>
		<input
			type="text"
			id="<?php echo esc_attr( $id ); ?>"
			name="<?php echo esc_attr( $id ); ?>"
			value="<?php echo esc_attr( $value ); ?>"
			<?php echo $described ? 'aria-describedby="' . esc_attr( implode( ' ', $described ) ) . '"' : ''; ?>
			<?php echo '' !== $error ? 'aria-invalid="true"' : ''; ?>
		/>
		<?php if ( '' !== $hint ) : ?>
			<span id="<?php echo esc_attr( $id ); ?>-hint"><?php echo esc_html( $hint ); ?></span>
		<?php endif; ?>
		<?php if ( '' !== $error ) : ?>
			<span id="<?php echo esc_attr( $id ); ?>-error" class="error-text">
				<span class="screen-reader-text"><?php esc_html_e( 'Error:', 'myplugin' ); ?></span>
				<?php echo esc_html( $error ); ?>
			</span>
		<?php endif; ?>
	</p>
	<?php
}
```

The error text must not depend on color alone (add the text prefix or an icon with text) and must meet 4.5:1 contrast. For a summary, render `<div role="group" tabindex="-1" aria-labelledby="error-summary-title">` before the form and focus it in a small script after a failed post.

## Autocomplete and input purpose

Personal-data fields should use the HTML `autocomplete` tokens (`name`, `given-name`, `family-name`, `email`, `tel`, `street-address`, `postal-code`, `country`, `cc-number`, `one-time-code`, `current-password`, `new-password`). They help password managers, autofill and users with cognitive or motor disabilities. Do not disable autofill on login or checkout forms. WooCommerce core address fields define `autocomplete` tokens in `WC_Countries::get_default_address_fields()` (for example `given-name`, `postal-code`, `country`); custom checkout fields added through filters often do not, and the Checkout block was not verified.

## Authentication

WCAG 2.2 AA 3.3.8 forbids requiring a cognitive function test (remembering a password, transcribing characters, solving a puzzle) unless an alternative, a mechanism that helps, object recognition or personal content is offered. Practical rules:

- Never block paste or autofill on username, password or one-time-code fields.
- Use proper `autocomplete` tokens and `type="password"`; a show-password toggle is helpful and must be a named button with state.
- Magic links, passkeys and SSO are valid alternatives. A CAPTCHA that asks users to transcribe distorted text fails; an image-recognition challenge is allowed at AA but offer an alternative where possible.
- Multi-step MFA: each step needs a path without a cognitive test (pasteable codes, push or link alternative).
- Session timeouts: warn before expiry, allow extension, and preserve entered data.

## Multi-step and checkout forms

- Information entered earlier in the same process (billing address reused as shipping) is pre-filled or selectable (3.3.7 Redundant Entry, WCAG 2.2 A), except for security or essential re-entry.
- Step changes: update the page heading and title, move focus to the step heading, and announce the step ("Step 2 of 3: Shipping").
- Totals updated by ajax (shipping method change) are status messages: announce "Order total updated: $42.00" without moving focus.
- Coupon and gift-card fields need their own labels, and a failure message tied to the field.
- Place the order button last in DOM order; do not disable it silently, explain what is missing.

## Status messages

A status message reports success, result counts, progress or an error without a change of context. Present it with a live region so assistive technology announces it without focus movement (WCAG 4.1.3).

- `role="status"` (polite): "Item added to cart", "12 results", "Saved".
- `role="alert"` (assertive): "Payment failed", session about to expire.
- Insert text into a region that already exists in the DOM; avoid injecting the region and text together.
- `wp.a11y.speak( message, 'polite' )` is the WordPress helper (it keeps its own live regions); do not combine it with a second `aria-live` region announcing the same text.
- Too many announcements are a defect: batch rapid updates, announce the final state.

## Checks

1. Tab through the form: order matches visual order; each stop announces name, role, state, required and hint.
2. Submit empty and with bad values: summary or first-field focus, per-field messages, preserved input.
3. Correct the field: error clears, `aria-invalid` removed, description reference not dangling.
4. Use a password manager and paste into every credential field.
5. 320 CSS px width, 200% text size: labels and errors are not clipped; fields keep their labels.
6. Screen reader pass of the failure path, recording what was announced.

## Sources

Reviewed 2026-10-08.

- [WCAG 2.2 Accessible Authentication (Minimum) understanding](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html)
- [WCAG 2.2 Status Messages understanding](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html)
- [W3C WAI forms tutorial](https://www.w3.org/WAI/tutorials/forms/)
- [@wordpress/a11y](https://developer.wordpress.org/block-editor/reference-guides/packages/packages-a11y/)
- [HTML autocomplete attribute (WHATWG)](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#autofill)
