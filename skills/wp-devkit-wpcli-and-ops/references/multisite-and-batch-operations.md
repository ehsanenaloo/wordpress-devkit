# Multisite scope, batch jobs and recurring maintenance

Contents: target scope on multisite; iterating sites; switching context in code; long-running jobs; cron and system cron; cache and transients; locking and concurrency; observability; failure symptoms; sources.

## Target scope on multisite

- `--url=<site-url>` selects the site; it is required to act on any site other than the main one. Without it WP-CLI uses the main site (or the URL in config/alias). Global flags `--network` (for commands that support it) widen scope; they are not interchangeable with `--url`.
- Commands that support `--network`: `plugin activate`, `search-replace` (all `$wpdb`-registered tables), `cron event run`, `transient delete` (where `--network` means network/site transients, not iterating sites), and others. Check `wp help <command>` on the installed version rather than assuming.
- `wp site list --field=url` (verified options: `--network=<id>`, `--site__in`, `--site_user`, `--site-path`, `--field`, `--fields`, `--format=ids|count|json|csv`, `--archived|--spam|--deleted` as field filters) builds the target list. Freeze the list first, then iterate:

```sh
wp site list --field=url --path=/var/www/net > sites.txt     # inspect before acting
while IFS= read -r url; do
  wp --path=/var/www/net --url="$url" option get blogname || echo "FAILED $url" >> failures.txt
done < sites.txt
test ! -s failures.txt
```

Count first (`--format=count`), exclude archived/spam/deleted deliberately, and treat any failure as a failed run.

## Context switching inside PHP

`switch_to_blog( $id )` changes `$wpdb->prefix`, options and object-cache group scope, and is expensive (hundreds of switches per request add measurable time). Rules:
- Always restore: `try { switch_to_blog( $id ); ... } finally { restore_current_blog(); }`. An exception or `WP_CLI::error()` inside the block must not leave the process on the wrong site; `WP_CLI::error()` exits, so restore before calling it or use `finally` plus a result flag.
- Prefer one process per site (`WP_CLI::runcommand( ..., array( 'launch' => true ) )` or an external loop with `--url`) for large networks: fresh state, bounded memory, per-site failure isolation.
- Use `get_sites( array( 'fields' => 'ids', 'number' => 100, 'offset' => $n, 'orderby' => 'id' ) )` rather than fetching all sites; skip archived/deleted/spam by arguments (`archived`, `spam`, `deleted` => 0).
- Network tables (`$wpdb->base_prefix`) are shared; per-site tables use `$wpdb->get_blog_prefix( $id )`.

## Long-running jobs

Design for interruption: `--batch-size` validated (for example 1-1000), stable keyed ordering, upper bound captured at start, checkpoint recorded after each verified batch, resumable via `--resume-from` or the stored checkpoint, idempotent per item. Define what happens to concurrent edits (revisit, ignore, reconcile) and say so in the runbook. Output a summary with processed, skipped, failed, duration and last cursor, and a non-zero exit when any item failed. Do not run heavy jobs on the web request path or on every cron tick.

## WP-Cron and system cron

- WP-Cron runs when pages load; low-traffic sites run late, high-traffic sites can run overlapping spawns. Production pattern: `define( 'DISABLE_WP_CRON', true );` in `wp-config.php` and a system scheduler running `wp cron event run --due-now` (verified flag; it respects the `doing_cron` transient to avoid overlapping runs) every minute or five. Use `--url` per site, or `--network` (supported) on multisite.
- Diagnose: `wp cron event list --fields=hook,next_run_gmt,recurrence`, `wp cron schedule list`, and `wp cron test` (it errors when `DISABLE_WP_CRON` is true, warns when `ALTERNATE_WP_CRON` is set, and otherwise tests an HTTP spawn; it is not meaningful on a site that deliberately uses system cron).
- `wp cron event run <hook>` executes the hook callbacks immediately: it is an operation with effects (emails, API calls, deletions), not a diagnostic. Run it only with scope and approval; prefer a staging copy.
- Scheduling inside a command: use `wp_next_scheduled` before `wp_schedule_event`; clear with `wp_clear_scheduled_hook` using the same args.

