# Admin accessibility, states and browser verification

Contents: scope; form and control requirements; feedback and status; keyboard and focus; tables and lists; motion and layout; verification method; what automated checks do not prove; sources.

Scope: custom wp-admin screens and editor-side tools you ship. Core admin chrome is out of your control; do not report core markup as a plugin defect. For a formal conformance audit hand off to `wp-devkit-wcag-review`; for a defects-first accessibility review of code, `wp-devkit-accessibility-review`.

## Form and control requirements

- Every field has a programmatic label: `<label for="id">` (use `label_for` in `add_settings_field` so the row header becomes a label), `aria-label` only when no visible text is appropriate. Placeholders are not labels.
- Descriptions and errors tie to the field with `aria-describedby`; mark invalid fields with `aria-invalid="true"` and give a text error (not color alone). Required state via `required`/`aria-required` plus visible text.
- Group related radios/checkboxes in `<fieldset><legend>`. Use native `<button>`, `<a>`, `<input>`, `<select>`; a clickable `<div>` needs role, tabindex, key handlers and is rarely justified. Icon-only buttons need an accessible name.
- Settings tables keep core's `form-table` with `<th scope="row">` for the label cell.
- Prefer WordPress components (`@wordpress/components`) for custom controls: they carry baseline labelling, focus and keyboard behavior. A component does not remove the need to supply `label` props.

## Feedback and status

- Save results, async errors and progress must be perceivable without sight: render notices in the DOM with `role="status"` (polite) or `role="alert"` (assertive); core's `.notice` markup injected on page load is read in context; for dynamic updates call `wp.a11y.speak( message, 'polite' | 'assertive' )` (script handle `wp-a11y`).
- On a failed submit move focus to the first error or an error summary, or keep focus on the submit control with the error announced; never leave focus on a removed element.
- Show pending state: disable or `aria-disabled` the submit control, change its label ("Saving..."), prevent double submission, and announce completion. Success is shown only after the server confirms persistence (response body or re-read), not when the request starts.
- Loading and empty states have text; spinners get an accessible label (`<span class="spinner is-active" aria-hidden="true">` plus a text status).
- Timed notices that auto-dismiss need a persistent way to re-read the message (WCAG 2.2.1 Timing Adjustable intent).

## Keyboard and focus

- All functions operable by keyboard in a logical order; visible focus indicator on every control (do not `outline: none` without a replacement of equal visibility); focus not hidden behind sticky bars (WCAG 2.2 criterion 2.4.11 Focus Not Obscured, AA).
- Modals/dialogs: move focus in, trap it, restore it to the trigger on close, close on Escape; use `Modal` from components or `<dialog>`.
- Drag-and-drop reordering needs a non-dragging alternative (WCAG 2.2 criterion 2.5.7, AA): up/down buttons or a numeric order field.
- Pointer targets at least 24 by 24 CSS pixels or adequately spaced (2.5.8 Target Size Minimum, AA).
- Do not request the same information twice in one flow (3.3.7 Redundant Entry, A) and do not require cognitive tests to authenticate screens that you add (3.3.8, AA).

## Tables and lists

Real `<table>` with `<th scope>` headers and a caption or heading; `WP_List_Table` supplies this. Sortable column headers expose sort state (core marks `aria-sort` through its sorted classes in `WP_List_Table`; custom grids must add `aria-sort`). Row actions that only appear on hover must also appear on focus (core's `.row-actions` does; custom CSS must keep this). Bulk-select checkboxes carry per-row labels.

## Motion and layout

Honor `prefers-reduced-motion`; WordPress 7.0 view transitions already do. Layout must reflow at 320 CSS px width and 200 percent zoom without two-dimensional scrolling for content (WCAG 1.4.10), except data tables. Do not rely on color alone for status (1.4.1); text contrast at least 4.5:1, UI components 3:1 against the admin color scheme options including the 7.0 Modern scheme.

## Verification method

1. Capability matrix (role switching), run against the real handlers: administrator allowed; the lowest role that sees the menu; a role without the capability sending the request directly (POST to `admin-post.php`, `admin-ajax.php`, REST). Assert stored state afterwards.
2. Playwright against `wp-env` or a disposable site, using `@wordpress/e2e-test-utils-playwright` (`Admin`, `RequestUtils`, `PageUtils`) to log in, visit the page (`admin.visitAdminPage( 'admin.php', 'page=acme-review' )`), fill the form, submit, assert the notice, reload and assert persisted values. Include: invalid input keeps previous values; double click submits once; keyboard-only submission; failed network response shows an error.
3. Axe via `@axe-core/playwright` on each state (initial, error, success, modal open, empty, loading). Fail on serious/critical violations in your markup; triage core-owned violations separately.
4. Manual: Tab through the whole screen; zoom to 200 percent and 320 px; one screen reader pass for the primary task (NVDA with Firefox/Chrome or VoiceOver with Safari) to confirm label, error and status announcements.
5. Regression across screens: load Dashboard, Plugins and a core editor, compare against baseline screenshots to catch leaked CSS/JS.
6. Record runner, versions, browser, role, fixture, result and exit code. Do not regenerate screenshot baselines to make a diff pass; review the diff.

## What automated checks do not prove

Axe-style rules find a subset of WCAG failures; a clean run does not show correct reading order, meaningful labels, keyboard traps in custom widgets, focus management after async updates, or screen reader output. A passing capability matrix covers the tested roles, not custom capability plugins or multisite super-admin differences. A passing Playwright run covers one browser and viewport.

## Sources (checked 2026-10-08)

- WCAG 2.2: https://www.w3.org/TR/WCAG22/ (criteria 1.4.1, 1.4.10, 2.4.11, 2.5.7, 2.5.8, 3.3.7, 3.3.8; levels for 2.4.11, 2.5.7, 2.5.8, 3.3.7, 3.3.8 and 1.4.10 checked against the Recommendation on 2026-10-08)
- Settings API: https://developer.wordpress.org/plugins/settings/settings-api/
- WordPress 7.0 field guide (view transitions, Modern color scheme): https://make.wordpress.org/core/2026/05/14/wordpress-7-0-field-guide/
- npm registry checked 2026-10-08 for package names: `@wordpress/e2e-test-utils-playwright` (3.0.0), `@axe-core/playwright` (4.13.0), `@wordpress/env` (11.17.0), `@wordpress/scripts` (36.1.0).

Confirmed 2026-10-08: WCAG 2.2 levels (2.4.11 AA, 2.5.7 AA, 2.5.8 AA with a 24 by 24 CSS px minimum, 3.3.7 A, 3.3.8 AA, 4.1.3 AA, 1.4.10 AA at 320 CSS px); `speak( message, ariaLive )` with `ariaLive` defaulting to `'polite'` (https://github.com/WordPress/gutenberg/blob/trunk/packages/a11y/README.md); `WP_List_Table` sets `aria-sort` on the sorted column (trunk `class-wp-list-table.php`); `Admin.visitAdminPage( adminPath, query )` and the exported `Admin`, `Editor`, `PageUtils`, `RequestUtils` classes (Gutenberg trunk `packages/e2e-test-utils-playwright`). Check `wp.a11y.speak` on older WordPress versions and the `RequestUtils` method names against the installed package README.
