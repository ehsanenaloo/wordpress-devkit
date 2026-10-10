# Storage, scheduled work, privacy and multisite

Contents: choosing storage; options and autoload; transients and object cache; custom tables; `$wpdb->prepare`; WP-Cron; Action Scheduler; multisite; privacy; failure symptoms; sources.

## Choosing storage

| Data | Prefer | Avoid |
|---|---|---|
| A handful of settings | One option array, registered with `register_setting()` | Dozens of autoloaded options |
| Per-object attributes | Post/term/user meta with `register_meta()` | Serialized blobs you must query inside |
| Content-like records edited by users | Custom post type | A table that duplicates revisions/capabilities for no reason |
| High-volume rows, joins, counters, logs | Custom table with owned schema and indexes | Millions of `postmeta` rows queried by value |
| Recomputable cache | Transient or object cache | Anything that must survive a cache flush |

## Options and autoload (behavior since WordPress 6.6)

- Autoloaded options are loaded on every request into memory. In 6.6 `add_option()`/`update_option()` default `$autoload` became `null` (WordPress decides); stored values are `on`, `off`, `auto`, `auto-on`, `auto-off`, and legacy `yes`/`no`. Options without an explicit `true` whose value exceeds 150000 bytes are not autoloaded (`wp_max_autoloaded_option_size` filter; do not raise it). Passing `'yes'`/`'no'` is deprecated since 6.7; pass booleans.
- Site Health reports a critical issue when total autoloaded size exceeds 800 KB.
- Pass `false` for options read on few screens (large arrays, caches, logs). Pass `true` only for options read on most frontend requests.
- Audit: `wp option list --autoload=on --format=total_bytes` is a start, but `--autoload=on` does not match `auto`/`auto-on`; for the real total use `wp db query "SELECT SUM(LENGTH(option_value)) FROM $(wp db prefix)options WHERE autoload IN ('yes','on','auto-on','auto')"`.
- Never store secrets in plain autoloaded options; keep credentials out of exports (`wp option` output, database dumps shared for debugging).
- Name options with the plugin prefix; keep the stored shape stable and migrate through the upgrade routine.

## Transients and the object cache

- A transient is a cache, not storage: with a persistent object cache it lives only in the cache backend and can vanish at any time; without one it is an option row (with a `_transient_timeout_` row) that expiry cleanup may leave behind. Never store data you cannot rebuild.
- The `set_transient()` docblock says names must be 172 characters or fewer (167 for `set_site_transient()`). Hash long keys (`md5`).
- Use `get_site_transient()` / `set_site_transient()` for network-wide caches on multisite; ordinary transients are per site.
- Stampede control: on expiry many requests rebuild the value. Store a soft-expiry timestamp in the value and refresh once, or take a short lock (`wp_cache_add` with a short expiry is atomic on a persistent cache).
- Use cache groups and versioned keys for invalidation (`wp_cache_set( $key . '_' . $version, ... )`; bump the version rather than flushing). `wp_cache_flush_group()` exists only when the backend supports it (`wp_cache_supports( 'flush_group' )`).
- `wp transient delete --expired` removes expired DB transients; it does not clear a persistent object cache.

## Custom tables

Use a custom table when queries need indexes, joins or aggregation that `postmeta` cannot serve. You then own schema, upgrades (see [lifecycle-and-upgrades.md](lifecycle-and-upgrades.md)), retention, export/erase, multisite prefixes, backups and cleanup. Keep primary keys small and index the exact filter/sort columns; avoid `SELECT *` in hot paths; paginate with a keyset (`WHERE id > %d ORDER BY id LIMIT %d`) rather than large `OFFSET`.

## `$wpdb->prepare` (verified)

- Placeholders: `%d`, `%f`, `%s`, and `%i` for identifiers (6.2+; check `$wpdb->has_cap( 'identifier_placeholders' )` if supporting older cores). Leave placeholders unquoted; `%s` is quoted for you. A literal percent is `%%`.
- `LIKE`: `$wpdb->prepare( 'WHERE col LIKE %s', '%' . $wpdb->esc_like( $term ) . '%' )`; wildcards belong in the argument.
- `IN()`: build `implode( ',', array_fill( 0, count( $ids ), '%d' ) )` and pass the values; never `implode` raw values into the string. Guard the empty array.
- A query with no placeholder passed to `prepare()` triggers `_doing_it_wrong`; plain static SQL needs no `prepare`. Table names from `$wpdb->prefix . 'literal'` are safe to interpolate; user-supplied identifiers are not (allow-list them or use `%i`).
- Check `$wpdb->last_error` (or `false === $result`) after writes; `$wpdb->update/insert` return `false` on error and `0` for no change.

