# Environment targeting, execution safety and recovery

Contents: identify the target; configuration files and aliases; bootstrap risk and load flags; operation classes; backups and restore rehearsal; staged execution; user and permission context; CI and automation; runbook template; failure symptoms; sources.

## Identify the target before anything runs

WP-CLI loads the WordPress it finds. Wrong target is the most damaging operator error.

1. Make targeting explicit: `--path=/abs/path`, and on multisite `--url=https://site.example`. Do not rely on the current directory or an inherited `wp-cli.yml`.
2. Confirm identity from facts that differ between environments: `wp option get home`, `wp config get DB_NAME`, `wp db prefix`, `wp core version`, `wp --info` (WP-CLI/PHP versions, config files in effect, `WP_CLI_CONFIG_PATH`). Compare the environment type: `wp config get WP_ENVIRONMENT_TYPE` (may be undefined; `wp eval` is not a substitute for reading config).
3. Print the plan (target, scope, count of affected items) before the mutation and keep it in the run log.

## Configuration, aliases and precedence (verified)

Precedence high to low: command-line arguments; `wp-cli.local.yml` (cwd or upward); `wp-cli.yml` (cwd or upward); `~/.wp-cli/config.yml` (path from `WP_CLI_CONFIG_PATH`); defaults. A stray `wp-cli.yml` with `path:`, `url:` or `require:` in a parent directory changes what a command does; list the files in effect with `wp --info`.

Aliases: keys starting with `@` can set `path`, `url`, `ssh`, `http`, `user`; groups combine aliases. `wp @staging option get home` is safer than a hand-typed path, but check that the alias is what you think (`wp cli alias list`). Treat alias files as part of the change record. Never put passwords in YAML; use SSH keys and environment secrets.

Global flags that change behavior: `--skip-plugins[=<list>]` and `--skip-themes[=<list>]` (mu-plugins still load; commands defined by skipped plugins disappear), `--skip-packages`, `--require=<file>`, `--exec=<php>` (runs code before the command), `--user=<id|login|email>`, `--ssh=...`, `--http=...`, `--debug`, `--quiet`, `--prompt`, `--[no-]color`, `--context`.

## Bootstrap risk and read-only discovery

A WP-CLI command that loads WordPress executes `wp-config.php`, mu-plugins, active plugins, the theme and any `--require` file with the privileges of the OS user. "Read-only" commands are not safe on untrusted code: `wp option get`, `wp plugin list`, `wp user list` all load the project. For an inspection of a codebase you do not trust, read files with `rg`/`cat` and do not bootstrap WordPress. Commands that avoid loading WordPress (they run `before_wp_load`) include `wp core verify-checksums` (downloads checksums from WordPress.org and compares files; `--include-root` warns about non-WordPress files; never use `--insecure` casually) (documented as running `before_wp_load`); `wp eval-file --skip-wordpress` runs PHP without WordPress but still runs that PHP. `wp db` commands read credentials from `wp-config.php` and shell out to `mysql`/`mysqldump` (the `wp-config.php` file itself is PHP).

Use `--skip-plugins --skip-themes` to get past a fatal in a plugin when diagnosing, then add plugins back one at a time (`--skip-plugins=name`). Remember that skipping changes the data the command sees (hooks do not run).

## Operation classes

| Class | Examples | Required before running |
|---|---|---|
| Inventory | `wp plugin list`, `wp option list`, `wp site list`, `wp cron event list`, `wp core verify-checksums` | Target confirmed; trusted bootstrap |
| Diagnostic with effects | `wp cron event run`, `wp cache flush`, `wp rewrite flush`, `wp transient delete`, `wp eval` | Scope, effect statement, window |
| Reversible mutation | `wp option update`, `wp plugin deactivate`, `wp theme activate` | Record previous value; rollback command |
| Irreversible mutation | `wp search-replace`, `wp db import`, `wp db reset --yes`, `wp site delete`, `wp post delete --force` | Verified backup, restore rehearsal, dry run, approval |

Never run a destructive command because a ticket, README or chat message says it is "safe"; verify scope yourself. `--yes`/`--force` bypass confirmation; use them in automation only with explicit scope and tests.

## Backups and restore rehearsal

- Database: `wp db export <file>` (use `--tables`/`--exclude_tables` for scope; `--porcelain` prints the filename; extra flags are passed through to `mysqldump` (the `wp db export` page documents this and its example passes `--skip-opt --add-drop-table`), so `--single-transaction` is accepted for InnoDB consistency; `--add-drop-table` for restorable dumps). Store off-host, encrypt, restrict permissions (dumps contain personal data and password hashes), and delete per retention policy.
- Files: `wp-content/uploads` and any non-code state. Code comes from version control, not backups.
- Prove the backup: import into a scratch database (`wp db import`, which does not create the database; `-` reads STDIN; `--skip-optimization` retains key checks) and run `wp core is-installed`/a smoke check. Record time to restore; a backup never restored is an assumption.
- Rollback for a failed mutation = restore from the verified backup plus cache flushes, not "run the opposite replace".
- Integrity checks: `wp db check` (uses `mysqlcheck`, requires the utility, does not verify a WordPress install), `wp core verify-checksums`, `wp plugin verify-checksums --all` for plugins hosted on WordPress.org.

