# Plugin lifecycle, upgrades and multisite provisioning

Contents: loading modes; headers; activation; deactivation; uninstall; versioned upgrades; dbDelta; dependencies; multisite; failure symptoms; sources.

## Loading modes

| Mode | Activation/deactivation hooks | Notes |
|---|---|---|
| Regular plugin in `wp-content/plugins` | Yes | Loaded after `muplugins_loaded`, before `plugins_loaded`. |
| Network-activated (multisite) | Run once with `$network_wide = true`, not per site | Header `Network: true` forces network-only activation. |
| Must-use (`mu-plugins`) | None | Always on. Needs its own setup path (version check at runtime). Subdirectory files load only through a loader file. |
| Drop-in (`object-cache.php`, `advanced-cache.php`, `db.php`, `sunrise.php`) | None | Loaded by core by file name, before most of WordPress. Cannot assume functions exist. |

Decide the mode first; most "activation did not run" reports are must-use or update cases.

## Headers (verified against the plugin handbook)

- Only `Plugin Name` is required. `Version` is compared with PHP `version_compare()`, so `1.02` is greater than `1.1`; use semantic versions.
- `Requires at least` and `Requires PHP` declare the support floor. Core refuses activation when the site does not meet them: `validate_plugin_requirements()` is documented `@since 5.2.0` and `activate_plugin()` calls it (core source). Sites older than that release ignore the headers, so confirm on the lowest WordPress you support.
- `Requires Plugins` (WordPress 6.5): comma-separated WordPress.org slugs only (no file paths, no commas in slugs). No version constraints, no load-order guarantee, must-use dependencies unsupported. Keep runtime `class_exists`/`function_exists` guards and a version check for the dependency API you use. The `wp_plugin_dependencies_slug` filter maps a slug (for example free to pro).
- `Update URI` (5.8): set to your own host for non-directory plugins so a same-named directory plugin cannot overwrite yours.
- `Network: true` only when the plugin must be network-activated; omit otherwise.
- `Text Domain` must equal the slug used in every `__()` call; `Domain Path` locates bundled `.mo/.po` files.

## Activation

```php
register_activation_hook( __FILE__, 'acme_activate' );

function acme_activate( $network_wide ) {
	// Idempotent. Runs once per activation, never on update.
	acme_register_post_types();          // register before flushing rules.
	add_option( 'acme_db_version', '0' ); // add_option never overwrites.
	flush_rewrite_rules();               // only because rules changed.
	if ( ! wp_next_scheduled( 'acme_daily' ) ) {
		wp_schedule_event( time() + HOUR_IN_SECONDS, 'daily', 'acme_daily' );
	}
}
```

Rules:
- Call `register_activation_hook` at file load of the main plugin file, not inside another hook that fires after activation. The path argument must be the main file (`__FILE__`) or the callback is never matched.
- Activation is not an upgrade mechanism. A plugin updated through the dashboard, WP-CLI, Composer, FTP or Git never reruns it.
- Do not run per-site work for every site inside an activation request on a large network (timeouts); defer to a queue or WP-CLI (see multisite).
- Never print output (`echo`, whitespace before `<?php`, notices). Core reports "generated N characters of unexpected output during activation"; it points to a stray BOM or echo, not to a failed callback.
- Do not redirect during activation without guarding: bulk activation, network activation and WP-CLI must not redirect. Store a short-lived transient flag and redirect once from `admin_init` for a single-site interactive activation only.
- Flush rewrite rules on activation and deactivation only after the post type or rewrite registration is loaded in that request. Flushing on every `init` rebuilds the `rewrite_rules` option on each request and is a performance defect, not a fix for 404s.

## Deactivation

Clear plugin-owned resources only: `wp_clear_scheduled_hook( 'acme_daily' )` (arguments must match the scheduled event), unschedule queue actions, remove rewrite rules (`flush_rewrite_rules()` after the type is unregistered or simply flush). Never delete user content or settings on deactivation: deactivation is routinely used for troubleshooting.

## Uninstall

Two mechanisms (verified): `uninstall.php` in the plugin root, or `register_uninstall_hook( __FILE__, 'callback' )`. Use one. `uninstall.php` must begin with a check of `WP_UNINSTALL_PLUGIN`; that constant is not defined when the hook callback is used.

```php
<?php
// uninstall.php
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}
if ( 'yes' !== get_option( 'acme_delete_data_on_uninstall' ) ) {
	return; // retention is the default policy.
}
delete_option( 'acme_settings' );
delete_option( 'acme_db_version' );
global $wpdb;
$wpdb->query( "DROP TABLE IF EXISTS {$wpdb->prefix}acme_events" ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery,WordPress.DB.PreparedSQL.InterpolatedNotPrepared -- table name is built from $wpdb->prefix and a literal.
```

Decisions:
- Retention is a product policy. Default to keeping user content (posts, uploaded files, orders). Offer an explicit opt-in setting for data removal; document it in the readme.
- Plugin code is not loaded during `uninstall.php`; do not call your classes or autoloader unless you require them explicitly.
- Multisite: `delete_site_option()` for network options; per-site options and tables need iteration with `get_sites( array( 'fields' => 'ids', 'number' => 100, 'offset' => $n ) )` in batches and `switch_to_blog()`/`restore_current_blog()` in `try/finally`. Looping every site inside one request is expensive; document a WP-CLI cleanup for large networks.
- Uninstall runs only when the plugin is deleted through WordPress. Removing the directory by hand skips it.

## Versioned upgrades

Pattern: persist an installed-version marker, compare on a cheap hook, run ordered idempotent steps, advance the marker only after each step succeeds.

