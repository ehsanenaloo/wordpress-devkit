# Platform upgrades, rollback and recovery

Researched 2026-10-08. Contents: 1 What an upgrade plan must contain | 2 WordPress core and plugin updates | 3 PHP upgrades | 4 Database engine upgrades | 5 Auto-update behavior | 6 Backup, restore and rollback | 7 Downgrade and uninstall | 8 Review checks

## 1. What an upgrade plan must contain

Source and target versions (WordPress, PHP, MySQL/MariaDB, WooCommerce, the plugin under review), supported range, the order of changes, the data steps, verification queries, the maintenance window or zero-downtime approach, rollback triggers and owner, and the communications. Discover the real versions (`wp core version`, `wp --info`, `wp plugin list --format=json`, `SELECT VERSION()`) on the environment; do not read them from marketing pages. Treat unsupported starting versions as untested.

Reference baseline (the versions DevKit was tested against; re-verify before use): WordPress requires PHP 7.4+ and MySQL 5.7+/MariaDB 10.3+ as a floor per the advanced administration requirements page, while the WordPress.org requirements page lists PHP 8.3+ and MySQL 8.0+/MariaDB 10.11+ as recommended and PHP 7.4/MySQL 5.5.5 as legacy minimums. These sources differ on the database floor; use the target project's declared "Requires" headers and the hosting policy, and report the discrepancy rather than choosing silently.

## 2. WordPress core and plugin updates

- Read the release notes, field guide and dev notes for the target version (make.wordpress.org/core) for deprecations and removals; run the project's test suite and static analysis against the new core on a copy.
- Run `wp core update-db` (or the network upgrade screen) after a core update when required; on multisite use `wp core update-db --network`. `--dry-run` reports whether an update is pending.
- Plugin updates replace files first and run the plugin's upgrade routine later, on the next request that loads the new code. During the window, requests can hit new code with an old schema (and old, still-resident code during the update request itself). Upgrade routines must be safe against being triggered by several simultaneous requests.
- `upgrader_process_complete` for a plugin updating itself runs with the old code and does not fire for manual replacement, so do not hang the data migration on it.
- Require headers: keep `Requires at least`, `Requires PHP` and `Requires Plugins` accurate; WordPress blocks activation when `Requires at least`/`Requires PHP` are unmet, and since 6.5 a plugin whose `Requires Plugins` dependencies are inactive cannot be activated until they are (the 6.5 dev note does not address multisite behavior: test it).
- Test the update path from every supported previous plugin version, not only the immediately previous one (an upgrade routine that assumes N-1 breaks a site updating from N-3). Store step functions per version and run all that are newer than the stored version, in order.

## 3. PHP upgrades

Check compatibility statically and at runtime on the target PHP:
- `phpcs -p . --standard=PHPCompatibilityWP --runtime-set testVersion 8.3-` (PHPCompatibilityWP via Composer; the `testVersion` range sets the PHP versions supported; without it only deprecation notices appear). Heuristic, not proof; confirm project maintenance status before relying on it for a new PHP minor.
- PHPStan with `phpVersion` set to the target (or a min/max range in PHPStan 2.x) to surface API changes.
- Run the full test suite on the target PHP in CI; watch for deprecations in logs (`error_reporting( E_ALL )` in staging).
- Typical breakage by version: 8.2 deprecates dynamic properties (use declared properties, `#[\AllowDynamicProperties]` for legacy classes, or `WeakMap`), `${var}` interpolation, `utf8_encode()`/`utf8_decode()`, and relative callables such as `'self::method'`; 8.4 deprecates implicitly nullable parameters (`Type $x = null`; write `?Type $x = null`) and `E_USER_ERROR` via `trigger_error()`; 8.5 deprecates non-canonical casts (`(boolean)`, `(integer)`, `(double)`), the backtick operator, `__sleep()`/`__wakeup()` in favor of `__serialize()`/`__unserialize()`, `null` as an array offset, and several Reflection and extension functions (`curl_close()`, `imagedestroy()`, `xml_parser_free()`). Fix deprecations in your code; vendor libraries may need upgrades.
- Extensions and settings differ per host: `mbstring`, `intl`, `gd` with WebP/AVIF, `imagick`, `sodium`, OPcache settings; verify on the target with `php -m` and `phpinfo()` in staging.
- Support windows: use php.net supported versions for end-of-support dates (the repository baseline records them); moving a production site off an unsupported PHP is itself a risk item.

## 4. Database engine upgrades