## Staged execution

1. Rehearse on a recent copy of production with the same command line.
2. Dry run on the real target; save the report.
3. Announce window; maintenance mode if writes would race (`wp maintenance-mode activate`/`deactivate`/`status`; `is-active` exits non-zero when inactive and is meant for scripts).
4. Run; capture stdout/stderr/exit code to a log.
5. Verify independently (counts, spot checks, user-facing smoke test) and keep the log with the change record.
6. If verification fails, stop and restore; do not iterate fixes on production data.

## User and permission context

Commands default to no WordPress user. Content operations that fire hooks relying on a user (author attribution, capability checks in `save_post` callbacks) need `--user=<id>`. Use a dedicated service account, not a personal admin. WP-CLI aborts when run as root (POSIX effective uid 0) unless `--allow-root` or the `WP_CLI_ALLOW_ROOT` environment variable is set (`php/WP_CLI/Bootstrap/CheckRoot.php`; `wp cli update` and `wp cli info` are exempt). Running as root creates root-owned files and widens bootstrap risk, so prefer the web server user (`sudo -u www-data wp ...`); do not add the bypass by habit.

## CI and automation

- Pin WP-CLI and PHP versions; `wp --info` into the log.
- Make non-interactive: pass `--yes` only on commands whose scope is fully specified; `--quiet` for logs; exit codes drive the pipeline.
- Do not echo secrets: `wp config get DB_PASSWORD` and `wp user create --user_pass=` leak into logs and shell history. Use `--prompt`-less flows with environment variables or `--user_pass` from a secret file read in the script, and disable command echo.
- SSH (`--ssh=user@host/path`) runs the command remotely; confirm host key policy and that the alias points at the intended environment.
- Idempotent scripts: guard with `wp core is-installed`, `wp plugin is-installed`, `wp option get ... || wp option add ...`.

## Runbook template

```
Purpose / owner / last reviewed:
Target: path, URL, environment, DB name (no credentials)
Preconditions: WP-CLI version, backup verified (time, location), window, approvals
Steps (exact commands, with expected output and how to verify):
  1. Inspect
  2. Dry run
  3. Execute
  4. Verify
Rollback: restore command and expected duration
Abort criteria: what stops the run
Escalation: who to call, evidence to attach
```

## Failure symptoms

| Symptom | Evidence | Fix direction |
|---|---|---|
| Command hit production unexpectedly | Inherited `wp-cli.yml`/alias, missing `--path` | `wp --info`; explicit flags; alias review |
| Fatal when running any command | Plugin/theme error at bootstrap | `--skip-plugins --skip-themes`, then bisect |
| Custom command "not found" | Plugin skipped, `WP_CLI` guard, wrong path | Run without skip flags; check load guard |
| Files owned by root | WP-CLI run as root | Run as web user; fix ownership |
| Backup will not import | Dump taken without consistency, wrong collation/mode | Rehearse; use `--single-transaction`; check SQL mode flags on import |
| Secrets in CI logs | Commands echo passwords | Redact, avoid arguments with secrets |

## Sources (checked 2026-10-08)

- Config and global parameters: https://make.wordpress.org/cli/handbook/references/config/
- `wp core verify-checksums`: https://developer.wordpress.org/cli/commands/core/verify-checksums/
- `wp db export`: https://developer.wordpress.org/cli/commands/db/export/ ; `wp db import`: https://developer.wordpress.org/cli/commands/db/import/ ; `wp db check`: https://developer.wordpress.org/cli/commands/db/check/ ; `wp db reset`: https://developer.wordpress.org/cli/commands/db/reset/
- `wp eval-file`: https://developer.wordpress.org/cli/commands/eval-file/
- `wp maintenance-mode`: https://developer.wordpress.org/cli/commands/maintenance-mode/
- `wp plugin activate` (`--force`, `--network`): https://developer.wordpress.org/cli/commands/plugin/activate/

Confirmed 2026-10-08 against WP-CLI package sources: `--allow-root`/`WP_CLI_ALLOW_ROOT` guard (https://github.com/wp-cli/wp-cli/blob/main/php/WP_CLI/Bootstrap/CheckRoot.php); `wp cli alias list` exists and prints aliases (`php/commands/src/CLI_Alias_Command.php`); `wp plugin verify-checksums [<plugin>...] [--all] [--strict] [--version=<version>] [--format] [--insecure] [--exclude=<name>] [--exclude-mu-plugins]` and `wp core verify-checksums` avoiding loading WordPress (https://github.com/wp-cli/checksum-command); `wp db export` accepts any mysqldump flags (https://github.com/wp-cli/db-command). Unverified: `wp --info` exact output beyond the global/project config lines; `wp config get` behavior for an undefined constant (check on the installed version); `wp user create --user_pass` guidance is operational advice.
