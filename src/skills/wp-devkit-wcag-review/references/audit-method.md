# WCAG evidence collection method

Contents: [Phase 1 scope](#phase-1-scope) - [Phase 2 explore](#phase-2-explore) - [Phase 3 sample](#phase-3-sample) - [Phase 4 evaluate](#phase-4-evaluate) - [Phase 5 report and retest](#phase-5-report-and-retest) - [Tools and what they cover](#tools-and-what-they-cover) - [Time and effort planning](#time-and-effort-planning) - [Sources](#sources)

The method follows W3C WCAG-EM (five steps) adapted to WordPress. Use representative journeys, not a page count. Treat automated output as leads.

## Phase 1 scope

Record, before any testing:

- Standard: WCAG version (2.1 or 2.2) and level (A, AA). Default AA.
- Boundary: domains, subsites (multisite), authenticated areas, apps, documents, third-party embeds in or out.
- Accessibility-supported baseline: browsers, versions, screen readers, devices. Content must work in this baseline; features that need something outside it fail the "accessibility-supported" requirement.
- Build identity: commit or release id, environment, plugin/theme versions, date. Retest must use a comparable build.
- Constraints: staging versus production, test accounts, payment sandbox, content freeze.

## Phase 2 explore

Inventory: page templates (home, archive, single, search, 404, cart, checkout, account), reusable components (header, mega menu, filters, forms, cards, modals, carousels, cookie banner, chat), media types, languages, user roles, and technologies relied upon (HTML, CSS, JavaScript, WAI-ARIA, PDF, SVG). In WordPress inspect: active theme and whether it is a block theme, builder usage, registered blocks in use, major plugins that print front-end markup, and caching or minification layers that alter markup.

## Phase 3 sample

- Structured sample: one page per template and per distinct component state; include empty, loading, success, error and long-content states. Include one page in each language or locale and each responsive layout that changes structure.
- Complete processes: every step of checkout (cart, shipping, payment, confirmation), registration, login and password reset, contact or lead form, search to result to item, account order lookup.
- Random sample: add pages not already chosen, about 10% of the structured sample size per WCAG-EM, and record how they were picked. If the random pages reveal new findings or content types, the structured sample was not representative: extend it.
- Small sites with few views can test everything.

## Phase 4 evaluate

For each sampled page or state:

1. Record environment (URL or fixture, auth state, browser and version, viewport, zoom, OS, input method, assistive technology and tool versions).
2. Run automated checks and keep raw results and rule tags. Triage into: confirmed, false positive, needs manual check. Keep `incomplete` items open.
3. Keyboard-only walkthrough: order, focus visibility, shortcuts, traps, Escape, overlays, equivalents for pointer actions.
4. Reflow at 320 CSS px width and 256 px height (for horizontal text), 200% text resize, text-spacing override, orientation, forced colors, reduced motion.
5. Contrast: measure text and UI component states, not the default only.
6. Screen-reader pass for names, roles, states, error and status announcements, page changes.
7. Content review: alt text meaning, link purpose, headings and labels, language, instructions, captions and descriptions for media, timing.
8. Record each criterion result with evidence reference. If a required environment is missing, mark Needs evidence.

Compare structured and random results; extend the sample if they disagree.

## Phase 5 report and retest

Use `deliverable-templates.md`. Group findings by root cause with all affected URLs, assign severity by user impact, and give each Fail steps to reproduce. After remediation retest the same sample states on the same kind of build, update the status table, and keep the earlier report for history. Schedule a recheck after theme, plugin or WordPress core updates and when new templates, authentication flows, media or checkout steps ship.

## Tools and what they cover

| Tool class | Covers | Does not cover |
| --- | --- | --- |
| axe-core (CLI, browser extension, `@axe-core/playwright`) | Names, ARIA validity, some contrast, ids, landmarks per rendered state | Keyboard logic, announcement quality, meaning of text |
| Lighthouse accessibility | A subset of axe rules, scored | Score is not a conformance result |
| WAVE, ARC, Accessibility Insights FastPass | Visual overlays and guided manual checks | Final judgment |
| Contrast analyzers (browser DevTools, TPGi CCA) | Foreground/background measurements | Gradients and images require sampling worst case |
| Screen readers (NVDA, JAWS, VoiceOver, TalkBack) | Real announcements, reading order | Other AT and versions |
| Responsive/zoom tests | Reflow, spacing, obscured focus | Content meaning |
| Validator for HTML | Parsing issues for 2.1 4.1.1 context | Not required for 2.2 |

Keep tool versions in the record. Never use a score as the result. Axe tags let you run version-specific rule sets (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`); tags are not combined automatically.

## Time and effort planning

Use scope-proportional estimates rather than a fixed number: the structured sample size, number of complete-process steps and states, and the AT matrix drive the effort. State the planned sample and matrix in the proposal so the reader can see what the resulting statement covers.

## Sources

Reviewed 2026-10-08.

- [WCAG-EM](https://www.w3.org/TR/WCAG-EM/) (current version at that URL): five steps, structured, random and complete-process samples, 10% random addition, report contents; scores discouraged
- [WCAG 2.2 understanding of conformance](https://www.w3.org/WAI/WCAG22/Understanding/conformance)
- [axe-core API](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md)
- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)