```php
add_action( 'plugins_loaded', 'acme_maybe_upgrade', 5 );

function acme_maybe_upgrade() {
	$installed = get_option( 'acme_db_version', '0' );
	if ( version_compare( $installed, ACME_DB_VERSION, '>=' ) ) {
		return;
	}
	// Single-runner lock: add_option fails if the row already exists.
	if ( ! add_option( 'acme_upgrade_lock', time(), '', false ) ) {
		$started = (int) get_option( 'acme_upgrade_lock' );
		if ( time() - $started < 15 * MINUTE_IN_SECONDS ) {
			return;
		}
		update_option( 'acme_upgrade_lock', time(), false );
	}
	$steps = array(
		'1.1.0' => 'acme_upgrade_1_1_0',
		'1.3.0' => 'acme_upgrade_1_3_0',
	);
	foreach ( $steps as $version => $callback ) {
		if ( version_compare( $installed, $version, '<' ) ) {
			if ( true !== call_user_func( $callback ) ) {
				break;                     // leave the marker so the step retries.
			}
			update_option( 'acme_db_version', $version, true );
			$installed = $version;
		}
	}
	delete_option( 'acme_upgrade_lock' );
}
```

Points that matter:
- `upgrader_process_complete` is not a safe trigger: it fires only for updates that go through WordPress's upgrader (not manual file replacement or deployment), and when your own plugin is the one being updated the hook runs the old version of your code already in memory (per the hook reference). Use a runtime comparison.
- Steps must be idempotent (`IF NOT EXISTS`-style checks, `add_option`, guarded `ALTER`). A partial failure must be retryable.
- Long data migrations (millions of rows) never run in a web request. Enqueue batches (Action Scheduler or WP-Cron with a cursor) or expose a WP-CLI command, and keep the plugin functional with old and new data layouts until the migration reports complete.
- On multisite, store the version per site (`get_option`) when the schema is per site, and network-wide (`get_site_option`) when it is shared. A site created after an upgrade must be provisioned by the current code, not by replaying history.
- Test the matrix: fresh install, upgrade from oldest supported marker, upgrade from the previous release, repeated run (no change), and failure injected mid-step.

## dbDelta rules (verified against the function reference)

- Handles `CREATE TABLE` and similar; each field and index on its own line; no blank lines inside the statement; `PRIMARY KEY (id)` for the primary key; secondary indexes use `KEY name (col)` with a name.
- Unsupported: `FOREIGN KEY`, `IF NOT EXISTS`, `COMMENT` clauses, dropping tables, renaming columns (the new column is added; the old remains). Drop with `$wpdb->query( 'DROP TABLE ...' )` after verification.
- Use lowercase column types, `$wpdb->get_charset_collate()` and `$wpdb->prefix` (per site) or `$wpdb->base_prefix` (network table).
- The returned messages can claim success without it; confirm with `SHOW CREATE TABLE` or `$wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $wpdb->esc_like( $table ) ) )`.
- Require `wp-admin/includes/upgrade.php` before calling `dbDelta()` outside admin.
- Index changes on a large table lock or rebuild it. Plan a maintenance window or an online-schema-change approach instead of relying on a request-time `dbDelta`.

## Multisite provisioning

- Network activation does not run activation code on each existing site. Per-site tables and options must be created by a loop (batched), by lazy creation on first use, or by the versioned upgrade routine (preferred: self-healing).
- New sites: hook `wp_initialize_site` (since 5.1; `$new_site` is a `WP_Site`) and create per-site data if the plugin is network-active. Do not use `switch_to_blog()` loops on every request.
- `is_plugin_active_for_network( plugin_basename( __FILE__ ) )` distinguishes network from per-site activation; `is_multisite()` alone does not.
- Wrap `switch_to_blog()` in `try { ... } finally { restore_current_blog(); }`; failing to restore corrupts later queries in the request.

## Failure symptoms and confirmation

| Symptom | Likely cause | Confirm |
|---|---|---|
| New table missing after update | Table created only on activation | Dashboard update path never calls activation; check marker and `SHOW TABLES`. |
| Activation succeeds, feature missing | Callback added after its action already fired (for example registering an `init` callback from inside `init` at the same or later priority) | `did_action`, `doing_action`, trace. |
| "Unexpected output during activation" | Echo, notice or BOM at load time | `wp plugin activate` with `WP_DEBUG_LOG`, view `debug.log`. |
| Duplicate cron events | `wp_schedule_event` without `wp_next_scheduled` | `wp cron event list --fields=hook,next_run_gmt`. |
| 404 on new post type URLs | Rules not flushed once after registration change | Flush once on activation/upgrade, test old and new permalinks and pagination. |
| Uninstall left data / removed too much | Wrong mechanism or no retention policy | Read uninstall path; test in disposable site. |

## Sources

Research date: 2026-10-08.

- Plugin header requirements: https://developer.wordpress.org/plugins/plugin-basics/header-requirements/
- Uninstall methods: https://developer.wordpress.org/plugins/plugin-basics/uninstall-methods/
- Plugin dependencies 6.5: https://make.wordpress.org/core/2024/03/05/introducing-plugin-dependencies-in-wordpress-6-5/
- `upgrader_process_complete`: https://developer.wordpress.org/reference/hooks/upgrader_process_complete/
- Core `validate_plugin_requirements()`: https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-admin/includes/plugin.php
- dbDelta: https://developer.wordpress.org/reference/functions/dbdelta/
- `wp_initialize_site`: https://developer.wordpress.org/reference/hooks/wp_initialize_site/
