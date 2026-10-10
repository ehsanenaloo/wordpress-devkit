---
name: wp-devkit-ui-design
description: Design, implement or review WordPress user journeys, responsive layouts, UI states, design tokens, editor/front parity, RTL and visual-regression checks. Not for WCAG criterion audits (wcag-review), theme.json internals (theme skill) or wp-admin implementation (admin-ui).
---

# WordPress journeys and visual decisions

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, redesign, baseline refresh or untrusted runtime execution. Implementation applies only when the request authorizes changes.

## Inputs

User task and success definition, existing screenshots and content, surface owner (theme, block, builder, admin), editable components, design constraints, supported locales, directions, browsers and devices. Inspect project evidence first; ask only what changes the decision.

## Boundaries

- WCAG criterion-by-criterion conformance: `wp-devkit-wcag-review`; accessibility defects in code: `wp-devkit-accessibility-review`.
- Theme templates, `theme.json` mechanics: `wp-devkit-theme-development`; wp-admin screen implementation: `wp-devkit-admin-ui-development`; block internals: `wp-devkit-block-development`.
- Speed measurement and tuning: `wp-devkit-performance-review`.

## Code Review Workflow

1. Capture the current journey and content (URLs, viewports, screenshots). Define the user outcome; separate visual polish from structural reconstruction.
2. Locate the owner of each surface and token (`references/wordpress-ui-surfaces.md`, `references/design-systems-and-tokens.md`). Preserve working navigation, links and content.
3. Check states, forms, layout and interaction against `references/responsive-states-and-interaction.md`: loading, empty, error, success, long content, 320 px to wide, zoom, keyboard, focus visibility, target size, reduced motion.
4. Check locale and RTL with stress data (`references/localization-and-content-design.md`).
5. Identify the evidence available for any usability, conversion or performance claim (`references/research-and-usability.md`, `references/analytics-and-experiments.md`); mark unsupported claims "not measured".
6. Report observed rendered and interaction evidence, plus proposed acceptance checks. A review does not authorize a redesign.

Read `references/ui-design-workbook.md` for the decision table, symptoms, false positives, severity and worked example. Use `references/acceptance-checklist.md` for delivery acceptance and `references/visual-regression-and-devices.md` for the rendering matrix, Playwright baselines, Core Web Vitals evidence and axe automation.

## Implementation workflow

State the user flow and the smallest affected owner. Use existing tokens and component states; change a token at its source. Implement all states, then run the acceptance checks at the stated viewports, locales and browsers. Never refresh a visual baseline without a recorded acceptance decision. Report unrun checks as unexecuted. Deployment needs its own scope.

## Search Patterns for Quick Detection

Read-only leads; no match proves nothing; a match is a candidate until rendered. Exit 0 = match, 1 = none, 2 = error.

```sh
# structure and landmarks
rg -n -g '*.{php,html,json,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist}/**' -e '<(main|nav|header|footer|h[1-6]|button)\b|wp:group|wp:columns|elementor' .
# tokens and presets
rg -n -g '*.{css,scss,json,js,ts}' -g '!**/{vendor,node_modules,build,dist}/**' -e '--wp--preset--|--wp--custom--|var\(--|"(palette|fontSizes|spacingSizes)"' .
# layout risks
rg -n -g '*.{css,scss}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'width:\s*[0-9]{3,}px|min-width:\s*[0-9]{3,}px|overflow(-x)?:\s*(hidden|scroll)|@container|@media' .
# focus, motion, preferences, targets
rg -n -g '*.{css,scss}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'outline:\s*(none|0)|:focus-visible|prefers-reduced-motion|forced-colors|prefers-color-scheme' .
# states and feedback
rg -n -g '*.{php,html,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'aria-busy|aria-live|role="(alert|status)"|aria-invalid|aria-describedby|disabled' .
# direction and language
rg -n -g '*.{css,scss,php,html}' -g '!**/{vendor,node_modules,build,dist}/**' -e '(margin|padding)-(left|right)|text-align:\s*(left|right)|float:\s*(left|right)|\b(dir|lang)=' .
```

Reading the leads: `outline: none` matters only when no replacement focus style exists; `margin-left` matters only where direction should flip; fixed pixel widths matter only when they clip at a tested width; `overflow: hidden` may be deliberate.

## Output Format

Lead with the result and what was observed (viewports, browsers, locales, assistive tech actually used). Confirmed concern: location (file:line or URL+viewport), actor, trigger, reachable path, impact, confidence, minimal fix, regression check. Keep candidates and unmeasured claims separate. For implementation include the user flow, responsive and keyboard checks, screenshots when available, empty/loading/error/success states, commands with exit codes and unexecuted checks. A visual pass does not prove usability, conversion, screen-reader behavior or conformance.
