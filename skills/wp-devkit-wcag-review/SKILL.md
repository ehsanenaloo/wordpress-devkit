---
name: wp-devkit-wcag-review
description: Produce a WCAG 2.1 or 2.2 A/AA conformance assessment for WordPress journeys: scope, sampling, per-criterion Pass/Fail/Needs evidence/N-A, evidence and retest. Use for audits, ACR/VPAT input and go-live acceptance; fixing widget behavior goes to wp-devkit-accessibility-review.
---

# Conformance scope and criterion evidence

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Boundary with the accessibility skill

- This skill decides status against normative criteria for a defined scope and keeps the evidence trail. It never fixes components; each Fail is handed to `wp-devkit-accessibility-review` (how to build and repair the control) with the criterion attached.
- It is also not a legal opinion. Name the standard and version the client commits to; legal applicability (ADA, EAA, Section 508) is context to confirm with counsel (`references/standards-and-legal-context.md`).
- If the user only wants "is this dialog accessible / why can't I tab here", use the accessibility skill. Use this one when the answer must be a criterion-by-criterion status, a sampled audit, a conformance statement or an acceptance gate.

## Inputs and scope

Target version and level (default WCAG 2.2 AA; WCAG 2.1 AA when a contract or regulation names it), site or product boundary, complete processes in scope (checkout, account, forms), sample method, browser/device/AT matrix, build identity, third-party content, and existing evidence (previous audits, automated reports). Ask only what changes the claim.

## Code Review Workflow

1. Define the claim: version, level, scope, accessibility-supported baseline (browsers and AT). Record exclusions and third-party boundaries.
2. Build the sample with `references/audit-method.md`: structured set (templates, components, states), complete processes and a small random set.
3. Select criteria from `references/wcag-criteria.md` for the chosen version (2.1: 50 A/AA criteria incl. 4.1.1; 2.2: 55, 4.1.1 removed). Open the normative text and its exceptions before judging.
4. Gather evidence per criterion: source, rendered DOM, automated, keyboard, zoom/reflow/spacing, contrast measurements, assistive technology. Mix as each criterion demands.
5. Assign a status with reason: Pass (evidence cited), Fail (reproduced, with steps), Needs evidence (not tested or inconclusive), Not applicable (reason tied to scope). Never infer Pass from silence or a clean scan.
6. For each Fail record user impact, severity per the contract, owner, proposed remediation direction and a same-build retest. Use `references/deliverable-templates.md` for the deliverable.

Read `references/wcag-review-workbook.md` first for the decision rules, false positives and acceptance cases.

## References (read only what the task touches)

- `references/wcag-criteria.md` - read to select criteria and see the per-criterion test, WordPress hot spots and 2.1 versus 2.2 differences.
- `references/audit-method.md` - read to plan scope, sampling (WCAG-EM), evidence layers, tools and retest.
- `references/deliverable-templates.md` - read to write the criterion table, finding entries, conformance statement and ACR/VPAT input.
- `references/standards-and-legal-context.md` - read when a regulation, contract wording or "AAA/WCAG 3" question comes up.

## Implementation workflow

Only with authorization. Fix by criterion cluster at the owning component (hand to `wp-devkit-accessibility-review` for the pattern), keep the failing steps as regression tests, rerun the same sample on the same build, and update statuses with new evidence. Preserve unrelated work. Report unexecuted checks as unexecuted.

## Search Patterns for Quick Detection

Leads only; they read files and run no project code. Exit 0 match, 1 no match, 2 error. Matches select criteria to test, they are not failures. Shared exclusions: `-g '!**/{vendor,node_modules,build,dist,coverage,backups}/**'`.

```sh
# Names, alternatives, relationships (1.1.1, 1.3.1, 2.4.4, 2.5.3, 4.1.2)
rg -n -g '*.{php,html,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '<img\b(?![^>]*\balt=)' -e '<input\b[^>]*placeholder' -e 'aria-label=|aria-labelledby=' -e '>\s*(click here|read more|more)\s*<' -P .
# Keyboard, focus, shortcuts, traps (2.1.x, 2.4.3, 2.4.7, 2.4.11)
rg -n -g '*.{php,html,css,scss,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'tabindex="[1-9]' -e 'outline:\s*(none|0)\b' -e 'accesskey|keydown|keypress|position:\s*(fixed|sticky)' .
# Reflow, spacing, orientation, contrast sources (1.3.4, 1.4.4, 1.4.10, 1.4.12)
rg -n -g '*.{css,scss,php,html,json}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'orientation|min-width:\s*[0-9]{3,}px|overflow(-x)?:\s*hidden|!important|user-scalable|maximum-scale' .
# Media, motion, timing (1.2.x, 1.4.2, 2.2.x, 2.3.1)
rg -n -g '*.{php,html,css,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '<(video|audio|track|iframe)\b|autoplay|setInterval|setTimeout|@keyframes|prefers-reduced-motion' .
# Forms, errors, status, authentication, redundant entry (3.3.x, 4.1.3)
rg -n -g '*.{php,html,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'aria-invalid|aria-live|role="(alert|status)"|autocomplete=|onpaste|paste.*preventDefault|captcha|type="password"' .
# Pointer gestures, dragging, target size (2.5.x)
rg -n -g '*.{php,html,css,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'pointerdown|touchstart|mousedown|draggable|ondrag|sortable|swipe|touch-action' .
```

## Output Format

Lead with scope and claim (version, level, sample, matrix, build, date) and the overall result in one sentence that never says "compliant" unless every in-scope criterion has a Pass with evidence. Then the criterion table (criterion, version/level, status, evidence reference), then Fail entries: criterion, journey and state, file:line or URL, steps to reproduce, affected users, impact and severity, confidence, remediation direction, retest. Keep Needs evidence separate from Fail and list untested technologies, processes and AT. State coverage limits: a sampled pass is a pass for the sample only.
