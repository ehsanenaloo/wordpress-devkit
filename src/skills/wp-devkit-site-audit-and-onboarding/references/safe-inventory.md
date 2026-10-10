# Safe inventory commands and version trust

Contents: [Principles](#principles) - [Version trust order](#version-trust-order) - [Passive commands](#passive-commands) - [Commands that execute project code](#commands-that-execute-project-code) - [Commands that contact the network](#commands-that-contact-the-network) - [Commands that change state](#commands-that-change-state) - [Secret and personal data handling](#secret-and-personal-data-handling) - [Asking the owner for evidence](#asking-the-owner-for-evidence) - [Sources](#sources)

## Principles

1. Inventory is observation. Anything that bootstraps WordPress, loads plugin or theme code, runs a project script, contacts an update server or writes is not passive and needs its own authorization and, preferably, a disposable copy.
2. A tool that reports success for a configuration file has not proven the tool works. Record "configured" and "executed" as different facts.
3. Prefer evidence the owner already holds (Site Health info, hosting panel exports, CI logs) over new access.

## Version trust order

When sources disagree, report both and keep this order for the headline value:

1. Runtime evidence from the target (trusted doctor runtime, Site Health info, `wp core version` on the target) with the date it was read.
2. Deployed artifact (the release zip or image actually running).
3. Lockfiles and Composer/npm resolved versions in the repository (resolved for builds, not necessarily production).
4. Plugin and theme headers and `wp-includes/version.php` in the checkout.
5. Declared requirements and compatibility claims (`Requires at least`, `Tested up to`, `engines`, CI matrix).
6. Documentation and README text.

State the source next to every version. A repository checkout of a managed site often does not contain production core or plugins; do not present checkout versions as live versions.

## Passive commands

Safe to run in the project root; they read files only.

```sh
git rev-parse --short HEAD; git status --short | head -20          # revision and local changes (does not modify)
git log -n 10 --format='%h %ad %an %s' --date=short                 # recent history
rg --files -g '!**/{vendor,node_modules}/**' . | head -200          # layout
sed -n '1,40p' composer.json; sed -n '1,60p' package.json            # declared dependencies and scripts (read, do not run)
rg -n '^\$wp_version|^\$required_php_version' wp-includes/version.php # core version without running PHP
jq '.packages[] | {name, version}' composer.lock | head -80          # resolved Composer versions (jq optional)
php --version; node --version; composer --version; docker --version  # tool versions
```

`php --version` and similar read only the tool. Do not run `composer`, `npm`, `yarn` or `make` scripts, `git hooks` or package installs to "see what happens".

## Commands that execute project code

These load WordPress, the active theme and plugins, or project hooks. Run them only on a trusted, disposable copy or with explicit owner authorization.

- `wp ...` in a directory with `wp-cli.yml`/`wp-cli.local.yml`: a `require:` entry loads PHP files before the command runs, and without `--skip-plugins --skip-themes` plugins and the theme load (mu-plugins still load even then). `wp core version` runs before WordPress loads and is the safest first probe; it still reads project WP-CLI configuration.
- `wp plugin list`, `wp theme list`, `wp option get`, `wp eval`, `wp shell`, `wp db query`, `wp cron event list`, `wp site list` all bootstrap WordPress. `wp eval` and `wp shell` execute arbitrary PHP: never run them for inventory.
- `php -r`, `php index.php`, loading `wp-load.php`, and the doctor's `--trusted-runtime` option (it executes WordPress and active plugin bootstrap inside the named container).
- `composer install/update/run-script`, `npm install/ci/run`, `npx`, `make`, pre-commit and git hooks.
- Opening the site in a browser executes its JavaScript and may trigger WP-Cron; acceptable for a staging copy, not a substitute for static reading.

If runtime facts are required, prefer: ask the owner to paste Site Health info (Tools, Site Health, Info, copy to clipboard), which lists WordPress and PHP versions, database, server, constants, drop-ins, must-use plugins and active plugins (the Site Health docs page lists the screen sections and the copy-to-clipboard export; the drop-ins and must-use sections are confirmed as keys `wp-dropins` and `wp-mu-plugins` in `WP_Debug_Data::debug_data()`), then redact before storing.

## Commands that contact the network

`wp plugin list` (it has a `--skip-update-check` option, so update fields imply a network check; the docs do not describe the fields), `wp core check-update`, `wp plugin verify-checksums`, `wp core verify-checksums`, `composer audit`, `npm audit` and `composer outdated` query external services. They are read-only for the project but leak the plugin/package inventory to those services and fail offline. `composer audit --locked` audits the lock file regardless of `vendor/`, and the Composer CLI page says it returns 1 when packages match dependency policies (0 otherwise); how abandoned packages are treated is set by `--abandoned` (ignore, report, fail) and audit config, and the page gives no default, so check your Composer version; treat its output as dependency advisory data, not exploitability. Record the date, because results change daily.

## Commands that change state

Never as part of inventory: `wp cache flush`, `wp transient delete`, `wp cron event run`, `wp plugin update/install/activate`, `wp core update`, `wp db optimize/repair/import`, `wp search-replace` (even with `--dry-run` on a live database it can load a lot), `wp rewrite flush`, `wp user create`, Docker `exec` commands that write, deployment scripts. If the task needs one, stop and obtain a separate scoped instruction with backup and rollback.

## Secret and personal data handling

- Read configuration by name and presence. `rg -l` or `--count` is enough to show that `DB_PASSWORD` exists. Never echo values from `wp-config.php`, `.env*`, `auth.json`, `*.pem`, Docker env, CI secrets or database dumps.
- Treat `wp-config.php` backups (`wp-config.php.bak`, `.orig`, `~`), database dumps (`*.sql`, `*.sql.gz`) and `.git` exposure in a web root as findings to hand to security, without opening their contents.
- Database content (users, orders, form entries) is personal data. Count and describe schema, do not display rows. Redact emails, IPs and tokens in any pasted logs.
- Keep generated reports outside the inspected tree and review them before sharing: hostnames, paths and plugin lists are sensitive in some organizations.

## Asking the owner for evidence

When access is limited, request: the Site Health info export; the hosting provider and plan type; the deploy process and who can deploy; the last known good backup and when a restore was tested; whether a staging copy exists; CI links; whether auto-updates are on; the list of third-party services (payments, search, CDN, email). Record the answers as owner-stated, not verified.

## Sources

Reviewed 2026-10-08.

- [WP-CLI configuration (require, skip-plugins, skip-themes; mu-plugins still load)](https://make.wordpress.org/cli/handbook/references/config/)
- [wp core version](https://developer.wordpress.org/cli/commands/core/version/) (runs before WordPress loads)
- [Composer audit](https://getcomposer.org/doc/03-cli.md#audit)
- [wp_using_ext_object_cache](https://developer.wordpress.org/reference/functions/wp_using_ext_object_cache/)
- [Plugin list command](https://developer.wordpress.org/cli/commands/plugin/list/)