Moving between MySQL and MariaDB or major versions changes collations, `sql_mode`, reserved words, JSON and generated-column behavior, and optimizer plans. Test the schema creation and key queries on the target engine, check `sql_mode` strictness (`STRICT_TRANS_TABLES`, `NO_ZERO_DATE`), collation compatibility (mixed-collation joins), and index lengths. Take a logical dump (`wp db export`) before and verify import on the target (`wp db import` or the native client) before cutover.

## 5. Auto-update behavior

- Core minor/security releases auto-update by default; plugin and theme auto-updates are per-item opt-in. Auto-updates run unattended, so an unsafe upgrade routine will run without anyone watching.
- WordPress 6.6 added automatic rollback for plugin auto-updates: after the update, a loopback request to the front end checks for a fatal error; if one is found the previous plugin version is restored and the administrator is emailed. It covers fatal PHP errors on the front end of plugin auto-updates only. It does not reverse database changes, does not cover theme updates, does not detect non-fatal breakage (wrong data, admin-only errors, REST failures), and, and may not catch failures in an upgrade routine that runs later, for example on the next admin load. Do not claim an upgrade is "safe because auto-update rolls back".
- Provide a kill switch or compatibility check for risky data migrations: the data step should run in a controlled runner, not as a side effect of the first request after an unattended update.

## 6. Backup, restore and rollback

- A backup is real only after a restore into an isolated environment: record the time it took, what was verified (row counts, uploads, configuration, a login, a representative transaction), and the retention. Back up the database and the files that are not reproducible (uploads, `wp-config.php` salts, custom configuration), plus the object-storage state when uploads are offloaded.
- Take a point-in-time snapshot immediately before a destructive step. Database dumps: `wp db export before-migration.sql` (compress; keep outside the web root; treat as sensitive data).
- Rollback has three separate parts: code (redeploy previous artifact), data (restore or reverse migration) and state (caches, queued jobs, scheduled events, search index). Restoring old code does not undo migrated data, and restoring data loses writes made after the snapshot (orders, comments, form entries): quantify that loss and decide a cut-over freeze or replay plan.
- Prefer forward-compatible additive states so rollback is code-only until the contract release; then define a data rollback (inverse migration with its own tests or restore).
- Decision points: rollback triggers (error rate, failed verification, queue not draining), owner, and the point of no return (after the contract step). Document them before the release.

## 7. Downgrade and uninstall

Downgrading a plugin to a version older than the stored schema version should be detected (stored version greater than code version): refuse destructive actions and show a notice instead of "fixing" data. Deactivation must not delete data; uninstall (deleting the plugin) is the permanent cleanup and should honor a "keep data" setting; on multisite iterate sites in batches or leave per-site data with a documented cleanup command. Never delete shared tables used by other plugins.

## 8. Review checks

1. Plan lists versions, order, verification, rollback triggers and owner.
2. Update path tested from each supported previous version; unattended auto-update case considered.
3. PHP compatibility checked on the target version with tests, not only static tools.
4. Backup restored once in isolation with recorded time; data-rollback plan exists for destructive steps.
5. Rollback statements distinguish code, data and state.
6. A pass does not prove production hosting parity (PHP extensions, DB settings, CDN, object cache behavior).

Sources: [WordPress requirements](https://wordpress.org/about/requirements/) | [Before you install (server requirements)](https://developer.wordpress.org/advanced-administration/before-install/) | [wp core update-db](https://developer.wordpress.org/cli/commands/core/update-db/) | [PHPCompatibilityWP](https://github.com/PHPCompatibility/PHPCompatibilityWP) | [PHP 8.2 deprecations](https://www.php.net/manual/en/migration82.deprecated.php) | [PHP 8.4 deprecations](https://www.php.net/manual/en/migration84.deprecated.php) | [PHP 8.5 deprecations](https://www.php.net/manual/en/migration85.deprecated.php) | [Auto-update rollback (Trac changeset 58128)](https://core.trac.wordpress.org/changeset/58128) | [Merge proposal: Rollback Auto-Update](https://make.wordpress.org/core/2024/04/19/merge-proposal-rollback-auto-update/) | [PHP supported versions](https://www.php.net/supported-versions.php). | [Plugin dependencies 6.5](https://make.wordpress.org/core/2024/03/05/introducing-plugin-dependencies-in-wordpress-6-5/) | [core class-wp-automatic-updater.php](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-admin/includes/class-wp-automatic-updater.php)