## Cache and transients

- `wp cache flush` flushes the object cache; on multisite and shared Redis/Memcached it typically affects all sites and sometimes other applications on the same instance (verified wording: "typically flush the cache for all sites"; warns about production performance impact). Use only in a planned window; prefer targeted deletes (`wp cache delete <key> <group>`, `wp transient delete <key>`) or versioned keys. Check whether the Redis database is shared before flushing.
- `wp transient delete --expired` clears expired DB transients (and `--all` all of them; `--network` for site transients). It does not clear a persistent object cache.
- Cache priming in a command: only write cache entries when not dry-running, check each write's return value, remember that without a persistent backend the entries die with the process.
- `wp rewrite flush` (add `--hard` only when `.htaccess` rules should be rewritten as well; the command page says `--hard` works only on single-site installs) regenerates rules; avoid in a loop.

## Locking and concurrency

Two overlapping runs of the same maintenance command can double-process. Use `flock` around the system cron entry (`flock -n /var/lock/acme-sync.lock wp acme sync`) or an atomic `add_option` lock with an expiry and a stale-lock policy. A lock is a safety mechanism, not a correctness proof; keep items idempotent.

## Observability and runbooks

Log start/end, target (path, URL, DB name without credentials), version of WP-CLI/PHP/WordPress, arguments (redacted), counts and exit code to a file or logging system; keep log retention and personal data policy in mind (no raw emails or tokens). Alert on non-zero exits and on jobs that have not run within the expected window (heartbeat). A runbook for each recurring operation lists purpose, preconditions, exact commands, expected output, rollback and escalation.

## Failure symptoms

| Symptom | Evidence | Fix |
|---|---|---|
| Wrong site modified | No `--url`, loop without frozen list | Explicit targeting, frozen list, dry run |
| Jobs skipped | `OFFSET` paging, interrupted run with no checkpoint | Keyed cursor, checkpoints |
| Subsequent queries hit another site | Missing `restore_current_blog()` after error | `finally` restore |
| Scheduled tasks never run | `DISABLE_WP_CRON` with no system cron, or loopback blocked | `wp cron event list` for overdue events; add system cron; `wp cron test` only when WP-Cron is enabled |
| Overlapping runs | No lock | `flock`/atomic lock |
| Site-wide slowdown after "cache clear" | `wp cache flush` on shared Redis | Targeted invalidation, warm-up plan |

## Sources

Research date: 2026-10-08.

- `wp site list`: https://developer.wordpress.org/cli/commands/site/list/
- `wp cron`: https://developer.wordpress.org/cli/commands/cron/ and `cron event run`: https://developer.wordpress.org/cli/commands/cron/event/run/
- `wp cache flush`: https://developer.wordpress.org/cli/commands/cache/flush/
- `wp transient delete`: https://developer.wordpress.org/cli/commands/transient/delete/
- `wp plugin activate`: https://developer.wordpress.org/cli/commands/plugin/activate/
- Global config and `--url`: https://make.wordpress.org/cli/handbook/references/config/

Notes from the package READMEs: `wp cron test` behavior, `wp cron event run [<hook>...] [--due-now] [--exclude] [--all] [--network]`, `wp cache delete <key> [<group>]`, `wp rewrite flush [--hard]`, `wp transient delete [<key>] [--network] [--all] [--expired]`, `wp site list` filters including `--site__in`, `--site_user`, `--site-path` (https://github.com/wp-cli/cron-command, https://github.com/wp-cli/cache-command, https://github.com/wp-cli/rewrite-command, https://github.com/wp-cli/entity-command). Check the `get_sites()` argument keys (standard `WP_Site_Query`; see the developer reference) and the `flock` recipe (OS behavior, not WordPress).
