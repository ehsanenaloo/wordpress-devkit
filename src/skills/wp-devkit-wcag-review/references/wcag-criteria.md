# WCAG 2.1 and 2.2 A/AA test index

Contents: [How to use](#how-to-use) - [Criteria table](#criteria-table) - [Evidence and scope](#evidence-and-scope) - [WordPress hot spots](#wordpress-hot-spots) - [Sources](#sources). Reviewed 2026-10-08 against the W3C Recommendations.

## How to use

Use the selected normative version, including its exceptions and conformance requirements. This practical index is not a replacement for the standard. Select a representative complete-process sample, record browser/assistive-technology versions, and mark each criterion pass, fail, not applicable with reason, or not tested.

WCAG 2.1 has 50 A/AA criteria, including 4.1.1. WCAG 2.2 removes 4.1.1 and adds six A/AA criteria, yielding 55. Focus Visible (2.4.7) remains AA in both. AAA 2.4.12 requires no part of the focused component be hidden by author-created content, subject to its notes; it is outside this A/AA table.

## Criteria table

| Criterion | Level | Versions | Practical procedure |
|---|---|---|---|
| [1.1.1 Non-text Content](https://www.w3.org/TR/WCAG22/#non-text-content) | A | 2.1, 2.2 | Inspect purpose of each image/control; compare accessible alternative with its function; mark decorative images appropriately. |
| [1.2.1 Audio-only and Video-only (Prerecorded)](https://www.w3.org/TR/WCAG22/#audio-only-and-video-only-prerecorded) | A | 2.1, 2.2 | Check prerecorded audio-only/video-only alternatives and the media-alternative exception. |
| [1.2.2 Captions (Prerecorded)](https://www.w3.org/TR/WCAG22/#captions-prerecorded) | A | 2.1, 2.2 | Play synchronized prerecorded media; verify accurate timed speech and meaningful sound captions. |
| [1.2.3 Audio Description or Media Alternative (Prerecorded)](https://www.w3.org/TR/WCAG22/#audio-description-or-media-alternative-prerecorded) | A | 2.1, 2.2 | Check a complete media alternative or audio description for meaningful visual information. |
| [1.2.4 Captions (Live)](https://www.w3.org/TR/WCAG22/#captions-live) | AA | 2.1, 2.2 | Observe live synchronized media and verify live captions. |
| [1.2.5 Audio Description (Prerecorded)](https://www.w3.org/TR/WCAG22/#audio-description-prerecorded) | AA | 2.1, 2.2 | Verify audio description for meaningful prerecorded video; a transcript alone does not satisfy this AA criterion. |
| [1.3.1 Info and Relationships](https://www.w3.org/TR/WCAG22/#info-and-relationships) | A | 2.1, 2.2 | Inspect headings, groups, labels and table headers in the accessibility tree against visual relationships. |
| [1.3.2 Meaningful Sequence](https://www.w3.org/TR/WCAG22/#meaningful-sequence) | A | 2.1, 2.2 | Read DOM/accessibility order with CSS disabled and screen reader; confirm meaning. |
| [1.3.3 Sensory Characteristics](https://www.w3.org/TR/WCAG22/#sensory-characteristics) | A | 2.1, 2.2 | Review instructions for dependence only on shape, color, size, location, orientation or sound. |
| [1.3.4 Orientation](https://www.w3.org/TR/WCAG22/#orientation) | AA | 2.1, 2.2 | Rotate portrait/landscape; verify equivalent use unless the orientation is essential. |
| [1.3.5 Identify Input Purpose](https://www.w3.org/TR/WCAG22/#identify-input-purpose) | AA | 2.1, 2.2 | Inspect personal-data inputs for programmatically identified purposes from the specified taxonomy. |
| [1.4.1 Use of Color](https://www.w3.org/TR/WCAG22/#use-of-color) | A | 2.1, 2.2 | Verify errors, charts, links and states convey information beyond color. |
| [1.4.2 Audio Control](https://www.w3.org/TR/WCAG22/#audio-control) | A | 2.1, 2.2 | For automatic audio lasting over three seconds test pause/stop or independent volume control. |
| [1.4.3 Contrast (Minimum)](https://www.w3.org/TR/WCAG22/#contrast-minimum) | AA | 2.1, 2.2 | Measure actual foreground/background text combinations: 4.5:1 normal, 3:1 large; document exceptions. |
| [1.4.4 Resize Text](https://www.w3.org/TR/WCAG22/#resize-text) | AA | 2.1, 2.2 | Resize text to 200% without assistive technology; check content and functionality, with specified exceptions. |
| [1.4.5 Images of Text](https://www.w3.org/TR/WCAG22/#images-of-text) | AA | 2.1, 2.2 | Inspect rasterized text; prefer real text unless customizable or essential. |
| [1.4.10 Reflow](https://www.w3.org/TR/WCAG22/#reflow) | AA | 2.1, 2.2 | Test 320 CSS-pixel width and 256 CSS-pixel height for the relevant writing direction; document essential two-dimensional exceptions. |
| [1.4.11 Non-text Contrast](https://www.w3.org/TR/WCAG22/#non-text-contrast) | AA | 2.1, 2.2 | Measure meaningful component/state and graphical boundaries at 3:1 with applicable exceptions. |
| [1.4.12 Text Spacing](https://www.w3.org/TR/WCAG22/#text-spacing) | AA | 2.1, 2.2 | Apply line height 1.5, paragraph spacing 2, letter spacing .12 and word spacing .16 times font size; check clipping and operation. |
| [1.4.13 Content on Hover or Focus](https://www.w3.org/TR/WCAG22/#content-on-hover-or-focus) | AA | 2.1, 2.2 | Trigger tooltip/popover by hover and focus; test dismissible, hoverable and persistent behavior and exceptions. |
| [2.1.1 Keyboard](https://www.w3.org/TR/WCAG22/#keyboard) | A | 2.1, 2.2 | Complete each function with keyboard alone; distinguish path-dependent exceptions. |
| [2.1.2 No Keyboard Trap](https://www.w3.org/TR/WCAG22/#no-keyboard-trap) | A | 2.1, 2.2 | Enter and leave every widget/dialog; check instructions for nonstandard exit. |
| [2.1.4 Character Key Shortcuts](https://www.w3.org/TR/WCAG22/#character-key-shortcuts) | A | 2.1, 2.2 | Test single-character shortcuts can be disabled/remapped or work only when their component has focus. |
| [2.2.1 Timing Adjustable](https://www.w3.org/TR/WCAG22/#timing-adjustable) | A | 2.1, 2.2 | Trigger session/form timeout; test adjustment, extension or switch-off and applicable exceptions. |
| [2.2.2 Pause, Stop, Hide](https://www.w3.org/TR/WCAG22/#pause-stop-hide) | A | 2.1, 2.2 | Observe moving/blinking/scrolling over five seconds and auto-updating content; test pause/stop/hide or update frequency controls. |
| [2.3.1 Three Flashes or Below Threshold](https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold) | A | 2.1, 2.2 | Inspect animations/video using a flash-analysis method; do not provoke unsafe flashing during manual review. |
| [2.4.1 Bypass Blocks](https://www.w3.org/TR/WCAG22/#bypass-blocks) | A | 2.1, 2.2 | Activate skip links/landmarks/heading navigation; verify bypass of repeated content. |
| [2.4.2 Page Titled](https://www.w3.org/TR/WCAG22/#page-titled) | A | 2.1, 2.2 | Inspect page titles, including route changes, for topic/purpose. |
| [2.4.3 Focus Order](https://www.w3.org/TR/WCAG22/#focus-order) | A | 2.1, 2.2 | Trace tab order through conditional content and errors; preserve meaning and operation. |
| [2.4.4 Link Purpose (In Context)](https://www.w3.org/TR/WCAG22/#link-purpose-in-context) | A | 2.1, 2.2 | Compare link text and programmatically determined context with actual destination/action. |
| [2.4.5 Multiple Ways](https://www.w3.org/TR/WCAG22/#multiple-ways) | AA | 2.1, 2.2 | Verify multiple routes to pages within a set, respecting process-step exceptions. |
| [2.4.6 Headings and Labels](https://www.w3.org/TR/WCAG22/#headings-and-labels) | AA | 2.1, 2.2 | Check headings and labels describe topic/purpose; this differs from programmatic association. |
| [2.4.7 Focus Visible](https://www.w3.org/TR/WCAG22/#focus-visible) | AA | 2.1, 2.2 | Check visible keyboard focus on every interactive element in both 2.1 and 2.2. |
| [2.4.11 Focus Not Obscured (Minimum)](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum) | AA | 2.2 | With author-created sticky headers/overlays, focused component must not be entirely hidden; test scrolling and exceptions. |
| [2.5.1 Pointer Gestures](https://www.w3.org/TR/WCAG22/#pointer-gestures) | A | 2.1, 2.2 | Perform multipoint/path gestures using a single pointer without a path-based gesture unless essential. |
| [2.5.2 Pointer Cancellation](https://www.w3.org/TR/WCAG22/#pointer-cancellation) | A | 2.1, 2.2 | Test down/up activation, abort and undo, including essential exceptions. |
| [2.5.3 Label in Name](https://www.w3.org/TR/WCAG22/#label-in-name) | A | 2.1, 2.2 | Compare visible label with accessible name; name must contain the visible text. |
| [2.5.4 Motion Actuation](https://www.w3.org/TR/WCAG22/#motion-actuation) | A | 2.1, 2.2 | Test a conventional UI alternative and disabling motion response unless an exception applies. |
| [2.5.7 Dragging Movements](https://www.w3.org/TR/WCAG22/#dragging-movements) | AA | 2.2 | Complete drag actions with a single pointer without dragging unless essential. |
| [2.5.8 Target Size (Minimum)](https://www.w3.org/TR/WCAG22/#target-size-minimum) | AA | 2.2 | Measure 24 by 24 CSS pixels or specified spacing/equivalent/inline/user-agent/essential exceptions. |
| [3.1.1 Language of Page](https://www.w3.org/TR/WCAG22/#language-of-page) | A | 2.1, 2.2 | Inspect the root language and screen-reader pronunciation. |
| [3.1.2 Language of Parts](https://www.w3.org/TR/WCAG22/#language-of-parts) | AA | 2.1, 2.2 | Inspect language changes on passages/phrases and specified exceptions. |
| [3.2.1 On Focus](https://www.w3.org/TR/WCAG22/#on-focus) | A | 2.1, 2.2 | Focus controls without activation; check unexpected context changes. |
| [3.2.2 On Input](https://www.w3.org/TR/WCAG22/#on-input) | A | 2.1, 2.2 | Change settings/select inputs; check context changes are announced beforehand or explicitly initiated. |
| [3.2.3 Consistent Navigation](https://www.w3.org/TR/WCAG22/#consistent-navigation) | AA | 2.1, 2.2 | Compare repeated navigation order across the sampled set of pages. |
| [3.2.4 Consistent Identification](https://www.w3.org/TR/WCAG22/#consistent-identification) | AA | 2.1, 2.2 | Compare identification of components with the same function across pages. |
| [3.2.6 Consistent Help](https://www.w3.org/TR/WCAG22/#consistent-help) | A | 2.2 | If specified help mechanisms repeat across pages, verify consistent relative order unless user changes it. |
| [3.3.1 Error Identification](https://www.w3.org/TR/WCAG22/#error-identification) | A | 2.1, 2.2 | Submit invalid data; verify item and error are identified in text. |
| [3.3.2 Labels or Instructions](https://www.w3.org/TR/WCAG22/#labels-or-instructions) | A | 2.1, 2.2 | Inspect visible labels/instructions for required input, format and purpose. |
| [3.3.3 Error Suggestion](https://www.w3.org/TR/WCAG22/#error-suggestion) | AA | 2.1, 2.2 | Cause known input errors; check correction suggestions unless security/purpose exceptions apply. |
| [3.3.4 Error Prevention (Legal, Financial, Data)](https://www.w3.org/TR/WCAG22/#error-prevention-legal-financial-data) | AA | 2.1, 2.2 | Test covered submissions/deletions are reversible, checked or reviewable/confirmable. |
| [3.3.7 Redundant Entry](https://www.w3.org/TR/WCAG22/#redundant-entry) | A | 2.2 | Repeat a multi-step process; earlier information must be auto-populated or selectable, with exceptions. |
| [3.3.8 Accessible Authentication (Minimum)](https://www.w3.org/TR/WCAG22/#accessible-authentication-minimum) | AA | 2.2 | Test password managers/paste and permitted alternatives; inspect cognitive tests and specified exceptions. |
| [4.1.2 Name, Role, Value](https://www.w3.org/TR/WCAG22/#name-role-value) | A | 2.1, 2.2 | Inspect custom control name/role/state/value and notification of changes with assistive technology. |
| [4.1.3 Status Messages](https://www.w3.org/TR/WCAG22/#status-messages) | AA | 2.1, 2.2 | Trigger progress/results/errors; confirm appropriate programmatic status without moving focus unnecessarily. |
| [4.1.1 Parsing](https://www.w3.org/TR/WCAG21/#parsing) | A | 2.1 only | W3C Understanding: consider always satisfied for HTML/XML content. Evaluate duplicate IDs or nesting problems that change name, role or relationship under 1.3.1/4.1.2; not a criterion in 2.2. |

## Evidence and scope

Record URL/component, state, criterion/version, actor, steps, observed result, artifact and remediation test. Automated tools find a subset; manually test keyboard, zoom/reflow, content meaning, authentication, complete processes and assistive-technology announcements. Do not convert absence of automated violations into conformance.

Include dynamic errors, empty/loading/success states, checkout/payment confirmation, modals, menus, sticky overlays, locale/RTL and responsive variants. Recheck after a fix on the same build. A passing sample is evidence for that sample, not all pages.

Normative sources (see also Sources below): [WCAG 2.1](https://www.w3.org/TR/WCAG21/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [2.4.12 notes](https://www.w3.org/TR/WCAG22/#focus-not-obscured-enhanced).

## WordPress hot spots

Where these criteria usually fail in WordPress sites, to prioritize sample selection. These are leads from experience of common patterns, not findings.

| Area | Criteria to test first | Look at |
| --- | --- | --- |
| Theme header, navigation, mega menus | 2.1.1, 2.4.1, 2.4.3, 2.4.7, 4.1.2, 1.4.13 | Hover-only submenus, `role="menu"` misuse, missing disclosure state, skip link target, sticky header over focus (2.4.11) |
| Block content authored by editors | 1.1.1, 1.3.1, 2.4.4, 2.4.6 | Alt text, heading levels chosen visually, "click here" links, tables without headers, color-only emphasis |
| Search, filters, pagination | 1.3.1, 3.2.2, 4.1.3 | Result counts announced, filters that auto-submit on change (context change), pagination labels and current page |
| Forms (contact, newsletter, login, registration) | 1.3.5, 3.3.1 to 3.3.4, 3.3.7, 3.3.8, 4.1.3 | Labels, errors, autocomplete, blocked paste, CAPTCHA, redundant entry |
| WooCommerce shop, cart, checkout, account | 1.3.1, 2.1.1, 2.4.3, 2.5.8, 3.3.x, 4.1.3 | Mini-cart drawer, quantity steppers, variation swatches (name and state), coupon toggle, address autocomplete, payment iframes, order confirmation |
| Sliders, carousels, video backgrounds, popups | 2.2.2, 2.3.1, 2.1.2, 1.4.2, 2.4.11 | Auto-advance without pause, autoplay audio, popup focus and dismissal, cookie banner over content |
| Embedded media | 1.2.x | Captions, audio description, transcript, player keyboard operation |
| Page-builder output | 1.3.1, 1.3.2, 2.4.6, 4.1.2 | Div soup, empty headings used for spacing, duplicate ids, reading order versus visual order |
| Multilingual and RTL | 3.1.1, 3.1.2, 1.3.2 | `lang` per locale, mixed-language passages, RTL focus and reading order |
| Documents (PDF downloads) | 1.1.1, 1.3.1, 2.4.2 | PDFs linked from the site are in scope when the claim covers them; tag structure, title, reading order |

## Sources

Reviewed 2026-10-08.

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [WCAG 2.1](https://www.w3.org/TR/WCAG21/)
- [What is new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) (nine additions, 4.1.1 removed, Recommendation 5 October 2023)
- [Target Size (Minimum) understanding](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html): 24 by 24 CSS px; exceptions spacing, equivalent, inline, user-agent control, essential
- [Focus Not Obscured (Minimum) understanding](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html): partial visibility suffices; sticky headers and cookie banners that fully cover focus fail; `scroll-padding` is a sufficient technique
