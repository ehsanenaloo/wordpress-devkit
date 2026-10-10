# Performance review workbook

Apply [the engineering contract](engineering-contract.md) first.

Contents: 1 Evidence ladder | 2 Severity | 3 Finding template | 4 Symptom to cause | 5 Looks slow but is fine | 6 Looks fine but is slow | 7 Acceptance checks | 8 Sources

## 1. Evidence ladder

Strongest to weakest: field data (real users, p75), production profiler sample, staging with production-sized data, local synthetic run, source reading. Claims must name the rung they stand on. Source reading alone yields a hypothesis with an expected-cost argument, never a measured gain.

Always record: WordPress/PHP/DB versions, theme and active plugins, object-cache backend and page-cache state, dataset size, user role, URL or action, tool and its overhead (Query Monitor and `SAVEQUERIES` add cost), number of runs, cold vs warm.

A budget comes from the project (SLO, contract, Core Web Vitals "good" at p75: LCP 2.5 s, INP 200 ms, CLS 0.1). Copied thresholds from articles are not a budget.

## 2. Severity

Contract item 5 applies; performance anchors:

| Demonstrated impact | Severity |
|---|---|
| Request or job fails or times out on realistic data (memory exhaustion, 504, deadlock, backlog that never drains); cache serves another user's private data; unbounded query reachable by anonymous callers | CRITICAL |
| Measured budget violation on a core journey, N+1 growing with data, autoload bloat above the Site Health threshold, uncached remote call on every request, stampede on expiry | WARNING |
| Micro-optimization, unproven inefficiency, style preference | INFO |

Cache correctness defects (wrong audience, stale authoritative data) are correctness first; rate them by data exposed or business impact, not by speed.

## 3. Finding template

```text
[SEVERITY][confidence: measured|estimated|hypothesis] Short title
Location : path/file.php:LINE
Journey  : URL/role/action and data volume
Evidence : tool, run conditions, numbers (queries, ms, MB, hit ratio); what was NOT measured
Cause    : why the cost scales (per row, per request, per user)
Effect   : expected gain and its basis
Fix      : minimal change; what must stay identical (results, order, privacy)
Regression: query-count/budget assertion, invalidation test, or load check
```

## 4. Symptom to cause

| Symptom | First evidence | Likely areas |
|---|---|---|
| High TTFB on every page | `wp profile stage`, Query Monitor timings | Autoload bloat, slow plugin hooks on `init`, uncached remote call, no page cache |
| Slow only for logged-in users | Compare cache headers; profile as that role | Page cache bypass, per-user queries, admin bar, personalization |
| Slow archive / search / filter | Query Monitor slowest queries, `EXPLAIN` | Meta/tax queries, `LIKE '%x%'`, `SQL_CALC_FOUND_ROWS` on huge tables, `-1` limits |
| Slow admin list or editor | Query Monitor on the screen, admin-ajax timings | Per-row queries, Heartbeat, metaboxes loading all posts |
| Intermittent spikes | Access log correlation, cron events | Cache expiry stampede, cron overlap, backups, bots |
| Memory exhaustion | `memory_get_peak_usage`, result size | Loading all posts/users/orders at once, large arrays in options |
| Stale or wrong data | Cache keys and invalidation trace | Missing key dimension, missing invalidation event, page cache with cookies |
| Jobs back up | Queue age and runner logs | Runner starvation, batch too large, failing action retried forever |
| Good lab score, bad field score | CrUX or RUM by device/country | Slow devices, third parties after consent, personalized content |

If evidence does not support the suspected cause, keep the hypothesis open and inspect the next layer.

## 5. Looks slow but is fine

