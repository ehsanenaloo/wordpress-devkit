# Routing and onboarding deliverable

Contents: [Routing table](#routing-table) - [Prioritizing follow-ups](#prioritizing-follow-ups) - [Candidate grading](#candidate-grading) - [Deliverable template](#deliverable-template) - [Worked example](#worked-example) - [Common first-week outputs](#common-first-week-outputs) - [Sources](#sources)

## Routing table

Route by the outcome the owner needs, using what the inventory showed. The skills below exist in this pack.

| If the inventory shows or the owner asks for | Next skill |
| --- | --- |
| Custom plugin lifecycle, hooks, settings, uninstall, activation | `wp-devkit-plugin-development` |
| Theme templates, `theme.json`, Site Editor, child theme | `wp-devkit-theme-development` |
| Custom blocks, saved content, deprecations, build chain | `wp-devkit-block-development` |
| Orders, checkout, payments, webhooks, HPOS, subscriptions | `wp-devkit-woocommerce-dev` |
| Custom REST routes, permission callbacks, schemas | `wp-devkit-rest-api-development` |
| WPGraphQL, Faust, frontend revalidation, preview | `wp-devkit-headless-and-wpgraphql` |
| ACF field groups, CPT/taxonomy model, meta queries | `wp-devkit-acf-and-content-modeling` |
| Settings screens, list tables, admin UI | `wp-devkit-admin-ui-development` |
| Authentication, authorization, escaping, file handling, secrets | `wp-devkit-security-review` |
| Slow pages, queries, object cache, Core Web Vitals | `wp-devkit-performance-review` |
| Schema changes, data migration, version upgrades, builder removal | `wp-devkit-migration-upgrade-review` |
| WP-CLI scripts, cron, multisite operations, backups | `wp-devkit-wpcli-and-ops` |
| CI/CD, release packaging, deploy and rollback | `wp-devkit-ci-cd-and-release-engineering` |
| Missing or weak tests, flaky suites | `wp-devkit-test-strategy` |
| Static analysis, types, baseline | `wp-devkit-phpstan-review` |
| Keyboard, screen reader, component accessibility | `wp-devkit-accessibility-review` |
| Conformance audit against WCAG | `wp-devkit-wcag-review` |
| Visual design, tokens, content, device design | `wp-devkit-ui-design` |
| Reproducible sandbox or Blueprint | `wp-devkit-playground-development` |

Specialist skills inspect the code deeply; this skill only decides order and what each needs.

## Prioritizing follow-ups

Rank each candidate by: potential impact if real (money, data, access, availability, compliance), likelihood given the evidence, and cost of the missing evidence. A short list wins over a long one: three follow-ups with the exact first check for each.

Typical high-priority candidates (all unconfirmed until a specialist traces them):

- Payment, webhook and auth surfaces with no visible validation near them.
- Schema or upgrade routines (`dbDelta`, version options, custom tables) with no tests or rollback.
- Release automation that can publish without verification, or manual FTP/SFTP deploy.
- Custom endpoints with `permission_callback` absent or permissive.
- Debug flags, exposed backup or dump files, committed secrets (hand to security; do not open the contents).
- EOL runtime: unsupported PHP or WordPress branch. Check the current PHP support table and WordPress release archive before stating EOL status.
- No backup restore evidence, no staging, single person deploys.
- Heavy builder dependence combined with a modernization request.

## Candidate grading

Follow the contract: CRITICAL needs a reachable path and demonstrated impact; unverified findings stay candidates. Use these labels in the deliverable:

- Confirmed: seen in the artifact with trace (for example a committed `.env` with a real-looking key, `WP_DEBUG_DISPLAY` true in a production-typed config).
- Candidate: plausible from a signal, needs a specialist check (webhook route without visible signature check in the file you read).
- Unknown: required fact not available (production PHP version, whether the plugin is active).
- Informational: structure or hygiene with no demonstrated failure.

Do not put an unverified candidate under a CRITICAL heading; put it in a "Priority candidates" list with the evidence needed. An unverified webhook is a priority candidate, not a critical finding.

## Deliverable template

```text
Project shape: <one sentence>   Evidence level: static | static+doctor | trusted runtime
Target: <path / container / site> (identity, date, revision)

Inventory (component | version | source of version | confidence)
  WordPress core | ... | wp-includes/version.php in checkout | checkout only
  PHP | ... | composer.lock platform / Dockerfile | declared, live unknown
  ...

Ownership map: bootstrap | content model | rendering | API | build | tests | delivery | hosting layer
Hosting and runtime layers: drop-ins, mu-plugins, object cache, platform
Quality tooling: configured | executed (command, exit) | not executed
Environment: topology (single/multisite), environments, deploy path as far as known

Unknowns (with the one observation that resolves each)
Priority candidates (candidate | evidence seen | evidence needed | skill | first check)
Blockers to starting work (access, secrets, staging, build)
Recommended sequence (1..n, each with scope and expected output)
Executed vs not executed checks
```

## Worked example

Signals: a root `acme-commerce.php` with a plugin header; `includes/api/class-webhook-controller.php` registering a route; `.github/workflows/release.yml`; `phpunit.xml.dist`; HPOS declaration via `before_woocommerce_init`; `composer.lock` pinning dependencies; no `tests/` for the webhook.

Good output:

- Shape: custom WooCommerce plugin with REST webhook intake and a tag-driven release workflow. Evidence: static source only; nothing executed.
- Versions: plugin header 3.4.1; `Requires PHP` 7.4; `composer.lock` PHP platform 8.1; WooCommerce version unknown (not in repository); live PHP unknown.
- Priority candidates: (1) webhook route: `permission_callback` is `__return_true`; signature verification not seen in the file read; evidence needed: trace the handler and test the invalid-signature path; skill: `wp-devkit-woocommerce-dev` then `wp-devkit-security-review`. (2) release workflow publishes on tag without a visible verification or rollback step; skill: `wp-devkit-ci-cd-and-release-engineering`. (3) HPOS declared compatible; no test in HPOS mode; skill: `wp-devkit-test-strategy`.
- Unknowns: whether the plugin is active on the live site, live WooCommerce/PHP versions, how built assets are produced.
- Not executed: PHPUnit (configured only), doctor runtime mode.

Bad output (do not do): "CRITICAL: webhook has no signature check" without having read the handler, and "WooCommerce 9 and HPOS enabled" taken from the header text.

## Common first-week outputs

Offer these as follow-up deliverables when the owner wants onboarding, not as part of the read-only pass: a one-page README with run, test and deploy steps; an ownership and escalation table; a list of environment constants and where they are set; a backup and restore drill; a dependency update plan; a minimal CI that runs lint and tests; a risk register fed by the specialist reviews.

## Sources

Reviewed 2026-10-08.

- [Plugin header requirements](https://developer.wordpress.org/plugins/plugin-basics/header-requirements/)
- [PHP supported versions](https://www.php.net/supported-versions.php) and [WordPress release archive](https://wordpress.org/download/releases/) for EOL checks (look up on the day; the compatibility baseline in this pack is dated)
- [WooCommerce HPOS](https://developer.woocommerce.com/docs/features/high-performance-order-storage/)
- Internal: engineering contract severity rules
