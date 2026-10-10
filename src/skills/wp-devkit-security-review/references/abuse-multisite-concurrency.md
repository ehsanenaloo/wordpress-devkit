# Abuse, tenant isolation and concurrency

Research date: 2026-10-08. Contents: 1 Public endpoints and abuse | 2 Webhooks and replay | 3 Tenant isolation | 4 Concurrency | 5 Severity and evidence | 6 Checks

## 1. Public endpoints and abuse

Candidates: contact/newsletter/comment forms, registration, login, password reset, XML-RPC, public REST routes, search and filter endpoints, `admin-ajax` `nopriv` actions, file or URL importers, export links, coupon or code-check endpoints, anything that sends email or SMS, calls a paid API or runs an expensive query.

For each, write the actor, the unit cost to the attacker, the cost to the site or third party, the state change, and the recovery path. Then check which bound exists:

- Rate limit per IP and per identity (account, email, session), with a bounded store. A transient-based counter on a site with a persistent object cache can be evicted; a counter keyed only by client IP is bypassed through proxies and shared by NAT users; trusting `X-Forwarded-For` without a trusted-proxy rule lets the caller choose its own key.
- Lockout and enumeration: identical responses and timing for existing vs unknown accounts or emails; reset flows that do not reveal existence; lockout that cannot be abused to lock out a victim indefinitely.
- Resource caps: `per_page` maximum, `posts_per_page => -1` reachable from a request, unbounded `LIKE '%term%'`, deep pagination, regexp input, uploads, archive and image sizes, recursion depth in JSON or XML, batch sizes in importers.
- Email and notification amplification: one request causing mail to an arbitrary address (contact form with a user-chosen recipient, "send to a friend") is a spam relay.
- Cost: outbound calls to metered APIs per anonymous request.

WordPress offers no built-in public rate limiter. Evaluate the project's own mechanism, or edge controls (WAF, CDN), and test with controlled accounts and bounded request counts, never against production.

Pre-built defenses to credit: `wp_login_failed` hooks, `authenticate` filter throttles, core's `wp_check_comment_flood`, CAPTCHA/honeypot. Do not credit a nonce on a guest form as an abuse control (guests share one nonce value).

## 2. Webhooks and replay

- Verify a signature over the raw body (`hash_hmac( 'sha256', $raw, $secret )`) compared with `hash_equals()`. Read `file_get_contents( 'php://input' )`, not re-encoded JSON.
- Enforce a timestamp tolerance and store processed event IDs so a captured valid request cannot be replayed; make handlers idempotent (unique key on provider event ID).
- Per-integration secrets, rotation plan, and no secret in query strings (they end up in access logs).
- Answer fast and queue slow work; do not run unbounded work in the request.
- Nonces provide neither replay protection nor idempotency: a nonce stays valid for its whole lifetime.

## 3. Tenant isolation

For multisite and any multi-tenant plugin (agencies, memberships, marketplaces) trace the tenant identifier from the request to storage:

- Every query on a custom table includes the tenant or blog filter in the `WHERE` clause; IDs from the request are checked against the tenant before use. Global tables with a `blog_id` column are the usual gap.
- `switch_to_blog()` pairs with `restore_current_blog()` on every exit path (use try/finally); a thrown exception between them leaves later code running on the wrong site. Loops over `get_sites()` for large networks need batching (see the performance skill).
- Option, transient and cache keys include the blog ID, or use the site-scoped APIs; `get_site_option`/`set_site_transient` are network-wide on purpose.
- Uploads: `wp_upload_dir()` is per site; shared directories mix tenants.
- REST and AJAX capability checks run on the correct site context; super admin passes everything, so test with a site administrator who has no role elsewhere.
- Background jobs carry the blog ID in their payload and restore it before touching data.
- Object-level IDs (orders, subscriptions, form entries) are authorized per tenant, not only per role.

Test matrix: user A on site 1 reading and writing site 2 objects (expect 403/404), super admin allowed, network-activated vs per-site activation, new site creation after plugin activation.

## 4. Concurrency

Look for check-then-act sequences where the check and act are not atomic: coupon use limits, stock decrement, one-time token redemption, "claim" or "seat" flows, balance or credit updates, duplicate-order prevention, idempotency keys, file replacement, option read-modify-write (`get_option` then `update_option` loses concurrent updates), and cron jobs that run twice (WP-Cron has no strong single-run guarantee).

Controls to look for: a database `UNIQUE` index plus handling duplicate-key failure, `UPDATE ... SET qty = qty - 1 WHERE qty > 0` and checking affected rows, `INSERT ... ON DUPLICATE KEY UPDATE`, `add_option()` as an atomic claim (fails when the option exists), `SELECT ... FOR UPDATE` inside a transaction on InnoDB tables (MyISAM has no row locks or transactions), named locks (`GET_LOCK`) with a bounded wait, and idempotency records. An object-cache lock without atomic acquire and owner-checked release is not a lock (see the performance cache reference).

Evidence rule: a high-severity race needs a reproducible interleaving or a clearly violated invariant. Record workload, number of workers, timing and the resulting persisted state (e.g. 12 redemptions of a 10-use coupon). Without it report a candidate. Do not mark TOCTOU as exploitable on single-user admin screens without a second actor.

## 5. Severity and evidence

Bounded, low-value abuse (a missing rate limit on a search) is INFO or WARNING. Credential-guessing without throttling on login or reset, cross-tenant data access, and monetary races (double-spend of credit, unlimited coupon) are WARNING to CRITICAL by demonstrated impact. Denial of service by one request that exhausts memory or the database is WARNING unless an anonymous actor can repeat it cheaply, then CRITICAL.

## 6. Checks

1. Each public endpoint: documented bound, tested with a controlled burst against staging.
2. Webhook: signature, timestamp, replay store, idempotency.
3. Tenant: matrix test above passes; no shared key or table without tenant filter.
4. Concurrency: two parallel requests (WP-CLI `xargs -P`, k6, or `ab` against staging) produce at most the allowed effects; the database constraint holds.
5. What a pass does not prove: coverage of distributed attackers, or behavior under a different cache backend.

Sources: [Nonces](https://developer.wordpress.org/apis/security/nonces/) | [OWASP API Security Top 10](https://owasp.org/API-Security/).
