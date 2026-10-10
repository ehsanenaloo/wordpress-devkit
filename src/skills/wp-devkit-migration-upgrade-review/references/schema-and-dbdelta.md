# Schema changes, dbDelta and online DDL

Research date: 2026-10-08. Contents: 1 dbDelta contract | 2 Safe table definition | 3 Version gate | 4 What dbDelta cannot do | 5 Cost of DDL on large tables | 6 Charset and collation | 7 Expand and contract | 8 Review checks

## 1. dbDelta contract

`dbDelta( $sql, $execute = true )` (in `wp-admin/includes/upgrade.php`, which must be required first) takes one or more `CREATE TABLE` statements, compares them to the existing table and runs the statements needed to create the table, add missing columns and add missing indexes. It returns an array of messages describing changes (and with `$execute = false` returns the list without running queries). Its parser is strict; known rules from the handbook and function reference:

- Put each column definition on its own line.
- Write `PRIMARY KEY` followed by two spaces and the column list in parentheses. Use `KEY` (core normalizes `INDEX` to `KEY`) with the index name and the column list in parentheses.
- Give lengths for types that take them; lowercase type names are the documented convention.
- Do not use backticks around names, `IF NOT EXISTS`, `FOREIGN KEY` constraints, or `COMMENT` clauses (reported not to be handled; treat as unsupported).
- Avoid blank lines inside the statement.
- Verify the result by reading the real schema (`SHOW CREATE TABLE`, `wp db query`); the returned messages can claim creation that did not happen.

## 2. Safe table definition

```php
global $wpdb;
require_once ABSPATH . 'wp-admin/includes/upgrade.php';

$table   = $wpdb->prefix . 'acme_events';
$charset = $wpdb->get_charset_collate();

$sql = "CREATE TABLE {$table} (
  id bigint(20) unsigned NOT NULL auto_increment,
  blog_id bigint(20) unsigned NOT NULL default 0,
  event_key varchar(100) NOT NULL,
  payload longtext NULL,
  created_at datetime NOT NULL default '0000-00-00 00:00:00',
  PRIMARY KEY  (id),
  UNIQUE KEY event_key (blog_id,event_key),
  KEY created_at (created_at)
) {$charset};";

dbDelta( $sql );
```

Notes: `$wpdb->prefix` is per site on multisite; use `$wpdb->base_prefix` for network-wide tables. Zero-date defaults are rejected by strict `sql_mode` (`NO_ZERO_DATE`); core's own connection removes `NO_ZERO_DATE`, `STRICT_TRANS_TABLES` and `STRICT_ALL_TABLES` from the session mode (`wpdb::$incompatible_modes`) and its own schema uses zero dates, so `$wpdb` queries and `dbDelta` usually work, but separate connections (CLI SQL, imports, replicas, external tools) in strict mode reject them. Prefer `NULL` or `CURRENT_TIMESTAMP` where the supported MySQL/MariaDB versions allow and test on the strictest supported mode. Unique indexes on `varchar` columns under the older `utf8mb4` row formats are limited to 191 characters per column prefix.

## 3. Version gate

Store the schema version as an option and compare on a hook that runs after every update:

```php
add_action( 'plugins_loaded', 'acme_maybe_upgrade_schema' );

function acme_maybe_upgrade_schema() {
	$installed = get_option( 'acme_db_version', '0' );
	if ( version_compare( $installed, ACME_DB_VERSION, '>=' ) ) {
		return;
	}
	acme_install_schema();                       // idempotent dbDelta
	acme_run_data_steps( $installed );          // versioned steps, each idempotent
	update_option( 'acme_db_version', ACME_DB_VERSION, false );
}
```

- `register_activation_hook` runs on activation only, not on updates; `upgrader_process_complete` runs in the old code for a plugin that updates itself and does not fire for manual file replacement, FTP/Git deploys or some auto-update paths. A stored-version comparison is the reliable trigger.
- Do the work under a lock when more than one request can arrive during the update (see the backfill reference); an unlocked `dbDelta` race is usually harmless but data steps are not.
- Autoload the version option (it is read every request) but keep it small; pass `false` for autoload of large state options.
- On multisite, `plugins_loaded` runs per request for the current site; per-site table prefixes need per-site version markers (see the multisite reference).
- Heavy upgrades do not belong on `plugins_loaded` of front-end requests: schedule a runner (WP-CLI or Action Scheduler) and show an admin notice or keep old behavior until completion.

