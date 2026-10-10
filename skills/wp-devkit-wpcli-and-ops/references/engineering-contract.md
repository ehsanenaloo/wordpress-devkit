# Engineering and evidence contract

Apply this contract before domain heuristics. Treat examples, grep matches and historical reference checklists as investigation leads, not proven defects. This contract overrides conflicting blanket severity rules in the bundled references.

1. Discover the actual WordPress, PHP, WooCommerce, Node and tooling versions from the project. Consult primary documentation for version-sensitive APIs; never invent API behavior or silently upgrade dependencies.
2. Establish whether the request authorizes review, implementation or deployment. Keep review read-only. For implementation, state a concise design, affected boundaries and validation plan before editing. Keep unrelated code unchanged.
3. Trace source, transformations, authorization, sink and reachable execution path. Account for core APIs, hooks, middleware and deliberate public behavior before reporting missing controls.
4. Separate confirmed findings from hypotheses. Include file:line, trigger or reproduction, affected actor, impact, confidence, remediation and a relevant regression check. Do not assign a vulnerability CWE to a style preference.
5. Classify by demonstrated impact: CRITICAL for reachable compromise, irreversible data loss or a release-blocking failure; WARNING for supported correctness, security, compatibility or performance concerns; INFO for optional improvements. Authentication alone does not justify downgrading a severe issue. Label unverified candidates separately.
6. Never use a WordPress nonce as authentication or authorization. Assess CSRF against the actual cookie/session model. A public read endpoint or intentional public submission is not automatically a vulnerability. Authenticated REST requests may use cookie nonces or another supported authentication model.
7. Validate according to the actual change: lint/static analysis, relevant unit/integration tests, browser behavior and visual screenshots where appropriate. Discover configured commands; do not claim execution from reading config. Record command, exit status and coverage limits. Tool absence is an unexecuted check, not a pass.
8. Never regenerate baselines, disable checks, weaken authorization or broaden ignores merely to obtain green CI. Explain unavoidable exceptions with a narrow scope and rationale.
9. Redact secrets and personal data from logs and fixtures. Never execute untrusted Blueprint PHP, shell snippets, project bootstrap code or downloaded scripts merely to inspect them. Use a disposable environment for runtime verification.
10. Report reviewed scope, findings, changes, executed checks, unexecuted checks and residual risks. No findings in the inspected scope does not mean the whole system is secure.
