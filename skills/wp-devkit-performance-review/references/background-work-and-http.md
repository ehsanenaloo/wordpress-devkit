# Background work, remote calls and request-path cost

Research date: 2026-10-08. Contents: 1 What belongs on the request path | 2 WP-Cron | 3 Action Scheduler | 4 Remote HTTP | 5 admin-ajax, REST and Heartbeat | 6 Hook cost | 7 Memory and limits | 8 Review checks

## 1. What belongs on the request path

A visitor's request should do only what the response needs. Move to background work: email, webhooks, API syncs, image regeneration, exports, imports, cache warming, search indexing, large recalculation. Moving work to a queue changes failure handling (retries, idempotency, ordering, visibility to the user) and does not by itself prove a speedup: measure request time before and after, and watch queue age.

## 2. WP-Cron

- WP-Cron is not a daemon. By default WordPress checks for due events on page loads and spawns `wp-cron.php` through a loopback HTTP request (since 6.9 the spawn happens at `shutdown` instead of `wp_loaded` (unless `ALTERNATE_WP_CRON` is enabled), which can reduce delay on the triggering request). On low-traffic sites jobs run late; on high-traffic sites several spawns may overlap.
- Production pattern: set `define( 'DISABLE_WP_CRON', true );` and trigger due events from the system scheduler every minute, either by requesting `wp-cron.php` or, better, with WP-CLI `wp cron event run --due-now` (check the exact flag with `wp cron event run --help`). Otherwise disabling WP-Cron stops all scheduled jobs.
- Schedule once: `if ( ! wp_next_scheduled( 'acme_sync' ) ) { wp_schedule_event( time() + 60, 'hourly', 'acme_sync' ); }` on activation or in a version-gated upgrade, never unconditionally on every `init`. Unschedule on deactivation (`wp_clear_scheduled_hook`). Custom intervals are registered through the `cron_schedules` filter.
- Single events with the same hook and args within a short window are de-duplicated by core; different args are not. A job scheduled per item can flood the cron array (stored as one serialized `cron` option rewritten on each change; a large array is a performance and concurrency problem).
- There is no guarantee of single execution across overlapping spawns: make handlers idempotent, take a lock with an owner and expiry, and bound the batch and runtime. Cron events can fail silently: log failures and monitor `wp cron event list` for events far past due.
- Diagnose: `wp cron event list --fields=hook,next_run_relative`, `wp cron test`, loopback failures in Site Health, and basic-auth or firewall blocks on `wp-cron.php`.

## 3. Action Scheduler

Used by WooCommerce and many plugins; stores actions in dedicated tables and processes them in claimed batches by a queue runner (WP-Cron triggered, an async loopback runner, and the WP-CLI runner for higher throughput).

Tuning knobs documented by the project: `action_scheduler_queue_runner_time_limit` (default 30 s), `action_scheduler_queue_runner_batch_size` (default 25), `action_scheduler_queue_runner_concurrent_batches` (default 1; raising it can substantially raise server load). The `action_scheduler_run_queue` action fires from WP-Cron at most once a minute. For heavy backlogs, run `wp action-scheduler run` under supervision rather than increasing web runners.

Review points: enqueue return values are checked; one action per unit of work with a unique key (`as_has_scheduled_action()` / unique flag) to avoid duplicates; payload args are small (IDs, not blobs); handlers are idempotent and re-entrant; failure and retry policy exist (a failing action retried every minute forever is a backlog); old completed/failed actions are purged (retention filter `action_scheduler_retention_period`); queue age and failed counts are monitored (Tools > Scheduled Actions, or `wp action-scheduler action list --status=failed`). Slow backlog evidence: oldest pending action age, claims per minute, average action duration.

## 4. Remote HTTP

