# Engineering and evidence contract

Apply this contract before WCAG heuristics. A match in source or an automated report is an investigation lead, not proof of a criterion failure.

1. Discover the actual WordPress, PHP, browser, JavaScript and assistive-technology versions in scope. Verify version-sensitive behavior with primary documentation. Version numbers written in these files never say what is current: look up the latest release and its documentation online from the official source, and record the version you used.
2. Keep review, remediation and deployment separate. State the requested posture and the exact paths being assessed before changing code.
3. Trace the reachable user journey from source to rendered output and state changes. Include server-rendered, client-rendered, embedded and third-party content boundaries.
4. Record criterion, level, trigger, reproduction, affected user, impact, evidence, confidence, remediation and retest. Do not map a style preference to a WCAG failure without a criterion and mechanism.
5. Automated tools can find candidates and regressions; they do not establish keyboard, screen-reader, zoom, reflow, timing or context outcomes by themselves.
6. Do not claim WCAG conformance or certification from a partial audit. Use `Needs evidence` when a required environment or manual test was not executed.
7. Redact secrets and personal data from screenshots, URLs, logs and fixtures. Do not execute untrusted project code or downloaded scripts merely to inspect it.
8. Report the exact commands, tool versions, browsers, assistive technologies, viewport/zoom settings and unexecuted checks.
