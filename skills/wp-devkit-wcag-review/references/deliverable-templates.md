# Deliverable templates

Contents: [Summary block](#summary-block) - [Criterion table](#criterion-table) - [Finding entry](#finding-entry) - [Conformance wording](#conformance-wording) - [ACR / VPAT input](#acr--vpat-input) - [Retest log](#retest-log) - [Sources](#sources)

Use these structures so another reviewer can reproduce each status. Fill every field or write "not recorded"; never invent evidence.

## Summary block

```text
Standard:      WCAG 2.2 Level AA (or 2.1 AA)
Scope:         <domains, subsites, processes in scope> / <exclusions>
Sample:        <N structured + M random pages + processes>, selection method
Baseline:      <browsers, screen readers, devices with versions>
Build:         <commit or release, environment, date>
Result:        <one sentence: counts of Pass / Fail / Needs evidence / Not applicable>
Highest risk:  <CRITICAL fails that block core tasks>
Not tested:    <technologies, processes, AT, content>
```

## Criterion table

| Criterion | Version/level | Status | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1.1 Non-text Content | 2.1, 2.2 A | Fail | F-003, trace ref | Product grid image links have no name |
| 2.5.8 Target Size (Minimum) | 2.2 AA | Pass | measured 24x24 px or spacing exception, 5 samples | Inline links excluded |
| 3.3.8 Accessible Authentication (Minimum) | 2.2 AA | Needs evidence | - | MFA step not tested (no test account) |
| 1.2.2 Captions (Prerecorded) | 2.1, 2.2 A | Not applicable | no prerecorded synchronized media in scope | Recheck when video added |

One row per criterion in scope. Status is one of Pass, Fail, Needs evidence, Not applicable.

## Finding entry

```text
ID:          F-003
Criteria:    1.1.1 (primary), 2.4.4, 4.1.2 (secondary)  | WCAG 2.2 A
Severity:    WARNING | CRITICAL | INFO (per user impact; not by WCAG level)
Confidence:  confirmed
Where:       URL(s) / template file:line / component; states affected
Actor:       screen-reader user, keyboard user, low vision, voice control, motor
Steps:       1..n to reproduce, with environment
Observed:    what happens
Expected:    what the criterion requires in this context
Impact:      what the user cannot do or must work around
Evidence:    screenshot, recording, trace, accessibility-tree dump, tool output ref
Remediation: direction at the owning component (hand to wp-devkit-accessibility-review)
Retest:      same steps on same kind of build, expected result
```

## Conformance wording

Allowed phrasing depends on evidence:

- All in-scope criteria Pass with cited evidence: "In the evaluated scope, on build X, tested with Y, the content meets WCAG 2.2 Level AA success criteria. This statement covers the sampled pages and processes listed; it is not a guarantee for pages outside the sample."
- Any Fail: "Does not currently meet WCAG 2.2 Level AA in the evaluated scope. N criteria fail; see findings."
- Needs evidence remains: "Partially evaluated; conformance is not established until the listed criteria are tested."
- Third-party content out of control: use partial conformance wording naming the content; conformance is claimed for the rest.

A conformance claim, if made, includes date, scope (URLs or patterns), WCAG version and level, relied-upon technologies, and the accessibility-supported baseline; optionally the user agents and AT used for testing. Tools and scores alone never support the claim. Do not use "certified", "fully compliant" or "legally compliant".

## ACR / VPAT input

Vendors producing an Accessibility Conformance Report in the VPAT format record per criterion: Supports, Partially Supports, Does Not Support, Not Applicable, Not Evaluated. Map statuses: Pass to Supports; Fail in all instances to Does Not Support; Fail in some instances to Partially Supports; Needs evidence stays open until tested (do not report it as Supports); "Not Evaluated" is, per the VPAT 2.5 wording used in published ACRs, only for WCAG AAA criteria, so it is not a valid status for A/AA rows (check the current ITI edition); Not applicable stays. Remarks name the test method, environment and affected components. The legal or sales owner decides publication; this skill supplies the evidence table.

## Retest log

```text
Finding   Build before   Build after   Steps rerun   Result (fixed / not fixed / regressed)   Evidence
F-003     a1b2c3         d4e5f6        1-4           fixed                                    trace link
```

Record also any new failures introduced by the fix. Keep Fail until the retest shows the criterion met in the same states.

## Sources

Reviewed 2026-10-08.

- [WCAG 2.2 conformance requirements and claims](https://www.w3.org/WAI/WCAG22/Understanding/conformance)
- [WCAG-EM reporting](https://www.w3.org/TR/WCAG-EM/)
- [ITI VPAT page](https://www.itic.org/policy/accessibility/vpat) (template and terminology; the page lists VPAT 2.5Rev, April 2025, in 508, EU, WCAG and INT editions; confirm current edition)