## 4. What dbDelta cannot do

It does not drop columns or tables, rename columns (a changed name adds a new column and leaves the old), change data in place, convert storage engines, remove indexes, or reorder safely. Destructive and data-changing steps require explicit statements, run in a separate contract release after verification. Changing an existing index definition under the same name is not a documented dbDelta capability: inspect the resulting indexes and handle the change with an explicit, reviewed statement.

## 5. Cost of DDL on large tables

- In MySQL and MariaDB, `ALTER TABLE`, `CREATE TABLE`, `DROP TABLE`, `CREATE INDEX` and similar statements commit implicitly and cannot be undone by `ROLLBACK`. A transaction around DDL protects nothing.
- InnoDB online DDL (MySQL 8.0 documentation): adding a secondary index is done in place and permits concurrent DML; adding a column can be `INSTANT` (8.0.12+) or in place; dropping a column rebuilds the table unless `INSTANT` is available (8.0.29+); changing a column data type requires `ALGORITHM=COPY` and blocks concurrent writes. Request the algorithm and lock explicitly so the statement fails instead of silently choosing a blocking method: `ALTER TABLE t ADD INDEX i (c), ALGORITHM=INPLACE, LOCK=NONE;`. MariaDB's online DDL differs in versions and syntax: check the target version's documentation.
- Metadata locks: a long-running transaction or query holding a table blocks the `ALTER`, and the waiting `ALTER` then blocks new queries behind it, causing an outage. Run during low traffic, set `lock_wait_timeout`, and check for long transactions first.
- On very large tables use an online schema change tool (gh-ost, pt-online-schema-change) or run the change outside the web path; managed hosts may restrict these.
- `wp_postmeta`, `wp_options`, `wp_posts` are core tables: adding indexes or columns to them is rarely safe or supported (core upgrades and other plugins assume the schema). Prefer a custom table.
- Replicas and managed platforms: replication lag and DDL on replicas; schema changes on platforms with deploy hooks.

## 6. Charset and collation

Use `$wpdb->get_charset_collate()` for new tables; core's `utf8mb4` default collation depends on the database version (`wpdb::determine_charset()` maps `utf8mb4_unicode_ci` to `utf8mb4_unicode_520_ci` when the server supports it); joins between tables with different collations fail with "Illegal mix of collations" or force index loss. When altering collations, convert tables deliberately (`ALTER TABLE ... CONVERT TO CHARACTER SET`) on a copy and time it; check index key length limits after conversion.

## 7. Expand and contract

Expand: add nullable columns or new tables with defaults, new options with fallbacks. Old code must keep working with the expanded schema (ignore unknown columns; `SELECT *` consumers tolerate extra columns; INSERTs from old code supply defaults).
Backfill: separate step.
Contract: drop old columns/options in a later release after the retention window and after verifying no reader remains; keep a backup of the dropped data. Never rename in place when two code versions run at once; add new, copy, switch, remove old.

## 8. Review checks

1. `CREATE TABLE` text follows the dbDelta rules; real schema inspected afterwards, including indexes and collation.
2. Version gate runs on updates and is recorded after success.
3. No destructive DDL in the same release as the switch; no DDL assumed transactional.
4. DDL cost estimated for the largest supported table with a stated algorithm and lock; plan for metadata-lock waits.
5. Multisite prefix and network-table choice are correct.
6. Regression: fresh install, upgrade from each previous schema version, repeated `dbDelta` (no changes reported on the second run), strict `sql_mode`.
7. A pass does not prove: production-size lock time, replica behavior, or compatibility with other plugins reading the same tables.

Sources: [Creating tables with plugins](https://developer.wordpress.org/plugins/creating-tables-with-plugins/) | [dbDelta](https://developer.wordpress.org/reference/functions/dbdelta/) | [MySQL implicit commit](https://dev.mysql.com/doc/refman/8.0/en/implicit-commit.html) | [InnoDB online DDL operations](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-operations.html) | [upgrader_process_complete](https://developer.wordpress.org/reference/hooks/upgrader_process_complete/).