- `get_post_meta()` in a loop over posts returned by `WP_Query`: meta is primed in one query by default (`update_post_meta_cache`), so repeated calls hit the cache. Verify the actual query count before calling it N+1; it becomes N+1 only if priming is off, the IDs came from `fields => 'ids'` or a raw SQL query, or the posts were fetched individually.
- `get_option()` calls: autoloaded options are loaded once per request and cached; many `get_option()` calls are cheap. The cost is the size of the autoload set and non-autoloaded options read repeatedly with persistent cache absent (each miss is a query, then cached for the request).
- `posts_per_page => -1` in an admin-only export, WP-CLI command, or on a taxonomy known to hold a handful of posts.
- A meta query on a small table or one that is paginated and cached.
- `WP_Query` with `no_found_rows` omitted on a short list where the total is used for pagination.
- Transients used for a computation that is expensive and invalidated correctly; the "database transients are bad" claim is false when no persistent object cache exists, and fine to keep.
- `wp_remote_get()` inside a cron/Action Scheduler job with timeout and retry.
- Minifying or concatenating assets under HTTP/2 or HTTP/3: gains are small; measure.
- `wp_cache_flush()` in a deploy script: expensive for the hit ratio afterwards but intentional; flag only when it runs on user requests.

## 6. Looks fine but is slow

- A "cached" call that is a miss every time: key includes a changing value (time, nonce, random), TTL of a few seconds, or non-persistent group; hit ratio near zero.
- Cache set after every request, or flush on every `save_post`/`update_option` of unrelated data.
- `get_posts()` / `WP_Query` with `suppress_filters` removed, or called in `pre_get_posts`/`posts_where` recursively on every query.
- Hooks registered on `init`, `wp_loaded` or `plugins_loaded` doing queries or HTTP on every request, including admin-ajax and REST.
- `update_option()` on every page view (writes to `wp_options`, invalidates caches, bumps `alloptions`).
- Autoloaded options with large values (serialized logs, queues, license payloads, page-builder caches).
- `LIKE '%term%'` search on postmeta/usermeta/content; `ORDER BY meta_value` without a bounded set.
- `count(get_posts(...))` to get a total; `get_users()` to count users; `wp_count_posts()` fine (cached) but `new WP_Query` for counts is not.
- Per-site loops (`get_sites()` + `switch_to_blog()`) on networks with thousands of sites.
- Remote call on every request with a long default timeout when the remote is down.

## 7. Acceptance checks

| Check | Method | Passing proves | Does NOT prove |
|---|---|---|---|
| Query count and time | Query Monitor, `SAVEQUERIES`, PHPUnit `$wpdb->num_queries` delta | Same-scenario cost fell on that dataset | Behavior on production-sized data |
| Plan | `EXPLAIN` / `EXPLAIN ANALYZE` (MariaDB: `ANALYZE`) of the exact statement | Index use for those parameter values | Plans for other values or statistics |
| Stage profile | `wp profile stage --all` / `wp profile hook` on a warmed site | Where bootstrap time goes | Browser metrics |
| Cache correctness | Two identities, cold then warm, inspect headers and bodies; invalidation after write | No cross-user leak on that path | Persistent-cache eviction behavior unless run with the real backend |
| Load | k6 / wrk / ab against staging with a bounded duration | Throughput/latency at that load | Real traffic mix |
| Field | CrUX/RUM p75 over 28 days | User-experienced change | Cause |
| Results unchanged | Golden-result test: ids, order, totals | No semantic regression | Performance |

Record tool versions, dataset, run counts and exit status; list unexecuted checks (persistent cache, concurrency, field data).

## 8. Sources

Research date: 2026-10-08. [WP_Query](https://developer.wordpress.org/reference/classes/wp_query/) | [WP_Object_Cache](https://developer.wordpress.org/reference/classes/wp_object_cache/) | [Options API autoload change (6.6)](https://make.wordpress.org/core/2024/06/18/options-api-disabling-autoload-for-large-options/) | [Web Vitals](https://web.dev/articles/vitals) | [Transients](https://developer.wordpress.org/apis/transients/) | [WP-CLI profile](https://developer.wordpress.org/cli/commands/profile/).
