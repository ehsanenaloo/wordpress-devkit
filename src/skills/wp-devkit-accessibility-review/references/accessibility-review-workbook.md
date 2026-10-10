# Accessibility review workbook

Contents: [Decision rules](#decision-rules) - [Looks wrong but is fine](#looks-wrong-but-is-fine) - [Looks fine but is wrong](#looks-fine-but-is-wrong) - [Severity](#severity) - [Finding template](#finding-template) - [Symptom to cause](#symptom-to-cause) - [Acceptance checks](#acceptance-checks) - [Sources](#sources)

Apply [the engineering contract](engineering-contract.md) first. This workbook is the decision layer; the topic files hold the detail:
[WordPress surfaces](wordpress-a11y-surfaces.md), [interactive patterns](interactive-patterns.md), [forms and errors](forms-and-errors.md), [testing and evidence](testing-and-evidence.md).

## Decision rules

| Question | Rule |
| --- | --- |
| Native or custom? | A native element wins unless a requirement cannot be met natively. Every custom widget needs a named APG pattern and its full key map; ARIA attributes alone add no behavior. |
| Which name? | The accessible name must contain the visible label text (voice users say what they see). `aria-label` on a `div` or `span` without a role is not allowed: generic elements cannot be named. Placeholder is not a label. |
| Menu or disclosure? | Site navigation is a list of links. Use a disclosure button (`aria-expanded`, `aria-controls`) for submenus. `role="menu"` promises application-menu keys (arrows, typeahead) and breaks link navigation when only Tab works. |
| Modal or not? | A modal needs: focus moved in, background inert, Escape, focus return. If background stays usable, it is not modal: no `aria-modal`, no focus trap. |
| Hide how? | `display:none`, `hidden` and `inert` remove from tab order and accessibility tree. `aria-hidden="true"` alone removes from the tree only and leaves focusable descendants (an ARIA violation). Visually-hidden-but-readable text uses the `screen-reader-text` pattern. |
| Announce what? | Announce results the user did not trigger focus for (saved, N results, error count). Do not announce what focus already conveys, and do not re-announce on every keystroke. |
| Move focus when? | Only when the context changes (dialog opens, step changes, error summary after failed submit). A toast or "saved" notice is a status message and must not steal focus. |
| Automation covers what? | Rules for names, roles, ARIA validity, color contrast of static text and duplicate IDs. It cannot judge focus order, key handling, announcement quality, reading order or whether an alt text is meaningful. |

## Looks wrong but is fine

- `tabindex="-1"` on a button or option: roving tabindex inside tabs, toolbars, listboxes and grids. Confirm arrow keys move focus before reporting.
- `tabindex="-1"` on a heading, `main` or dialog title: deliberate programmatic focus target after navigation or open.
- `role="presentation"` / `alt=""` on a decorative image next to text that already conveys the meaning.
- `aria-hidden="true"` on an icon inside a button that has visible text or an `aria-label`.
- `onclick` on a `<button>` or `<a href>`: native elements already handle Enter and Space (link: Enter only).
- A skip link hidden at rest: correct if it becomes visible on `:focus` and its target exists.
- A `role="dialog"` without `aria-modal` that does not trap Tab: correct for a non-modal dialog or popover.
- `outline: none` followed by a visible `:focus-visible` replacement with sufficient contrast.
- Duplicate links to the same destination with different visible text in one card (image link plus title link) where the image link has `aria-hidden` and `tabindex="-1"` and the title link carries the name.

## Looks fine but is wrong

- A visible label that is not programmatically associated (`<label>` without `for`/nesting, or a `<span>` beside the input).
- `aria-describedby` or `aria-labelledby` that points to an id missing in the current state (for example an error element removed after correction while the reference stays), so the description is silently empty.
- A focus trap implemented on `keydown` Tab only, which lets screen-reader virtual cursor and touch swipe escape into the page behind (use `inert` on the siblings or native modal `<dialog>`).
- `role="alert"` injected together with its container: many screen readers miss announcements from a region that did not exist before the text was inserted. Render the empty region first, then insert text.
- Custom select built from divs with no `listbox`/`combobox` semantics but "works with the mouse".
- Focus returned to `document.body` after the trigger was removed from the DOM.
- Contrast measured on the default state only; hover, focus, disabled-looking-but-active and error states fail.

## Severity

Per the contract, by demonstrated impact on a real journey:
CRITICAL: a keyboard or screen-reader user cannot complete a core task (cannot submit checkout, cannot close a modal, focus lost behind a modal, trap with no exit).
WARNING: task is completable with workaround or extra effort (missing error association, wrong role, poor order, low contrast on secondary text).
INFO: improvement with no demonstrated failure (heading level skips with clear structure, redundant ARIA).
Candidates that need AT or runtime proof are labeled candidate with the missing evidence named. A failed automated rule is a lead until reproduced.

## Finding template

```text
[WARNING] file:line (component, state)
Actor: keyboard-only user | screen-reader user | low-vision (zoom) | voice control | motor
Trigger: exact steps and state
Observed / Expected: what happens vs. the pattern's contract
Impact: what the user cannot do or must work around
Confidence: confirmed (reproduced) | probable (code path) | candidate (needs AT)
Fix: change in the owning component (native element, attribute, handler, CSS)
Regression: rendered-DOM or Playwright assertion plus manual script row
Pointer: WCAG criterion number (status is decided by wp-devkit-wcag-review)
```

## Symptom to cause

| Symptom | Evidence to gather | Usual cause and fix |
| --- | --- | --- |
| Element reachable by mouse, not by Tab | Computed role, tabindex, whether it is `<div onclick>` | Replace with `<button type="button">` or `<a href>`; do not bolt on `tabindex="0"` plus key handlers unless a widget pattern requires it. |
| Dialog closes, focus jumps to top of page | Which element held focus before open; was it re-rendered | Store `document.activeElement` on open; restore if still connected, else focus a logical successor. |
| Screen reader says "button" only | Accessible name in DevTools accessibility pane | Icon-only control without text: add visible text, `aria-label`, or `VisuallyHidden` text. |
| Error text present but never spoken | Is the container created before insertion; is it tied to the input | Pre-render `role="status"`/`role="alert"` region or use `wp.a11y.speak()`; add `aria-describedby` and `aria-invalid="true"`. |
| Sticky header covers focused link | Tab through page at 100% and 200% zoom | `scroll-padding-top` equal to the header height; avoid fixed layers that cover focus. |
| Menu opens on hover only | Tab to the item | Add a disclosure button and open on click/Enter/Space; keep hover as enhancement; make hover content dismissible and persistent. |
| Reduced-motion user still gets animation | Emulate `prefers-reduced-motion: reduce` | Gate large or parallax motion in `@media (prefers-reduced-motion: reduce)`. |

## Acceptance checks

- Complete the journey with keyboard only, including error and cancel paths; visible focus on every stop; no trap; Escape and focus return verified.
- Accessible names, roles and states read from the accessibility tree match the visible UI in each state.
- At 320 CSS px width and 200% text zoom nothing is clipped or obscured; text spacing overrides do not break controls.
- At least one screen-reader and browser pair walked through the journey; record names and versions.
- An automated scan (axe through Playwright) reports no new violations for each state, and it is not treated as proof.

A pass proves the recorded journey, states and tools only. It does not prove other assistive technology, other viewports, content authored later, or conformance. Hand off to `wp-devkit-wcag-review` for a status table.

## Sources

Reviewed 2026-10-08. Behavior in this workbook was checked against these primary sources; browsers and screen readers differ, so retest in the target matrix.

- [WordPress accessibility coding standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/accessibility/) (WCAG 2.2 AA is the stated core expectation)
- [APG modal dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), [APG disclosure navigation](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/), [APG patterns index](https://www.w3.org/WAI/ARIA/apg/patterns/)
- [ARIA 1.2 roles that cannot be named](https://www.w3.org/TR/wai-aria-1.2/#namefromprohibited)
- [MDN inert](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/inert)
