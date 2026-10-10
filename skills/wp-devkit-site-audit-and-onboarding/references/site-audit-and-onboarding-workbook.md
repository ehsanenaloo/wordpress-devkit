# Site audit and onboarding workbook

Contents: [Decision rules](#decision-rules) - [Looks wrong but is fine](#looks-wrong-but-is-fine) - [Looks fine but is wrong](#looks-fine-but-is-wrong) - [Severity and candidates](#severity-and-candidates) - [Finding template](#finding-template) - [Symptom to cause](#symptom-to-cause) - [Enterprise concerns](#enterprise-concerns) - [Acceptance checks](#acceptance-checks) - [Sources](#sources)

Apply [the engineering contract](engineering-contract.md) first. Detail files: [stack signals](stack-signals-and-ownership.md), [safe inventory](safe-inventory.md), [routing and deliverable](routing-and-deliverable.md), [doctor](doctor.md).

## Decision rules

| Question | Rule |
| --- | --- |
| How far may I go? | Static reading by default. Anything that loads WordPress, runs a project script, contacts an update service or writes needs its own authorization (safe-inventory.md). |
| Which version is "the" version? | The most trustworthy source available, named: runtime over deployed artifact over lockfile over header over documentation. Report disagreement instead of picking silently. |
| Present or active? | Present in a directory is not active; active is not working. Activation needs runtime or database evidence. |
| Configured or executed? | A config file for PHPUnit, PHPStan, Playwright or CI proves intent. Executed needs a command, exit status and date. |
| Whose code is it? | First-party, vendored, generated, third-party copied in, platform/host. Only first-party source is a normal edit target; others are reported. |
| Is this a defect? | Inventory raises candidates. Severity needs a reachable path and impact traced by a specialist. |
| When to stop? | When the next step needs execution, credentials, or a decision the owner has not given. Report the unknown and the exact request. |
| When not to run this skill? | When the user already names the problem domain (a checkout bug, a slow query, a block validation error): go to the domain skill and take only the facts you need. |

## Looks wrong but is fine

- `eval`, `base64_decode`, `unserialize` or `shell_exec` in vendored libraries, build tooling or WordPress core copies: not first-party; at most note the dependency version.
- Minified or built JavaScript and CSS committed under `build/` or `dist/`: generated; find the source and the build step.
- Multiple plugin copies (zip backups) in a repo: dead weight, but verify none is the one deployed before calling it dead.
- `WP_ALLOW_MULTISITE` defined without `MULTISITE`: network not active.
- `WP_DEBUG` true in a local or staging config file that production overrides via environment: check the environment type before raising it.
- Missing `wp-config.php` in the repository: usually deliberate (Bedrock `.env`, host-managed). Do not conclude the project is incomplete.
- No tests directory in a theme or small plugin: informational; not a critical gap on its own.
- A CMS plugin with obfuscated license-check code: a vendor concern; note vendor and version.
- A parent theme inside `themes/` with no custom code: the child theme is the first-party boundary.
- Public REST routes that return public content.

## Looks fine but is wrong

- Plugin header says `Tested up to: 6.9`: that is the author's claim, not the installed or live WordPress version.
- `composer.lock` shows WooCommerce 10.x: that is what the build installs, not necessarily production.
- A CI workflow named `test.yml`: it may not run tests, may run on a different branch, or may be disabled. Read it.
- `phpstan.neon` exists with `level: 0` and a huge baseline: configured, but weak assurance.
- Staging `.env.example` values look like production hostnames: do not contact them.
- `DISALLOW_FILE_MODS` true: updates are managed elsewhere, so plugin update status in the dashboard is hidden; inventory outdated plugins from lockfiles or a runtime export.
- An `object-cache.php` drop-in present while the backing service is down: the site is silently falling back or erroring.
- `readme.txt` `Stable tag` differing from the plugin header version: a release process defect candidate.

## Severity and candidates

Per the contract, severity follows demonstrated impact. At onboarding almost everything is a candidate:

- Confirmed CRITICAL examples (need evidence in hand and a reachable path): a committed live credential for a reachable service, a database dump or `wp-config.php` backup inside a directory that is served publicly.
- WARNING: supported correctness, security, compatibility or performance concern shown from source or config (permissive `permission_callback`, debug display enabled in a production-typed configuration, unsupported PHP declared, no rollback path for a destructive upgrade).
- INFO: hygiene and structure.
- Candidate: any item needing a specialist trace. Put it in the priority list with the evidence required; do not label it CRITICAL.

## Finding template

```text
[candidate|confirmed] [INFO|WARNING|CRITICAL] path:line or config key
Signal: what was seen (name only for secrets)
Not verified: what is missing (activation, reachability, live value)
Why it matters: impact if real
Next: specialist skill and first check
```

## Symptom to cause

| Symptom | Evidence to gather | Reading |
| --- | --- | --- |
| Cannot find the active theme code | `Template:` header, `stylesheet`/`template` options (runtime or owner), Site Editor customizations in database | Parent/child or database-stored templates; ask for runtime evidence |
| Plugin directory present but behavior absent | Activation state, mu-plugin overrides, `Requires Plugins`, network activation | Not active or overridden |
| Versions differ between local and live | Which source produced each; build artifact | Report both; investigate the deployment owner |
| Slow/odd site and no code changes | Drop-ins (`object-cache.php`, `advanced-cache.php`, `db.php`), host mu-plugins | Hosting layer behavior not in the repository |
| Doctor shows tool failed | Exit code, PATH, Windows Store alias | Environmental; check before blaming the project |
| Doctor runtime failed | Container state, root path, database connectivity | Collector failed closed; use manual fallback on a disposable copy |
| Unexpected writes during inventory | Which command executed, `wp-cli.yml`, hooks | A non-passive command was run; stop and record |
| Multisite classification conflicts | `MULTISITE` versus `WP_ALLOW_MULTISITE` | Only `MULTISITE` true (plus network constants) means active |

## Enterprise concerns

Check during inventory, then route:

- Environments and promotion path (local, CI, staging, production), parity, who deploys, rollback and backup restore evidence.
- Multisite or multi-tenant topology, domain mapping, per-site differences.
- Large data: custom tables, order volume, postmeta size, autoloaded options, media library size; flag for performance and migration review.
- Object cache and page cache layers, CDN, WAF, and their invalidation owners.
- Background processing: WP-Cron versus system cron (`DISABLE_WP_CRON`), Action Scheduler, queues.
- Compliance and privacy: personal data stores, consent tooling, retention, exporter/eraser support, processors (payments, email, analytics).
- Observability: error logging destination, uptime and performance monitoring, who gets alerts.
- Supply chain: dependency sources, abandoned plugins, premium plugin license ownership, update policy and auto-updates.
- Backward compatibility: public hooks and APIs other code depends on, supported WordPress/PHP range, builder lock-in.
- Access: who holds hosting, DNS, Git, CI, payment and email credentials; bus factor.

## Acceptance checks

- The deliverable names the target identity, evidence level and date, and every version carries its source.
- Static, database and runtime evidence are labeled separately; unknowns each list the resolving observation.
- No candidate is labeled CRITICAL without a traced path; no secret value appears anywhere.
- Follow-ups are at most a handful, each with a skill, scope and first check.
- Only passive commands ran unless the owner authorized more; every command is listed with its exit status; doctor output (if any) is stored outside the source tree.

A complete inventory proves what was observed from the sources listed. It does not prove security, performance, accessibility, compatibility, backup health or that the repository matches production.

## Sources

Reviewed 2026-10-08.

- [Create a network (WP_ALLOW_MULTISITE)](https://developer.wordpress.org/advanced-administration/multisite/create-network/)
- [Drop-ins](https://developer.wordpress.org/reference/functions/_get_dropins/)
- [wp_get_environment_type](https://developer.wordpress.org/reference/functions/wp_get_environment_type/)
- [Plugin header requirements](https://developer.wordpress.org/plugins/plugin-basics/header-requirements/)
- [WP-CLI configuration](https://make.wordpress.org/cli/handbook/references/config/)
- [WordPress debugging](https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/)
