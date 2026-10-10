---
name: wp-devkit-accessibility-review
description: "Build, debug or review accessible WordPress controls: forms, errors, dialogs, menus, tabs, focus, live announcements, block, admin and WooCommerce UI. Use for keyboard and screen-reader behavior of a component; criterion-by-criterion status and audit scope belong to wp-devkit-wcag-review."
---

# Usable controls and assistive access

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Boundary with the WCAG skill

- This skill answers "does this control work for keyboard, screen-reader, zoom and voice users, and how do we fix it?". It works per component or journey and ends in a fix plus a retest.
- `wp-devkit-wcag-review` answers "what is the conformance status of this scope against WCAG 2.1/2.2 A/AA?". It owns sampling, per-criterion Pass / Fail / Needs evidence / Not applicable, and conformance wording.
- Findings here may cite a criterion as a pointer. Do not issue a Pass or a conformance claim from this skill. If the user wants a status table, an ACR/VPAT input or a go-live gate, switch to the WCAG skill and pass it the evidence gathered here.

## Inputs and scope

Journey and states (loading, empty, error, open, closed), rendered output or source owner (theme, block, plugin, admin, WooCommerce template), browser plus assistive technology if known, input methods, supported WordPress/theme versions. Inspect project evidence first; ask only what changes the decision.

## Code Review Workflow

1. Reproduce the journey in rendered output before trusting markup searches. Capture each state, not only the initial one. Identify who owns the markup (core, theme, block, plugin, third-party script).
2. Check the native-first rule: a real button, link, input, select, details or dialog beats a role on a div. For each custom control record accessible name, role, state/value and the keyboard contract of the chosen APG pattern.
3. Trace keyboard order, activation (Enter, Space), Escape, focus placement on open and focus return on close. Confirm nothing hidden stays focusable and nothing visible is unreachable.
4. Check forms and dynamic changes: label, instructions, error association, error summary, status announcements without focus theft, preserved input.
5. Check zoom/reflow (320 CSS px), text spacing, sticky-element obstruction, reduced motion and forced-colors in the browser.
6. Classify with the contract: confirmed finding (reproduced or proven from code path), candidate (needs AT or runtime evidence), or insufficient evidence. State which assistive-technology evidence is missing.

Read `references/accessibility-review-workbook.md` first for decision rules, false positives and the finding format.

## References (read only what the task touches)

- `references/wordpress-a11y-surfaces.md` - read for theme, block, admin, WooCommerce and core API specifics: skip links, `screen-reader-text`, `wp.a11y.speak`, `html5` support, nav menus, editor components, admin notices and list tables.
- `references/interactive-patterns.md` - read for dialogs, disclosure navigation, tabs, accordions, comboboxes, popovers, focus management, `inert` versus `aria-hidden`, drag alternatives.
- `references/forms-and-errors.md` - read for labels, validation, error summaries, autocomplete tokens, authentication, status messages and checkout forms.
- `references/testing-and-evidence.md` - read before proposing retests: manual keyboard/zoom/screen-reader script, axe with Playwright, what automation cannot see, evidence record.

## Implementation workflow

State the expected interaction (pattern, keys, announcements) and the smallest owning boundary before editing. Change the owning component, not a downstream patch. Keep core markup and filters when they already provide the behavior. Add the regression that failed (rendered-DOM or Playwright assertion, plus the manual script rows that automation cannot cover). Run the checks, record command and exit status, and list the unexecuted assistive-technology checks. Deployment and live-site changes need their own scope.

## Search Patterns for Quick Detection

Run only the groups relevant to the task from the first-party project root. They read files only. Matches are leads, not findings; no match proves nothing, because helpers, components and generated markup change the result. Exit code 0 is a match, 1 no match, 2 an error (record errors separately). Shared exclusions: `-g '!**/{vendor,node_modules,build,dist,coverage,backups}/**'`.

```sh
# Click handlers on non-interactive elements, positive tabindex, outline removal
rg -n -g '*.{php,html,js,jsx,ts,tsx,css,scss}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '<(div|span|li|a)\b[^>]*(onclick|role="button")' -e 'tabindex="[1-9]' -e 'outline:\s*(none|0)\b' .
# Controls that may lack a name: placeholder-only inputs, icon buttons, new-window links
rg -n -g '*.{php,html,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '<input\b[^>]*placeholder' -e '<button\b[^>]*>\s*<(svg|i|img)\b' -e 'target="_blank"' .
# ARIA that often hides a problem: menu roles, aria-hidden, naming on generic elements, live regions
rg -n -g '*.{php,html,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'role="(menu|menubar|menuitem|application|tablist)"' -e 'aria-hidden="true"' -e 'aria-live|role="(alert|status)"|wp\.a11y|@wordpress/a11y' .
# Dialogs and focus handling
rg -n -g '*.{php,html,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '<dialog|showModal|aria-modal|\.focus\(|activeElement|keydown|Escape|\binert\b|popover' .
# Visual hiding, reduced motion, sticky layers that can obscure focus
rg -n -g '*.{css,scss,php,html}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'display:\s*none|visibility:\s*hidden|screen-reader-text|prefers-reduced-motion|position:\s*(fixed|sticky)|scroll-padding|forced-colors' .
# Theme support and core output that other findings depend on
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e "add_theme_support\(\s*'html5'" -e 'skip-link|get_search_form|wp_nav_menu|comment_form|wp_enqueue_script\([^)]*a11y' .
```

## Output Format

Start with the verdict, the reviewed scope (journeys, states, browsers/AT) and what was not tested. For each confirmed finding give: file:line, component and state, actor (keyboard, screen-reader, low-vision, voice, motor), trigger and steps, observed versus expected behavior, impact, confidence, minimal fix in the owning component, regression check, and an optional criterion pointer. Severity follows demonstrated impact (blocked task = CRITICAL for a core journey; degraded but workable = WARNING; polish = INFO). Keep candidates and "insufficient evidence" in separate lists. For implementation, add changed boundaries, commands with exit codes, and manual checks still owed.
