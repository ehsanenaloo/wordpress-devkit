---
name: wp-devkit-performance-review
description: Investigate and improve measured WordPress performance: slow queries, N+1 loads, autoloaded options, object/page cache correctness, cron and remote calls, hook cost, Core Web Vitals. Use for a slow or must-scale journey with workload context; ordinary code review alone does not select this skill.
---

# Measured queries, caches and delivery

Read `references/engineering-contract.md` first. A review request is read-only: measure what exists, explain and recommend; do not edit, flush caches, run load against production or execute untrusted code. Implement only when the user authorizes changes.

Hand off: security of an endpoint to `wp-devkit-security-review`; WooCommerce HPOS order APIs to `wp-devkit-woocommerce-dev`; WP-CLI batch runbooks to `wp-devkit-wpcli-and-ops`; schema backfills to `wp-devkit-migration-upgrade-review`; accessibility of loading states to `wp-devkit-wcag-review`.

## Inputs

The slow journey (URL, role, action), data volume (posts, meta rows, users, orders, sites), budget (e.g. TTFB p75, LCP/INP/CLS p75, queries per request, memory), baseline numbers, cache and CDN topology (page cache, persistent object cache backend, host), authentication state, and available profilers. Without a baseline or budget, say the task is a hypothesis list, not a performance finding.

## Code Review Workflow

1. Define the journey and the symptom class: slow server response (TTFB), slow query, memory/timeouts, stale or wrong cached data, background backlog, or slow browser metrics. Different classes use different evidence.
2. Establish the measurement: same build, dataset, user and cache state before and after; enough repetitions to see variance; separate cold and warm cache. Read `references/profiling-and-tooling.md` for tools and commands.
3. Locate cost: database (count, duplicates, slow statements, EXPLAIN), hooks and filters, remote HTTP, cache miss rate, memory, then frontend (network waterfall, long tasks, layout shifts).
4. Judge the cause against the topic references; load only what applies (list below).
5. Check that a proposed change preserves the result contract: filters, order, visibility, pagination, totals, privacy and multisite scope. A faster query that changes results is not an optimization.
6. Rank by measured share of the request, not by how suspicious the code looks. Report estimated gain only with a basis; never invent a speedup from source reading.

Read `references/performance-review-workbook.md` for severity rules, the finding template, false positives and acceptance checks.

## Implementation workflow

1. Record the baseline (command, dataset, numbers) and the budget before changing code.
2. Make one change at a time at the measured hotspot; keep results identical; keep fallbacks for cache misses and eviction.
3. Re-measure with the same method; compare distributions, not one run. Run the functional tests that cover the changed query or cache.
4. Add a guard where possible: a PHPUnit query-count assertion, a cache-invalidation test, or a budget check in CI.
5. Do not add a cache without stating key dimensions, invalidation events and the authoritative source. Cache changes can leak private data; test two identities.

## Search Patterns for Quick Detection

Read-only leads from the first-party root; they are candidates, not findings, and a hit says nothing about cost without a measurement. Exit codes: 0 match, 1 none, 2 error.

```sh
scan() { rg -n -g '*.{php,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e "$1" "${2:-.}"; }
scan "posts_per_page['\"]?\s*=>\s*-1|numberposts['\"]?\s*=>\s*-1|nopaging|'limit'\s*=>\s*-1"   # unbounded result sets
scan "meta_query|meta_key|meta_value|tax_query|post__not_in|'s'\s*=>|LIKE\s+'%"   # heavy query shapes
scan 'get_(post|user|term)_meta\s*\(|get_option\s*\(|WP_Query|get_posts\s*\(|get_users\s*\(|get_terms\s*\('   # calls to check inside loops
scan "add_option\s*\(|update_option\s*\(|autoload|set_transient|get_transient|wp_cache_(get|set|add|delete|flush)"   # option, transient and cache use
scan "wp_remote_(get|post|request)|file_get_contents\s*\(\s*['\"]?https?|curl_exec|sleep\s*\(|usleep"   # blocking work on the request path
scan "wp_schedule_(single_)?event|wp_next_scheduled|as_(schedule|enqueue)|wp_ajax_|heartbeat|admin-ajax|'heartbeat_settings'"   # cron, ajax, early hooks
scan "wp_(enqueue|register)_(script|style)|<script|<link\s+rel|loading=|fetchpriority|font-display|@import"   # frontend delivery
scan 'switch_to_blog|get_sites\s*\(|get_blog_option|wp_get_sites'   # per-site loops on networks
```

Typical benign hits: a meta query on a table of a few hundred rows, `get_post_meta` inside a loop whose posts were primed by `WP_Query`, `-1` in an admin-only export run in batches, a remote call inside a queued job.

## Task-selected resources

- `references/profiling-and-tooling.md`: Query Monitor, `wp profile`, `SAVEQUERIES`, EXPLAIN, load tools, safe production sampling. Read before measuring.
- `references/queries-and-options.md`: `WP_Query` arguments, meta/taxonomy queries, N+1, autoload and options, indexes, HPOS, large tables. Read for slow queries or database load.
- `references/performance-cache-coordination.md`: object cache, transients, page cache privacy, invalidation, locks, counters. Read for stale or wrong cached data and stampedes.
- `references/background-work-and-http.md`: WP-Cron, Action Scheduler, remote HTTP, admin-ajax and Heartbeat, hook cost. Read when work happens on the request path or jobs back up.
- `references/frontend-performance.md`: LCP, INP, CLS, WordPress asset APIs, images, fonts, speculative loading. Read for browser metrics.

## Output Format

Lead with the verdict, journey and measurement basis. Per finding: severity, `file:line`, trigger (request/data volume), measured evidence (numbers, tool, run conditions), root cause, expected effect and its basis, minimal fix, regression or budget check. Keep hypotheses and missing measurements separate. End with executed checks (command, exit status), unexecuted checks (for example persistent cache, production-sized data, field data) and residual risk. For implementation add before/after numbers on the same dataset. A pass on a lab run does not prove field improvement.
