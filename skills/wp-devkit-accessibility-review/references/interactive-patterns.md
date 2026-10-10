# Interactive patterns and focus management

Contents: [Method](#method) - [Modal dialog](#modal-dialog) - [Disclosure and navigation](#disclosure-and-navigation) - [Tabs](#tabs) - [Accordion](#accordion) - [Combobox and autocomplete](#combobox-and-autocomplete) - [Popovers, tooltips and hover content](#popovers-tooltips-and-hover-content) - [Hiding content correctly](#hiding-content-correctly) - [Dynamic updates and routing](#dynamic-updates-and-routing) - [Pointer-only interactions](#pointer-only-interactions) - [Sources](#sources)

## Method

For each widget: name the APG pattern, write its keyboard contract, then test the rendered DOM in every state against that contract. A widget that deviates is not necessarily wrong; document the deliberate choice. ARIA roles promise behavior, so a role without its keys is worse than a plain element.

## Modal dialog

Contract (APG): focus moves into the dialog on open; Tab and Shift+Tab cycle inside; Escape closes; focus returns to the opener (or a sensible successor if it is gone); the container has `role="dialog"`, `aria-modal="true"` (only when the page behind really is inert) and a name via `aria-labelledby` or `aria-label`. Initial focus: the first focusable element, or a static heading with `tabindex="-1"` for long content, or the least destructive button for destructive confirmations.

Preferred implementations, in order:

1. Native `<dialog>` opened with `showModal()`: the browser makes the rest of the document inert, handles Escape, and restores focus. Verify the `close` event and that your own Escape handlers do not double-close.
2. `@wordpress/components` `Modal` in the block editor and admin React screens.
3. Custom: set `inert` on every sibling subtree of the dialog (or on the app root when the dialog is portaled). Avoid relying on a Tab keydown trap alone.

```html
<button type="button" id="open-filters" aria-haspopup="dialog">Filters</button>
<dialog id="filters" aria-labelledby="filters-title">
	<h2 id="filters-title">Filters</h2>
	<!-- controls -->
	<form method="dialog"><button>Apply</button> <button value="cancel">Cancel</button></form>
</dialog>
```

```js
const dialog = document.getElementById( 'filters' );
const opener = document.getElementById( 'open-filters' );
opener.addEventListener( 'click', () => dialog.showModal() );
dialog.addEventListener( 'close', () => {
	if ( opener.isConnected ) opener.focus(); // The browser usually does this; keep for removed/re-rendered openers.
} );
```

Edge cases to test: opener removed while open (cart drawer re-render), nested dialogs (the second opens above and returns to the first), dialog opened from a menu that closes, page scrolled, iOS VoiceOver swipe past the dialog, background scroll lock (`overflow:hidden` must not shift layout or hide focus), `prefers-reduced-motion`.

## Disclosure and navigation

Site navigation with submenus is a set of links plus disclosure buttons, not `role="menu"`.

- Button: `aria-expanded="false|true"`, `aria-controls` the list. Enter and Space toggle. Escape closes and returns focus to the button. Arrow keys, Home and End are optional additions, Tab must still work.
- Parent items that are also links need a separate toggle button; do not make one element both a link and a toggle.
- Hover alone is not a trigger. Hover content must be dismissible, hoverable and persistent.
- Closed submenus must be removed from the tab order (`hidden`, `display:none` or `inert`), not just moved off screen.
- Mobile hamburger buttons: visible text or an accessible name ("Menu"), `aria-expanded`, and the open panel reachable immediately after the button in DOM order or with focus moved in.
- Current page: `aria-current="page"` on the link (core's nav walker emits it).

`role="menu"`/`menuitem` is right for application menus (actions such as an editor toolbar menu), with arrow-key navigation, typeahead and roving focus. Report a `role="menu"` used for site navigation as WARNING only after showing link users are affected (for example links do not activate on Enter, or screen readers switch to application mode).

## Tabs

Contract: `role="tablist"` containing `role="tab"` elements with `aria-selected` and `aria-controls`; panels have `role="tabpanel"` and `aria-labelledby`. Roving tabindex: only the selected tab is in the Tab sequence; Left/Right (or Up/Down if vertical) move between tabs; Home/End jump; Tab moves into the panel. Choose automatic activation only if panel content renders instantly; otherwise use manual activation (Enter/Space). Tabs that merely filter page content without panels are better as a group of buttons with `aria-pressed` or links.

## Accordion

A heading containing a button per section: `<h3><button aria-expanded aria-controls>`. Enter/Space toggles. Collapsed panel content must not be focusable. Native `<details>`/`<summary>` is acceptable and has built-in state; do not add `aria-expanded` to `<summary>`. If grouping `<details>` with the `name` attribute (exclusive accordion) confirm browser support in the target matrix.

## Combobox and autocomplete

Follow the APG combobox: the input has `role="combobox"`, `aria-expanded`, `aria-controls` the popup, `aria-autocomplete`, and `aria-activedescendant` pointing at the highlighted option while real focus stays in the input. Down arrow opens, Escape closes (and clears if already closed), Enter selects. Announce result count (`wp.a11y.speak`) when suggestions load. Search suggestion lists that are only links under an input can use a simpler list with a live count instead of the full pattern.

## Popovers, tooltips and hover content

- A tooltip describes; it never carries the only copy of essential information. Show on focus as well as hover, dismiss with Escape without moving focus, keep visible while the pointer is over it, and tie it to the trigger with `aria-describedby`.
- The native `popover` attribute gives top-layer rendering and light dismiss, is non-modal and does not move focus into the popover unless a child has `autofocus`. For a button using `popovertarget`, browsers expose the expanded state implicitly (MDN; W3C ARIA-in-HTML test page flags an extra `aria-expanded` there as an error), so do not add it; for a popover opened from script (`showPopover()`) or a custom invoker, set `aria-expanded` yourself in the `toggle` event. As of 2026-10-08 MDN labels the API Baseline 2025, newly available; verify target browsers.
- Cookie banners and chat widgets are persistent overlays: they must not hide the focused element (use `scroll-padding`, avoid covering the focus ring) and must be reachable and dismissible by keyboard.

## Hiding content correctly

| Goal | Use | Do not |
| --- | --- | --- |
| Hidden for everyone | `hidden` or `display:none` | `opacity:0` alone |
| Disable a whole region (background of a modal, off-screen panel) | `inert` (widely available since April 2023) | `aria-hidden` alone: it leaves focusable descendants |
| Read by AT, not visible | `.screen-reader-text` | `display:none`, `visibility:hidden` |
| Visible, not for AT (decoration) | `aria-hidden="true"` on non-focusable decoration | on any element that contains or is focusable |
| Disable a single form control | `disabled` (or `aria-disabled="true"` plus blocked activation to keep it focusable for explanation) | `inert` on one input; `pointer-events:none` only |

Inert content is not findable by browser find-in-page and has no visual cue; style it. A modal `<dialog>` opened with `showModal()` escapes ancestor inertness.

## Dynamic updates and routing

- Live regions: render the empty container first, then change its text. `role="status"` (polite) for results and progress, `role="alert"` (assertive) for errors that block the user. One region per message type; do not nest.
- Do not move focus for passive updates. Move focus when the context changes: new page or step, dialog open, validation summary after submit.
- Client-side navigation (Interactivity API router, headless frontends): after the swap update `document.title`, move focus to the new `h1` or main container (`tabindex="-1"`), announce the change, and keep scroll position rules sane. Test browser Back.
- Infinite scroll and "load more": keep the trigger a button, preserve focus on the first new item, and announce how many were added. Provide pagination as an alternative.
- Loading skeletons: set `aria-busy="true"` on the updating region and announce completion, not each placeholder.

## Pointer-only interactions

Provide a single-pointer, non-drag alternative for sortable lists, sliders with drag handles, maps and range pickers (up/down buttons or a numeric input). Multi-touch and path gestures need button equivalents. Targets should be at least 24 by 24 CSS pixels or have the spacing exception; very small close icons in sticky banners are common failures. Single-character shortcuts must be remappable, disableable or active only on focus.

## Sources

Reviewed 2026-10-08.

- [APG modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [APG disclosure navigation example](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/)
- [APG tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/), [accordion](https://www.w3.org/WAI/ARIA/apg/patterns/accordion/), [combobox](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/)
- [MDN inert](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/inert)
- [MDN Popover API](https://developer.mozilla.org/en-US/docs/Web/API/Popover_API)
- [WCAG 2.2 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)
