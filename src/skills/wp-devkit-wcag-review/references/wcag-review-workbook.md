# WCAG review workbook

Contents: [Status vocabulary](#status-vocabulary) - [Decision rules](#decision-rules) - [2.1 versus 2.2](#21-versus-22) - [Common mistakes in assessments](#common-mistakes-in-assessments) - [Looks failing but passes](#looks-failing-but-passes) - [Looks passing but fails](#looks-passing-but-fails) - [Severity versus failure](#severity-versus-failure) - [Evidence needed per status](#evidence-needed-per-status) - [Acceptance checks](#acceptance-checks) - [Sources](#sources)

Apply [the engineering contract](engineering-contract.md) first. Companion files: [criteria](wcag-criteria.md), [method](audit-method.md), [report templates](deliverable-templates.md), [standards and legal context](standards-and-legal-context.md).

## Status vocabulary

| Status | Use when | Never use when |
| --- | --- | --- |
| Pass | The criterion applies, evidence for the sampled states shows it is met, evidence is cited | Only a scan ran, or a state was not exercised |
| Fail | A reproducible state violates the criterion (steps, URL, build) | Style preference, best practice without a criterion, or a candidate lead |
| Needs evidence | A required test was not run, the tool was unavailable, or the result is inconclusive (axe `incomplete`) | You are unsure and want to look cautious: say exactly what is missing |
| Not applicable | The content or function the criterion governs does not exist in scope (no video, no time limit, no authentication) | The criterion is merely hard to test, or applies on pages outside the sample |

A sampled Pass does not extend to unsampled pages, and a Not applicable reason must be re-validated when content changes.

## Decision rules

- Start from the claim. Unclear scope makes every status unreliable: fix version, level, boundary, sample, processes and matrix first.
- Conformance has five requirements (WCAG 2.2): conformance level, full pages, complete processes, only accessibility-supported ways of using technologies, non-interference. Four criteria (1.4.2, 2.1.2, 2.3.1, 2.2.2) apply to all content on a page even content that is not relied upon. Check them on pages with third-party widgets.
- Complete processes: if any step of checkout fails, the process is not conforming at that level. Test every step and its error states, including payment and confirmation.
- Third-party content you cannot control may justify partial conformance wording; it does not turn a Fail into a Pass. List providers and versions, and re-sample when they change.
- Responsive variants are separate pages for conformance: test each layout breakpoint that changes structure.
- An automated violation is a lead; reproduce and map it to a criterion mechanism (the specific success criterion text) before calling it a Fail. An automated pass is evidence for the rules that ran, only.
- Every Fail needs the user-visible mechanism. "Missing alt" is a lead; "Product image link has no accessible name, so screen-reader users hear 'link' in the product grid" is a Fail under 1.1.1/2.4.4/4.1.2.
- Prefer one criterion per root cause for the headline count, but list secondary criteria (a missing label commonly maps to 1.3.1, 2.4.6, 3.3.2 and 4.1.2).

## 2.1 versus 2.2

- WCAG 2.2 (W3C Recommendation, 5 October 2023) adds nine criteria. A/AA ones: 2.4.11 Focus Not Obscured (Minimum) AA, 2.5.7 Dragging Movements AA, 2.5.8 Target Size (Minimum) AA, 3.2.6 Consistent Help A, 3.3.7 Redundant Entry A, 3.3.8 Accessible Authentication (Minimum) AA. AAA additions: 2.4.12, 2.4.13, 3.3.9.
- 4.1.1 Parsing is removed in 2.2 as obsolete. Under a 2.1 commitment it is still listed, but the W3C Understanding document says to consider it always satisfied for content using HTML or XML, and axe tags the rule `wcag2a-obsolete` (no longer required for conformance). For a 2.1 audit record 4.1.1 as Pass for HTML with that note; report duplicate ids or broken nesting that actually change names, roles or relationships under 1.3.1, 4.1.2 or the criterion they break.
- Content that conforms to 2.2 also meets the 2.1 criteria except that 4.1.1 is no longer tested; a 2.1-only audit does not cover the six new 2.2 A/AA criteria. If a client says "WCAG 2.2" ask whether the target is A, AA or AAA.
- Counts: 2.1 has 50 A/AA criteria, 2.2 has 55. State which version the statement uses.

## Common mistakes in assessments

- Reporting "Pass" for 2.1.1 because no keyboard test was run.
- Treating contrast tool output of a static page as 1.4.3 and 1.4.11 coverage when state colors (hover, focus, disabled, error) were not measured.
- Counting a skip link as 2.4.1 Pass without checking that it works, is visible on focus and that the target takes focus.
- Using Lighthouse or axe scores as the conformance result.
- Excluding the checkout, login or consent banner from the sample because "it is a plugin".
- Reporting the same defect on every page instead of once with a pattern and affected URLs.
- Failing 2.4.7 on a custom focus style without measuring it; or passing 2.4.7 while 2.4.11 fails because a sticky element covers the focus.
- Assigning severity from WCAG level (A means critical): level is conformance weight, severity is user impact on the task.

## Looks failing but passes

- Placeholder-less input whose label is `aria-label` and visible text exists nearby: acceptable if the accessible name contains the visible text and a visible label or equivalent exists (3.3.2).
- Decorative image with `alt=""` or CSS background: Pass for 1.1.1 if truly decorative.
- Heading level skip with clear structure: not a 1.3.1 Fail by itself; evaluate the relationship.
- Small inline text links: 2.5.8 inline exception; undersized targets with enough spacing (24 CSS px circle rule) also pass.
- Fixed header present, but `scroll-padding` keeps focus visible: 2.4.11 Pass.
- Modal dialog covering the page: not a 2.4.11 failure (modal takes focus); tooltips and menus that close on blur are excluded.
- Auto-playing audio under three seconds (1.4.2) or moving content that stops within five seconds (2.2.2).
- Time limit that is essential (auction, real-time event) per 2.2.1 exceptions.
- Password field that allows paste and autofill with a password manager: 3.3.8 Pass without further alternative.

## Looks passing but fails

- Contrast measured on a screenshot with image or gradient backgrounds: measure the worst case.
- Alt text exists but is a file name, the product SKU, or "image".
- Focus indicator exists but is below 3:1 against adjacent colors where 1.4.11 applies (2.4.11 is about obscuring, not contrast; 2.4.13 Focus Appearance is AAA).
- Error messages in red only (1.4.1), or shown in a toast that is removed before the user reads it (2.2.1/3.3.1).
- Keyboard works but Escape does not close a dialog and focus is lost (2.1.1 passes while 2.4.3 fails).
- Language attribute present but wrong on a translated site (3.1.1).
- Drag to reorder without a pointer or keyboard alternative (2.5.7, 2.1.1).
- Cookie banner or chat widget that obscures focused controls (2.4.11).
- Authentication demanding a typed code that cannot be pasted (3.3.8).

## Severity versus failure

A criterion Fail is binary. Severity (contract) describes impact and priority:
CRITICAL: a core task (browse, search, add to cart, check out, log in, contact) cannot be completed by an affected user group, or an escape trap exists.
WARNING: completable with workaround, or non-core content affected.
INFO: not a failure; advisory (AAA-level idea, best practice).
Report CRITICAL fails first for a go-live decision; do not hide WARNING fails when stating conformance, because conformance is all-or-nothing within the claimed scope.

## Evidence needed per status

| Criterion family | Minimum evidence for Pass | Typical Needs evidence reason |
| --- | --- | --- |
| Text alternatives, names, relationships | Rendered accessibility tree plus screen-reader spot check of the sampled components | AT not run |
| Keyboard, focus, shortcuts | Recorded keyboard walkthrough per state | Dynamic overlay not opened |
| Contrast, spacing, reflow, orientation | Measured values per state, zoom screenshots | Only default state measured |
| Time, motion, flashing, media | Content inventory plus control tests; flash analysis tool or content review | Third-party player untested |
| Forms, errors, authentication | Submitted invalid and valid paths, password-manager test | Server errors not triggered |
| Status messages, name/role/value | Screen-reader announcement observed | Only DOM inspected |

## Acceptance checks

- Scope statement, version, level, sample method, matrix and build id appear on the first page of the deliverable.
- Every in-scope criterion has exactly one status with evidence or reason; Needs evidence and Fail are never mixed.
- Every Fail has reproducible steps, mechanism, user impact, remediation direction and a retest on the same build.
- The summary uses wording allowed by the evidence (see report templates) and lists untested technologies and processes.
- Retest results update the status table; an earlier Fail is not removed without evidence.

A completed audit proves status for the stated sample, build and tool/AT versions. It does not prove conformance of unsampled pages, later content, third-party updates, other assistive technology, or legal compliance.

## Sources

Reviewed 2026-10-08.

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [WCAG 2.1](https://www.w3.org/TR/WCAG21/)
- [What is new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
- [Understanding conformance](https://www.w3.org/WAI/WCAG22/Understanding/conformance)
- [Understanding Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html), [Accessible Authentication (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html)
- [axe-core tags](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md)
