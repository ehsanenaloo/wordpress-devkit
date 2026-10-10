---
name: wp-devkit-security-review
description: "Review or remediate reachable WordPress security defects: missing capability or ownership checks, XSS, SQL injection, CSRF, SSRF, unsafe uploads, secrets, dependency risk, multisite isolation. Use for plugin/theme/REST/AJAX audits and exploit-path triage; route design belongs to the REST skill."
---

# Security paths and exploit evidence

Read `references/engineering-contract.md` first. A review request is read-only: trace, explain and recommend; do not edit, mutate data, send attack traffic or execute untrusted project code. Switch to the implementation workflow only when the user authorizes changes.

Hand off: REST route and schema design to `wp-devkit-rest-api-development`; WooCommerce payment or order flows to `wp-devkit-woocommerce-dev`; CI gate wiring to `wp-devkit-ci-cd-and-release-engineering`; hosting and WP-CLI operations to `wp-devkit-wpcli-and-ops`. Stay here for the exploit path itself.

## Inputs

Entry surface, attacker role (anonymous, subscriber, wrong-owner, admin, other site), affected object or tenant, target WordPress/PHP/plugin versions, existing helpers, and a safe reproduction boundary. Inspect the repository before asking. Ask only what changes the verdict or the execution boundary; state assumptions.

## Code Review Workflow

1. Enumerate entrypoints: `admin-ajax` and `admin_post_*` actions (including `nopriv`), REST routes, shortcodes, block render callbacks, form/`init`/`template_redirect` handlers, cron and WP-CLI callbacks, uploads, webhooks, `unserialize` of stored data.
2. For each, record who can call it, what they control, and which sink they reach (SQL, HTML/JS/URL output, filesystem, outbound request, include/exec, option or capability write).
3. Walk source to sink and note each control actually on the path: authentication, capability or object ownership, intent (nonce), validation, parameterization, context escaping, destination allowlist. Core helpers and shared wrappers count; read them.
4. A control is missing only if no layer on the reachable path provides it. Public-by-design behavior is not a defect; abuse of it is, if bounded limits are absent and impact is shown.
5. Run the false-positive checks in `references/security-review-workbook.md`. Classify per the contract: demonstrated impact sets severity, authentication alone does not downgrade it.
6. Propose the fix at the failing boundary and a regression that uses three actors: authorized owner, authenticated wrong owner, anonymous. Do not implement it during review.

Read `references/security-review-workbook.md` for severity calibration, the finding template, false-positive catalogue and acceptance checks. Then load only the topic references below.

## Implementation workflow

1. Restate the expected behavior and the smallest boundary to change; check the oldest supported WordPress/PHP.
2. Write the failing regression first (wrong-owner write, harmless XSS marker, quoted SQL value, blocked internal URL).
3. Fix at the sink or the authorization boundary, not by adding a downstream filter. Keep the intended behavior for the authorized actor.
4. Run the regression, the project's lint/static analysis and relevant tests; record command and exit status.
5. Never weaken a check, widen an ignore or regenerate a baseline to get green. Deployment, secret rotation and live remediation are separate, explicitly authorized tasks.

## Search Patterns for Quick Detection

Read-only leads from the first-party root; they do not bootstrap WordPress. Matches are candidates, never findings; no match proves nothing. Exit codes: 0 match, 1 no match, 2 error (record errors separately). Narrow `.` when possible. `rg` honors `.gitignore`; use `--no-ignore` only on a named directory.

```sh
scan() { rg -n -g '*.{php,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e "$1" "${2:-.}"; }
scan '\$_(GET|POST|REQUEST|COOKIE|FILES|SERVER)\b|wp_ajax_|admin_post_|register_rest_route|add_shortcode'   # entrypoints
scan 'current_user_can|map_meta_cap|permission_callback|check_(ajax|admin)_referer|wp_verify_nonce|is_user_logged_in'   # controls present
scan '\$wpdb->(query|get_(results|var|row|col)|prepare)|ORDER\s+BY|LIMIT\s+\$|IN\s*\('   # SQL sinks
scan '\becho\b|\bprint\b|esc_(html|attr|url|js)\b|wp_kses|innerHTML|dangerouslySetInnerHTML|insertAdjacentHTML|document\.write|\.html\('   # output sinks
scan '\b(eval|exec|shell_exec|system|passthru|proc_open|popen|unserialize|maybe_unserialize|extract|call_user_func(_array)?)\s*\(|\b(include|require)(_once)?\s*\(?\s*\$'   # execution
scan 'move_uploaded_file|wp_handle_(upload|sideload)|file_put_contents|unlink|ZipArchive|wp_remote_|wp_safe_remote_|curl_init|file_get_contents\s*\(\s*\$|wp_redirect|header\s*\(\s*.Location'   # files, network, redirects
scan 'api[_-]?key|client_secret|private[_-]?key|Authorization|Bearer|error_log|var_dump|print_r|WP_DEBUG'   # secrets, leakage
scan 'switch_to_blog|restore_current_blog|get_current_blog_id|rate_limit|hash_equals|hash_hmac|DISALLOW_FILE_EDIT'   # isolation, integrity
```

Judge each hit by tracing the path, not the line. Typical benign hits: fixed includes, `echo` of escaped or integer values, `wp_redirect` to a hard-coded admin URL, `unserialize` of internally generated data that no user can write.

## Task-selected resources

- `references/access-control-and-csrf.md`: capability and object checks, REST/AJAX/admin-post, nonces, application passwords, role and privilege writes, multisite capabilities. Read for any authorization or CSRF question.
- `references/input-output-and-sql.md`: validation vs sanitization, `wp_unslash`, `$wpdb->prepare` including `%i` and LIKE/IN, escaping by context, DOM sinks, serialization. Read for XSS, SQL injection or object injection.
- `references/files-network-and-execution.md`: uploads, path traversal, archives, SSRF and redirects, include/exec. Read when the path touches files, outbound requests or code execution.
- `references/abuse-multisite-concurrency.md`: public endpoints, brute force, webhooks, tenant isolation, races. Read for abuse, replay, quota or cross-site questions.
- `references/dependency-supply-chain.md`: Composer/npm audits, provenance, CI actions. Read for dependency or build-chain scope.
- `references/runtime-hardening.md`: deployed headers, cookies, debug, file policy, DAST bounds. Read when deployed configuration is in scope.
- `references/secrets-and-integrity.md`: secret scanning, rotation, checksums, CSP rollout, personal data in logs. Read for exposed credentials, tampering or privacy exposure.

## Output Format

Lead with the verdict and reviewed scope. Per confirmed finding use the template in the workbook: severity, `file:line`, actor, trigger, path source to sink, impact, confidence, minimal fix, regression. List candidates and missing evidence separately. End with executed checks (command, exit status), unexecuted checks and residual risk. For implementation add changed boundaries and the before/after regression result. "No findings" means none in the inspected scope, not that the system is secure.
