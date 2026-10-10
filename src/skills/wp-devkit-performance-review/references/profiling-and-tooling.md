# Profiling and measurement tooling

Research date: 2026-10-08. Contents: 1 Principles | 2 Query Monitor | 3 WP-CLI profile | 4 SQL evidence | 5 Request-level and load | 6 Browser and field | 7 Safe production sampling | 8 Reporting

## 1. Principles

- Measure on a copy with production-shaped data. A 50-post dev site hides every scaling problem.
- Fix the variables: same dataset, same user role, same cache state (cold and warm reported separately), same PHP/opcache settings, debug flags off except the profiler. `WP_DEBUG`, Query Monitor and `SAVEQUERIES` add overhead; compare timings only between runs with the same tooling.
- Repeat. Report median and spread (p75/p95) over enough runs to see noise; a single sample is an anecdote.
- Profile before and after with the same method. Keep the raw output in the report (redacted).
- Review mode: reading existing profiler exports, logs or slow-query logs is fine. Installing plugins, enabling `SAVEQUERIES` or running a load test is an action that needs authorization and a non-production target.

## 2. Query Monitor (plugin)

A WordPress plugin that adds a panel to the admin bar for administrators. Use it on staging to see: queries grouped by calling component (plugin/theme/core), duplicate queries, slow queries, queries with errors, HTTP API requests with duration, hooks and their callbacks, enqueued scripts and styles, REST and Ajax requests (via response headers), PHP errors, and memory/time. Typical uses: identify the plugin responsible for the bulk of queries; find duplicate identical queries (a caching or priming opportunity); see which HTTP call blocks the request. It needs the `db.php` drop-in to capture queries (it installs a symlink); remove it after the session. Do not leave it enabled for anonymous users or in production.

## 3. WP-CLI profile

Install on a development or staging environment: `wp package install wp-cli/profile-command`. Commands:

```sh
wp profile stage --all --spotlight          # time per load stage (bootstrap, main_query, template); hide zero-cost rows
wp profile stage bootstrap --fields=stage,time,cache_ratio
wp profile hook init --spotlight            # callbacks on a hook, time and query counts
wp profile hook --all --url=https://staging.example/shop/
wp profile eval 'wp_remote_get( "https://api.example/" );'   # profile arbitrary code (do not run untrusted code)
wp profile eval-file path/to/script.php
```

It reports time, query counts and cache hit ratio per stage, hook and callback. It profiles the CLI process loading WordPress, so it is good for bootstrap and hook cost, not for browser-visible behavior or front-end caching. Use `--url` to load a front-end URL context. The `--fields` and `--spotlight` flags are documented; confirm others with `wp profile --help` on the installed version.

## 4. SQL evidence

- Slow query log: MySQL/MariaDB `slow_query_log=1`, `long_query_time` low on staging; `log_queries_not_using_indexes` is noisy but useful for sweeps. Summarize with `pt-query-digest` (Percona Toolkit) or `mysqldumpslow`. In production, read existing logs; do not change server settings without ownership.
- `SAVEQUERIES` constant (define `SAVEQUERIES` as true in a staging `wp-config.php`) fills `$wpdb->queries` with SQL, time and a caller stack; dump on `shutdown` to a log. It stores every query in memory.
- `EXPLAIN SELECT ...` (MySQL 8 and MariaDB) for the statement with real parameter values; `EXPLAIN ANALYZE` in MySQL 8.0.18+ runs the statement and reports actual timing, `ANALYZE SELECT` in MariaDB. Read: access type (`ALL` = full scan), `key` used, `rows` estimate, `Using filesort`, `Using temporary`. Run through `wp db query "EXPLAIN SELECT ..."` or a client; take the statement from the profiler, not from reconstruction.
- Table facts: `wp db size --tables`, `SELECT COUNT(*) FROM wp_postmeta`, `SHOW INDEX FROM wp_postmeta`. `wp_postmeta` has indexes on `post_id` and `meta_key` (prefix length 191), none on `meta_value`; sorting or filtering by `meta_value` cannot use an index on it.
- Autoload size: `wp option list --autoload=on --format=total_bytes` gives the total; `wp option list --autoload=on --fields=option_name,size_bytes --format=csv | sort -t, -k2 -nr | head -20` lists the largest (`--orderby` cannot sort by size). On WordPress 6.6+ the stored autoload values are wider than `yes`; see the queries reference for the SQL form.

## 5. Request-level and load

- Server timing: `curl -o /dev/null -s -w 'ttfb=%{time_starttransfer} total=%{time_total}\n' URL` repeated; compare cached vs uncached (`Cache-Control`, `Age`, `X-Cache` headers; add a cache-busting query only if the cache keys on it).
- Load: k6 (scriptable, thresholds), wrk, hey, ab. Use staging, a bounded duration and concurrency, authenticated flows with test accounts, and a realistic URL mix. Report concurrency, duration, error rate and p95; watch PHP-FPM saturation (`pm.max_children` reached), DB connections and CPU.
- PHP-level profilers: Xdebug profiler (dev only, large overhead), Blackfire, Tideways/XHProf-style sampling, or hosting APM (New Relic, Datadog). Use sampling profilers for production-like data; interpret wall time vs CPU time.
- Object cache: `wp cache type`; with Redis, `redis-cli INFO stats` (`keyspace_hits`/`keyspace_misses`, `evicted_keys`), `INFO memory`; the Redis Object Cache plugin's diagnostics; confirm the drop-in is `object-cache.php` in `wp-content`.
- Cron: `wp cron event list --fields=hook,next_run_relative`, `wp cron test`; Action Scheduler: `wp action-scheduler` commands and the Tools > Scheduled Actions screen for pending/failed counts.

## 6. Browser and field

- Lab: Lighthouse / Chrome DevTools Performance panel with CPU and network throttling, trace of the interaction; WebPageTest for filmstrips and waterfalls; record device, viewport, network, cache state and consent state of third parties.
- Field: CrUX (PageSpeed Insights, CrUX API/BigQuery) for p75 LCP/INP/CLS by origin or URL; the `web-vitals` JavaScript library to send real-user metrics with attribution (which element, which interaction) to your own endpoint. Lab results diagnose; field results decide.
- Compare equivalent routes; a template-level fix should be verified on each distinct template (home, archive, single, cart, checkout).

## 7. Safe production sampling

Prefer already-present data: APM traces, slow logs, access logs with `$request_time`, CrUX. If sampling is needed: sample a small percentage of requests, enable timing only (not payload capture), redact URLs with tokens, set an end time, and name an owner who can disable it. Never leave `SAVEQUERIES` or query logging enabled in production.

## 8. Reporting

For every number give: tool and version, URL/action, dataset size, cache state, run count, and whether tooling overhead was included. State what was not measured. A before/after pair from different datasets or cache states is not a comparison.

Sources: [WP-CLI profile command](https://developer.wordpress.org/cli/commands/profile/) | [Core Web Vitals](https://web.dev/articles/vitals) | [Query Monitor](https://wordpress.org/plugins/query-monitor/) | [Action Scheduler performance](https://actionscheduler.org/perf/).