## WP-Cron

- Cron runs on page loads, so timing is approximate on low-traffic sites. High-traffic sites should set `define( 'DISABLE_WP_CRON', true )` and trigger `wp cron event run --due-now` from system cron (see `wp-devkit-wpcli-and-ops`).
- Schedule once: `if ( ! wp_next_scheduled( 'acme_sync', $args ) ) wp_schedule_event( ... )`. Arguments are part of the event identity for lookup and clearing.
- Callbacks must be idempotent and time-boxed; a long job needs batches and a cursor option, not one execution that hits the PHP time limit.
- Custom intervals are added through the `cron_schedules` filter; the filter must be registered on every request, not only on activation, or the event stops running.
- Clear on deactivation (`wp_clear_scheduled_hook`); `wp_unschedule_hook()` removes all arguments variants.
- For exact timing or retries with backoff, use Action Scheduler.

## Action Scheduler (when the plugin bundles it or depends on WooCommerce)

Verified API: `as_enqueue_async_action( $hook, $args, $group, $unique, $priority )`, `as_schedule_single_action( $timestamp, ... )`, `as_schedule_recurring_action( $timestamp, $interval, ... )`, `as_schedule_cron_action(...)`, `as_unschedule_action`, `as_unschedule_all_actions`, `as_next_scheduled_action`, `as_has_scheduled_action` (3.3+), `as_get_scheduled_actions`. Use a plugin-specific `$group`; use `$unique` or guard with `as_has_scheduled_action()` to avoid duplicate scheduling. Do not call Action Scheduler APIs before `init` priority 1; use the `action_scheduler_init` hook (Action Scheduler usage docs). Batch work by re-enqueueing the next batch at the end of the current one; treat each action as retryable.

## Multisite

- Per-site data: `get_option`, `$wpdb->prefix`. Network data: `get_site_option`, `$wpdb->base_prefix`.
- `switch_to_blog()` is expensive (cache group switching); avoid it in request paths or loops over hundreds of sites. Iterate with `get_sites( array( 'fields' => 'ids', 'number' => 100, 'offset' => $offset ) )` and always `restore_current_blog()` in `finally`.
- Network admin pages use `network_admin_menu`, `manage_network_options` and `update_site_option`; options.php does not save network settings, so a custom `admin_post_` handler with capability and nonce is needed.
- Object cache keys on multisite are blog-scoped unless the group is registered global (`wp_cache_add_global_groups`).

## Privacy (GDPR)

If the plugin stores personal data (user meta, form submissions, logs with IP or email): register exporters and erasers (`wp_privacy_personal_data_exporters`, `wp_privacy_personal_data_erasers` filters, paginated callbacks returning `done`), add suggested policy text with `wp_add_privacy_policy_content()` on `admin_init`, avoid logging raw personal data, apply a retention schedule via cron/queue, and disclose external services. Verify with Tools > Export/Erase Personal Data on a test user.

## Failure symptoms

| Symptom | Evidence | Fix direction |
|---|---|---|
| Slow every request, memory high | Autoloaded total, largest autoloaded rows | Set `autoload` false for large options; split data |
| Duplicate emails/jobs | Event listed twice, no lock | Guard scheduling, idempotent jobs, unique actions |
| Cron never fires | `cron_schedules` filter registered only on activation, or `DISABLE_WP_CRON` without system cron | Register filter each request; add system cron |
| Cache returns another site's data on multisite | Key lacks blog scope or wrong global group | Scope keys/groups |
| `last_error` ignored, silent data loss | Write result unchecked | Check and surface errors, retry or fail visibly |

## Sources

Research date: 2026-10-08.

- Autoload changes: https://make.wordpress.org/core/2024/06/18/options-api-disabling-autoload-for-large-options/
- `add_option`: https://developer.wordpress.org/reference/functions/add_option/
- `wpdb::prepare`: https://developer.wordpress.org/reference/classes/wpdb/prepare/
- Action Scheduler API: https://actionscheduler.org/api/
- `wp option list`, `wp transient delete`: https://developer.wordpress.org/cli/commands/option/list/ , https://developer.wordpress.org/cli/commands/transient/delete/