- Every `wp_remote_*` call on the request path adds the remote's latency plus connection setup and blocks PHP. Default timeout is 5 seconds; a down service then costs 5 seconds per request, per call. Set an explicit short `timeout` and `redirection`, handle `WP_Error`, and cache successful and failed responses (a short negative cache avoids hammering a failing service).
- Move calls off the request path (cron/Action Scheduler) or cache the result with correct invalidation; use `blocking => false` only for fire-and-forget calls whose loss is acceptable.
- Parallel calls: `Requests::request_multiple()` (the Requests library bundled in core) instead of serial loops, bounded by concurrency.
- Do not make HTTP calls in `init`, `plugins_loaded`, `admin_init` or `wp_head` unconditionally; update checks and license pings are common offenders (visible in Query Monitor's HTTP API panel). Check frequency, caching and admin-only scoping.
- Payload size and `limit_response_size`; `sslverify` stays true.
- Outage behavior: the site must stay usable when a third party is down; verify with a blocked host in staging (`WP_HTTP_BLOCK_EXTERNAL` with `WP_ACCESSIBLE_HOSTS`).

## 5. admin-ajax, REST and Heartbeat

- `admin-ajax.php` boots all of WordPress and all active plugins per call; frequent polling endpoints are costly. REST routes boot a similar stack. Prefer fewer, batched, cacheable requests; for read endpoints send cache headers appropriate to the audience.
- The Heartbeat API pings every 15 to 60 seconds on the editor and dashboard (heartbeat.js slows to 120 seconds after about five minutes of inactivity) (and the front end when a plugin enables it). On busy admin teams this is a large share of requests. The `heartbeat_settings` filter changes the interval (limits apply) and Heartbeat can be disabled on screens that do not need it; do not disable it in the post editor (autosave locking, login expiry warnings depend on it).
- Polling endpoints should be cheap: no full `WP_Query`, no remote call, short-circuit early (`wp_doing_ajax()` checks in plugin bootstraps that otherwise load heavy admin classes).
- `wp-json` discovery and `admin-ajax` calls by anonymous users should be rate-limited (security skill).

## 6. Hook cost

Measure with `wp profile hook` or Query Monitor's hook panel; the expensive mistakes are structural:
- Queries or remote calls registered on `init`, `wp_loaded`, `plugins_loaded` or `shutdown` that run for every request type (front end, admin, AJAX, REST, cron, CLI). Guard by context (`is_admin()`, `wp_doing_ajax()`, `defined( 'REST_REQUEST' )`, `wp_doing_cron()`) only when the work is not needed there.
- Filters on hot paths (`the_content`, `posts_where`, `option_*`, `gettext`, `sanitize_*`, `pre_get_posts`) that do database or file work per invocation; `gettext` and `option_*` filters run thousands of times per request.
- Loading classes and files eagerly: autoload on demand, avoid scanning directories per request, avoid `include`-ing admin code on the front end, and avoid unserializing large option arrays on every request.
- Recursion: `save_post` handlers that call `wp_update_post()` re-trigger themselves; unhook before updating or guard with a static flag.
- Regex or string processing over the whole page output (output buffering) on every request.

## 7. Memory and limits

Memory exhaustion usually comes from loading result sets or files whole: `get_posts( -1 )`, `get_users()`, `file_get_contents` on big files, building huge arrays, unserializing big options, image processing. Fix by batching (IDs only, process N, free references, `wp_cache_flush_runtime()` in long-running CLI loops on 6.0+ where the object cache grows), streaming files, and setting `WP_MEMORY_LIMIT`/`WP_MAX_MEMORY_LIMIT` as a mitigation, not a fix. In long-running CLI jobs also disable `SAVEQUERIES`, and for imports consider `wp_defer_term_counting( true )` and `wp_defer_comment_counting( true )` around bulk loops (remember to turn them off). Time limits: `set_time_limit()` may be disabled by the host; design jobs to resume.

## 8. Review checks

1. Request-path inventory: each remote call, file operation and loop with a timeout, cache or move-to-queue decision.
2. Cron: scheduled once, idempotent, locked, bounded, monitored; real cron trigger in production.
3. Queue: age, failure rate, retry policy, retention.
4. Hook cost: top callbacks by time from a profile, not guesses.
5. Passing does not prove: behavior under real concurrency, or that a queue drains at production volume; run a staging backlog drill and record drain time.

Sources: [Hooking WP-Cron into the system task scheduler](https://developer.wordpress.org/plugins/cron/hooking-wp-cron-into-the-system-task-scheduler/) | [Action Scheduler performance](https://actionscheduler.org/perf/) | [WordPress 6.9 frontend performance field guide](https://make.wordpress.org/core/2025/11/18/wordpress-6-9-frontend-performance-field-guide/) | [WP-CLI profile](https://developer.wordpress.org/cli/commands/profile/) | [wp_cache_flush_group / object cache](https://developer.wordpress.org/reference/classes/wp_object_cache/). | [Action Scheduler source](https://github.com/woocommerce/action-scheduler) | [core heartbeat.js](https://github.com/WordPress/wordpress-develop/blob/trunk/src/js/_enqueues/wp/heartbeat.js)
