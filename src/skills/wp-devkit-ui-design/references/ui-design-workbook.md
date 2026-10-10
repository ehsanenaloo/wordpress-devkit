# WordPress UI design workbook

Apply [the engineering contract](engineering-contract.md) first. Contents: evidence, decision table, symptom table, looks-fine cases, severity, worked example, acceptance, reports, sources.

## Evidence to collect

User task and success definition, existing screenshots and content, who owns the surface (theme, block, builder, admin), editable components, design constraints (brand, tokens), supported locales, directions, browsers and devices, and what research or analytics already exist. Capture the current journey (URLs, screenshots at 360 and 1280 px) before judging it.

## Decision table

| Decision | Rule |
| --- | --- |
| Polish vs rebuild | A structural request needs real section/component changes (landmarks, headings, order); CSS alone cannot satisfy it. A polish request must not restructure. |
| Where to change | At the owner (theme.json token, block style, builder section, admin component). Never add a competing override. See [wordpress-ui-surfaces.md](wordpress-ui-surfaces.md). |
| Tokens | Change the token at its source; list consumers; check user Global Styles; keep aliases on rename. See [design-systems-and-tokens.md](design-systems-and-tokens.md). |
| States | Design all states before visuals; see [responsive-states-and-interaction.md](responsive-states-and-interaction.md). |
| Claims | Visual and interaction results come from rendered evidence; user preference, conversion and usability gains need sessions or a valid experiment ([research-and-usability.md](research-and-usability.md), [analytics-and-experiments.md](analytics-and-experiments.md)). |
| Locale | Check RTL and long text before sign-off ([localization-and-content-design.md](localization-and-content-design.md)). |

## Symptom table

| Symptom | Evidence | Likely owner |
| --- | --- | --- |
| Redesign looks the same | section/component diff vs request | structure not changed |
| Mobile overflow | computed width of the overflowing element, fixed widths, long tokens | layout owner |
| Editor differs from front | computed styles in both, loaded stylesheets | missing editor style or competing source |
| Cannot reach/see focus | tab through; sticky overlay; `outline: none` | focus styles (2.4.11) |
| Small tap targets | measured box size | target size (2.5.8) |
| Claimed uplift with no data | absence of sessions/events | report as unmeasured |

## Looks wrong but is fine

- Black body copy on a white form body (a deliberate high-contrast choice; verify the ratio rather than "fixing" it).
- Fixed widths on elements that never clip at tested widths and zoom.
- Repeated literal values not yet tokenized when no design-system change is requested.
- A screenshot that improved visually with no conversion claim made.
- Inline targets (links inside sentences) smaller than 24 px, which 2.5.8 exempts.
- Hidden labels implemented with a visually-hidden class (valid) versus placeholder-only labels (not valid).

Insufficient evidence outcome: when only code, only a screenshot, or only one viewport is available, say which observations are missing (browser run, keyboard, zoom, RTL) and report "not established" instead of a verdict.

## Severity

CRITICAL: the primary action is unreachable or invisible on a supported viewport, a keyboard trap, or content loss on form error. WARNING: clipping/overlap at supported widths, failed contrast or target size on core flows, editor/front divergence, missing error/empty states. INFO: polish, token hygiene, optional motion refinements.

## Worked example: clipped long labels in a fixed row

Problem: `.contact-row { display:flex; width:900px; }` clips at 360 px. Fix at the owner: `display:flex; flex-wrap:wrap; gap:1rem; max-width:100%;` and `min-width:0` on children. Prove: Playwright screenshots at 360, 768, 1280 px with a 40-character label and a long email; `document.documentElement.scrollWidth <= innerWidth`; Tab order unchanged; zoom 200%.

## Acceptance

Run the rows of [acceptance-checklist.md](acceptance-checklist.md) that apply; add visual regression and axe per [visual-regression-and-devices.md](visual-regression-and-devices.md). A passing run does not prove real-user outcomes or conformance beyond the tested browsers, assistive technologies and locales.

## Reports

Review finding: `file:line` or URL+viewport | actor | trigger | path | impact | confidence | fix | regression. Change report: owner, files, flows implemented, viewports/browsers/locales tested, screenshots, empty/loading/error/success states, commands with exit codes, unexecuted checks.

## Sources

Research date: 2026-10-08.

- https://developer.wordpress.org/coding-standards/wordpress-coding-standards/accessibility/
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- https://developer.wordpress.org/themes/global-settings-and-styles/introduction-to-theme-json/
