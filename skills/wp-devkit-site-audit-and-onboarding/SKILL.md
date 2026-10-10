---
name: wp-devkit-site-audit-and-onboarding
description: "Inventory an inherited or unfamiliar WordPress project: stack and version discovery, ownership map, drop-ins and mu-plugins, environment doctor, risk-ranked routing to specialist skills. Read-only first pass; use a domain skill directly when the problem is already known."
---

# Project discovery and evidence-led routing

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Boundary with sibling skills

This skill answers "what is this project, who owns what, what do we not know, and which specialist should look first?". It does not perform the specialist review. Route security to `wp-devkit-security-review`, speed to `wp-devkit-performance-review`, orders and checkout to `wp-devkit-woocommerce-dev`, saved block content to `wp-devkit-block-development`, upgrades and data changes to `wp-devkit-migration-upgrade-review`, WP-CLI operations to `wp-devkit-wpcli-and-ops`, pipelines to `wp-devkit-ci-cd-and-release-engineering`, tests to `wp-devkit-test-strategy`. An inventory is not a security audit, performance audit, accessibility audit or penetration test.

## Inputs and scope

Authorized target path (repository, plugin, theme, or a container the owner named), requested outcome, which access exists (source only, database, running site, hosting panel), setup docs and ownership notes, and the decision the inventory feeds. Confirm what may be executed. Default is static reading plus the bundled doctor in filesystem mode.

## Code Review Workflow

1. Separate evidence sources: first-party source, vendored dependencies, generated or built artifacts, deployment configuration and the live site. Read project instructions (README, CONTRIBUTING, CLAUDE.md, runbooks) first.
2. Classify the shape from several signals (`references/stack-signals-and-ownership.md`): plugin, theme (block, classic, hybrid, child), block library, WooCommerce, headless, builder-driven, multisite, composer-managed (Bedrock-style), monorepo.
3. Discover versions with the trust order in `references/safe-inventory.md`: runtime evidence over lockfiles over headers over documentation. Name the source of each version and mark unknown activation, storage, hosting and deployment state as unknown.
4. Map owners: bootstrap, content model, rendering, API, build, tests, delivery, hosting layer (drop-ins, mu-plugins, platform plugins). Keep the map short enough to guide the next task.
5. Rank specialist follow-ups by potential impact times missing evidence (`references/routing-and-deliverable.md`). An unverified webhook, upgrade directory or `eval` is a candidate, not a confirmed critical.
6. For doctor requests follow `references/doctor.md`: filesystem mode by default; a trusted container runtime only with explicit authorization.

Read `references/site-audit-and-onboarding-workbook.md` first for decision rules, false positives and acceptance checks.

## References (read only what the task touches)

- `references/stack-signals-and-ownership.md` - read to classify the project and interpret wp-content layout, drop-ins, mu-plugins, multisite and environment constants.
- `references/safe-inventory.md` - read before running any command: what is read-only, what executes code, version trust order, secret redaction.
- `references/routing-and-deliverable.md` - read to choose follow-up skills, grade candidates and write the onboarding deliverable.
- `references/doctor.md` - read for the bundled environment doctor (`scripts/doctor.py`, `scripts/evidence_report.py`), its output, exit codes and limits.

## Implementation workflow

Only when authorized: write onboarding documentation or ownership notes, add the missing runbook, or wire the doctor into a documented procedure. Do not update plugins, flush caches, run cron, repair data or change configuration as part of inventory. Keep generated evidence outside the inspected tree, redact secrets, and report each command with its exit status.

## Search Patterns for Quick Detection

Leads only; they read files and run no project code. Exit 0 match, 1 no match, 2 error. Do not print secret values: use `-l` or `--count` on configuration files. Shared exclusions: `-g '!**/{vendor,node_modules,build,dist,coverage,backups}/**'`.

```sh
# Shape: plugin and theme headers, block theme markers, block registrations
rg -n -g '*.{php,css,json}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '^\s*\*?\s*(Plugin Name|Theme Name|Template|Requires at least|Requires PHP|Requires Plugins|Update URI):' -e 'register_block_type|"apiVersion"|"\$schema"' .
# Builders and content ownership
rg -l -g '*.{php,json,js}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'elementor|wpbakery|vc_row|et_pb_|fusion_builder|beaver|bricks|breakdance|add_shortcode' .
# Topology: multisite, environments, composer-managed layout (names only, no values)
rg -l -g '*.{php,json,yml,yaml,env,example}' -e 'MULTISITE|SUBDOMAIN_INSTALL|WP_ENVIRONMENT_TYPE|WP_ENV|WP_CONTENT_DIR|WPMU_PLUGIN_DIR|roots/bedrock|roots/wordpress' .
# Surfaces: routes, post types, commerce, cron, custom tables
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'register_rest_route|register_post_type|register_taxonomy|wp_schedule_event|as_schedule_|dbDelta|admin_post_|wp_ajax_|woocommerce_' .
# Delivery and quality tooling that exists (configured is not executed)
rg --files --hidden -g '{composer.json,package.json,phpunit.xml*,phpstan.neon*,phpcs.xml*,.wp-env.json,playwright.config.*,.github/workflows/*,.gitlab-ci.yml,Dockerfile,docker-compose*.y*ml,.ddev/config.yaml,.lando.yml,pantheon.yml}' .
# Risky constructs worth a specialist look (candidates only)
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '\beval\s*\(|base64_decode\s*\(|unserialize\s*\(|\$wpdb->query\s*\(\s*"|shell_exec|passthru|proc_open|file_put_contents\s*\(.*\$_(GET|POST|REQUEST)' .
```

## Output Format

Lead with the project shape in one sentence and the evidence level (static source only, source plus doctor, trusted runtime). Then: inventory table (component, version, source of the version, confidence), ownership map, hosting and runtime layers found, unknowns with the single observation that would resolve each, ranked specialist follow-ups (candidate, why, evidence needed, which skill, first command), and blockers to starting work. Label static inspection, database evidence and runtime execution separately. Never print secret values. Never call a candidate CRITICAL; severity needs a reachable path and demonstrated impact (contract). End with checks executed with exit codes and checks not executed.
