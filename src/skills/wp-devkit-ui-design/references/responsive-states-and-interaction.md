# Responsive layout, states and interaction

Contents: layout, states, forms, motion and preferences, WCAG 2.2 interaction criteria, examples, sources.

## Layout

- Design from content outward; breakpoints follow where content breaks, not device names. Test 320, 360, 768, 1024, 1280 px, 200% and 400% zoom (reflow at 320 CSS px without two-dimensional scrolling is WCAG 1.4.10).
- Prefer wrapping and intrinsic sizing: `flex-wrap`, `grid-template-columns: repeat(auto-fit, minmax(min(100%, 16rem), 1fr))`, `min-width: 0` on flex/grid children, `max-width: 100%`, `overflow-wrap: anywhere` for long tokens (emails, URLs). Fixed pixel widths are defects only when they cause clipping or overlap at a tested width.
- Container queries (`@container`) for components placed in unknown column widths (patterns, widgets).
- Images: set `width`/`height` or `aspect-ratio` to prevent layout shift; `object-fit` for cropped media.
- Use logical properties (`margin-inline`, `padding-block`, `inset-inline-start`, `text-align: start`) so RTL works without a second stylesheet.

## State completeness

For each component list and render: default, hover, `:focus-visible`, active, disabled, loading, empty, error, success, long content, missing media, no-permission. Required behavior:

- Loading: reserve space, announce with `aria-busy` or a polite live region; avoid layout jump.
- Empty: say why and offer the next action.
- Error: keep entered input, put the message next to the field, link it with `aria-describedby`, move focus to the first error or an error summary on submit, never rely on color alone.
- Success: confirm in text; use `role="status"` for non-blocking confirmations.
- Disabled controls: prefer `aria-disabled` plus explanation when the reason matters, because native `disabled` removes focusability.

## Forms

Visible `<label>` per control, not placeholder-only; `autocomplete` tokens for personal data (WCAG 1.3.5); inline format hints before input; do not make users re-enter data already provided in the same process (3.3.7); authentication without cognitive tests such as transcribing characters, allowing paste and password managers (3.3.8).

## Motion and preferences

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }
@media (forced-colors: active) { .btn { border: 1px solid ButtonText; } }
```

Keep essential state changes visible without motion. Respect `prefers-color-scheme` only if the theme ships a dark palette tested for contrast.

## WCAG 2.2 criteria that most affect UI work

- 2.5.8 Target Size (Minimum, AA): pointer targets at least 24 by 24 CSS px unless an exception (spacing, inline, equivalent control, user-agent control, essential) applies.
- 2.4.11 Focus Not Obscured (Minimum, AA): a focused item must not be entirely hidden by sticky headers, cookie banners or chat widgets.
- 2.5.7 Dragging Movements (AA): provide a single-pointer alternative to drag-only controls.
- 3.2.6 Consistent Help (A), 3.3.7 Redundant Entry (A), 3.3.8 Accessible Authentication (Minimum, AA).
- 4.1.1 Parsing was removed in 2.2 (W3C: obsolete and removed). The WordPress accessibility coding standards state core code is expected to conform to WCAG 2.2 AA; do not assume that bar for third-party plugins.

This skill checks UI behavior; criterion-by-criterion conformance belongs to `wp-devkit-wcag-review` and `wp-devkit-accessibility-review`.

## Example: wrapping form row

```css
.contact-row { display: flex; flex-wrap: wrap; gap: 1rem; max-width: 100%; }
.contact-row > * { min-width: 0; flex: 1 1 14rem; }
```

Verify with a 40-character translated label, a long email address and 200% zoom.

## Sources

Research date: 2026-10-08.

- https://www.w3.org/TR/WCAG22/ (1.4.10 Reflow 320 CSS px, 1.3.5 Identify Input Purpose, 2.4.11, 2.5.7, 2.5.8, 3.3.7, 3.3.8 as listed in the wcag-review criteria index)
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- https://developer.wordpress.org/coding-standards/wordpress-coding-standards/accessibility/
