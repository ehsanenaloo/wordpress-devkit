# Standards and legal context

Contents: [Standards map](#standards-map) - [Regulatory snapshot](#regulatory-snapshot) - [How to use this in an audit](#how-to-use-this-in-an-audit) - [WCAG 3.0 and AAA](#wcag-30-and-aaa) - [Sources and verification status](#sources-and-verification-status)

This file is context for choosing a target version. It is not legal advice and the legal facts change; verify against the primary text and confirm applicability with counsel before putting them in a deliverable.

## Standards map

| Standard | Web baseline | Notes |
| --- | --- | --- |
| WCAG 2.2 (W3C Recommendation, 5 Oct 2023) | A/AA/AAA criteria; 55 A/AA | WordPress core project expectation is 2.2 AA |
| WCAG 2.1 | 50 A/AA incl. 4.1.1 | Referenced by many current regulations |
| WCAG 2.0 | 38 A/AA | Section 508 baseline in the United States |
| EN 301 549 | Web clauses reference WCAG | v3.2.1 aligns web content with WCAG 2.1 AA; v4.1.1 is reported to align with 2.2 AA (see below) |

## Regulatory snapshot

Checked on 2026-10-08: ADA Title II (ada.gov), Section 508 (section508.gov), the ETSI publication listing and the WCAG 3.0 draft status were read at primary sources; the EAA application date and the Official Journal status of EN 301 549 v4.1.1 were not confirmed at a primary source.

- United States, ADA Title II (state and local governments): the DOJ rule adopts WCAG 2.1 AA. The ada.gov web rule page states WCAG 2.1 Level AA and, after an April 2026 interim final rule extending the deadlines, compliance dates of 26 April 2027 (population of 50,000 or more) and 26 April 2028 (smaller entities and special district governments). Check the Federal Register text for later changes. Private businesses (Title III) are not covered by that rule; litigation uses WCAG 2.1/2.2 AA as the practical benchmark.
- United States, Section 508 (federal ICT): WCAG 2.0 AA is the legal baseline; 2.1/2.2 are recommended best practice.
- European Union, European Accessibility Act (Directive (EU) 2019/882) applies from 28 June 2025 (confirm in the EUR-Lex text, Article 31) to specified consumer products and services including e-commerce; presumption of conformity comes through EN 301 549, which in v3.2.1 points to WCAG 2.1 AA. ETSI lists EN 301 549 v4.1.1 as published on 2 September 2026; secondary reports say its web clauses reference WCAG 2.2 AA instead of 2.1 AA and that it has no EAA presumption-of-conformity effect until cited in the Official Journal. Check the Official Journal before relying on v4.1.1 over v3.2.1. Member-state laws set enforcement and penalties.
- Other jurisdictions (UK Equality Act and PSBAR, Canada AODA/ACA, Ontario, Australia DDA) generally point to WCAG 2.x AA. Look them up when the client operates there.

## How to use this in an audit

1. Ask the client which standard and version they have committed to by contract or policy. If none, recommend 2.2 AA (a superset of 2.1 AA except 4.1.1).
2. If the legal baseline is 2.1 AA, report 4.1.1 and note the 2.2-only criteria as additional findings so the client is ready for the newer baseline.
3. For e-commerce serving the EU, include the complete purchase process in the sample; checkout is the usual enforcement focus.
4. Put the legal caveat in the deliverable: the audit measures technical conformance; it does not determine legal compliance.

## WCAG 3.0 and AAA

WCAG 3.0 is a W3C Working Draft (the 10 September 2026 draft states it may be updated, replaced or obsoleted at any time) with a different conformance model; do not audit against it or cite it as the standard. AAA criteria are not required for general conformance; W3C recommends not requiring AAA as a blanket policy because some content cannot satisfy it. Record AAA items (for example 2.4.12 Focus Not Obscured (Enhanced), 2.4.13 Focus Appearance, 3.3.9) as advisory unless the contract names them.

## Sources and verification status

Reviewed 2026-10-08.

- Verified against W3C primary pages: [What is new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/).
- Verified against WordPress primary page: [WordPress accessibility coding standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/accessibility/).
- Verified at primary pages: [ADA.gov web rule](https://www.ada.gov/resources/web-rule-first-steps/) (WCAG 2.1 AA, 2027/2028 dates); [ETSI EN 301 549 listing](https://www.etsi.org/deliver/etsi_en/301500_301599/301549/) (v4.1.1 dated 2026-09-02); [Section 508 applicability and conformance](https://section508.gov/develop/applicability-conformance) (WCAG 2.0 AA incorporated by reference); [WCAG 3.0 draft](https://www.w3.org/TR/wcag-3.0/).
- Secondary-source only (re-verify before use): EN 301 549 v4.1.1 content and Official Journal status ([Deque article](https://www.deque.com/blog/en-301-549-v4-1-1-is-final-what-changed-what-it-means-and-what-you-should-do/), [DWT summary](https://www.dwt.com/insights/2026/09/european-accessibility-act-ict-standards-update)). Not retrievable here: [Directive (EU) 2019/882](https://eur-lex.europa.eu/eli/dir/2019/882/oj); read Articles 2 and 31 for scope and the 28 June 2025 date.
