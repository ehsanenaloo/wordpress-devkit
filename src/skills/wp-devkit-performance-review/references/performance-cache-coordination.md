# Cache correctness and concurrency

Apply [the engineering contract](engineering-contract.md) first. Researched 2026-10-08. Cache proposals require topology and correctness evidence.

Contents: 1 Topology | 2 Object cache API | 3 Transients | 4 Page and fragment caching | 5 Keys and invalidation | 6 Stampedes and locks | 7 Counters | 8 Multisite and operations | 9 Review checks

## 1. Topology

Map every layer: browser, CDN or reverse proxy, page cache (plugin, host, Varnish/nginx), object cache (request-local or persistent drop-in: Redis, Memcached), transients, OPcache, database buffer pool. For each: backend and version, eviction policy and memory limit, shared workers, multisite prefix, supported operations. Core's object cache is request-local without a persistent `wp-content/object-cache.php` drop-in; with the drop-in, entries survive requests but may be evicted at any time. A transient expiration is a maximum lifetime, not a minimum availability promise: always recompute safely on a miss.

For each cached object document: authoritative source, key dimensions (identity, authorization, tenant, locale, currency, query, device), freshness allowance, invalidation events, fallback behavior. Permission decisions, inventory, payment state and accepted jobs need durable authority, never only a cache.

## 2. Object cache API

```php
$found = false;
$value = wp_cache_get( 'public_listing', 'acme', false, $found );
if ( ! $found ) {
	$value = acme_build_public_listing(); // Existing application function.
	wp_cache_set( 'public_listing', $value, 'acme', 300 );
}
```

Use `$found` to distinguish a cached `false`/`0`/empty from a miss. Some drop-ins implement `wp_cache_get` without the `$found` parameter (it then stays `null`): test the deployed drop-in. Key and group names are scoped by the drop-in's prefix; use a plugin-specific group.

Bulk and group APIs, with the WordPress versions that introduced them: `wp_cache_get_multiple()` (5.5), `wp_cache_set_multiple()`, `wp_cache_add_multiple()`, `wp_cache_delete_multiple()` (6.0), `wp_cache_flush_group()` (6.1), `wp_cache_flush_runtime()` (6.0). Core provides polyfills, but whether a "multiple" call is one network round trip depends on the drop-in: inspect it before claiming a latency gain. Before relying on group flushing, call `wp_cache_supports( 'flush_group' )`; if unsupported, `wp_cache_flush_group()` returns false, and a drop-in fallback might flush more than the group. Prefer known-key deletes when the dependency set is bounded. (Verified against core `cache.php` docblocks.)

Non-persistent groups (`wp_cache_add_non_persistent_groups()`) and global groups (`wp_cache_add_global_groups()`, shared across a network) change visibility; check that data placed in a global group has no tenant-specific content.

`wp_cache_incr()` and `wp_cache_decr()` fail on missing keys and are as durable as the backend.

## 3. Transients

- `set_transient( $key, $value, $ttl )`: stored in `wp_options` when no persistent object cache is installed, otherwise in the object cache (and then possibly absent at any time). Keys must be 172 characters or fewer. Site transients (`set_site_transient`) are network-wide.
- With the database as backend, expired rows are removed only when read or by occasional cleanup; large transient volumes bloat `wp_options`; `wp transient delete --expired` removes expired ones. Do not store transients without expiry in the database if they are large (with the database backend and no expiry, core stores the transient as an autoloaded option, per `set_transient()` in `wp-includes/option.php`).
- `get_transient()` returns `false` for a miss and a stored `false` alike; wrap values in an array when `false` is meaningful.
- Do not use transients as durable state (job acceptance, rate-limit bans with legal effect, one-time tokens that must not repeat).

## 4. Page and fragment caching

Anonymous and non-admin do not imply public: carts, sessions, previews, password-protected posts, personalized prices, nonce-bearing markup and signed URLs can contain private content. Use the existing application or CDN rules; do not install a blanket public `Cache-Control` header. WordPress sends `nocache_headers()` on some private screens, but each plugin response needs its own decision.

- Cache partitioning must work before TTL is increased. Test two identities across cold and warm requests and inspect `Cache-Control`, `Set-Cookie`, `Vary` and bodies. A response that sets a cookie is typically not cacheable by shared caches; a `Vary: Cookie` response fragments the cache per user.
- Pages with nonces: a cached nonce becomes invalid for other users or after expiry (12 to 24 hours by default); load nonces by AJAX/REST or exclude those pages.
- WooCommerce cart, checkout, account and `?add-to-cart=` URLs must bypass full-page caches; cart fragments must not be cached publicly.
- Do not strip query parameters that alter authorization or content; GET alone is not evidence of cacheability.
- Fragment caches (sidebar, mega-menu): only when the output dependencies are known; a locale-only key cannot safely cache user-specific widgets or cart state.
- Edge and browser caching: `Cache-Control: public, max-age, stale-while-revalidate` only for content that is identical for all audiences; `private` or `no-store` for user data.

## 5. Keys and invalidation

- Invalidate every dependent key on content, meta and term changes, deletion, status changes, imports, and relevant option changes. `save_post` alone is not a complete dependency graph (also `deleted_post`, `transition_post_status`, `set_object_terms`, `updated_post_meta`, `edited_term`, plus WooCommerce stock/price events).
- Concurrent recomputation can publish a value computed before a write after the invalidation ran. Use a version check at publish time or a short TTL plus authoritative source; verify with a test that writes during a fill.
- Generation IDs in the key (cache "namespaces") must be durable. Do not keep the only generation counter in an evictable cache: after eviction the generation resets (for example to 1) and still-existing entries of that old generation become valid again, serving stale data. `wp_cache_incr` fails on a missing key. Keep the generation in a durable store (an option or custom table) and read it with the value; do not invent a schema without project approval.
- Tag registries kept as read-modify-write lists lose registrations under concurrency and eviction; use authoritative dependency records, or a backend mechanism with tested atomicity.
- Group flush on every minor save defeats caching; flush on the narrowest scope.

## 6. Stampedes and locks

On expiry of a hot key many workers recompute simultaneously. Options: serve stale-while-revalidate with a background refresh (job inspected for acceptance, not fire-and-forget), probabilistic early refresh with jitter, a single-flight lock, or longer TTL with explicit invalidation. Jitter spreads expirations but does not solve invalidation or durable job acceptance.

A cross-process lock needs atomic acquisition (`wp_cache_add()` with a backend that implements atomic add, or a database `GET_LOCK`/unique row), an owner token, expiry, and atomic owner-checked release. Deleting a lock after it expired can delete a successor's lock; the generic WordPress cache API has no portable compare-and-delete. Follow the actual backend or database contract. Bound retries and total waiting time; on contention serve a documented stale result only where freshness and privacy allow, otherwise a retryable failure. Release on exceptions without releasing another owner's lock. Never wait recursively without a bound.

## 7. Counters

A cache increment is not a durable view/event counter. Even persistent counters lose events on eviction, restart or a read-then-delete flush. Choose explicitly approximate analytics with documented loss, or durable atomic increments (`UPDATE ... SET n = n + 1`) and acknowledged aggregation. Test two writers and a crash during flush. Do not call an untested cache buffer lossless.

## 8. Multisite and operations

- Object-cache keys are prefixed by blog ID for non-global groups; verify `switch_to_blog()` switches the prefix in the drop-in (`wp_cache_switch_to_blog()`), and that a plugin does not cache site-specific data in a global group.
- Redis/Memcached: record `maxmemory` and `maxmemory-policy` (an eviction policy like `allkeys-lru` explains disappearing entries), hit ratio, evictions, latency, and connection failures; a failed cache connection must degrade to origin, not to errors. Key prefix per environment to avoid staging flushing production.
- Record queue lag, cache hit ratio, error rate, p95 latency, memory and authoritative writes before and after a change.
- Cache warmers and preloaders can overload the origin or cache private pages as an authenticated user; run unauthenticated.

## 9. Review checks

Acceptance cases: missing and false values, eviction, two simultaneous fills, write during fill, lock owner expiry, refresh failure, private response warmed by another user, multisite switch, flush behavior without group support. Run against the real persistent backend where possible and record unexecuted persistent-cache cases separately. A pass in a request-local test environment does not prove behavior with Redis eviction or a CDN.

Sources: [WP_Object_Cache](https://developer.wordpress.org/reference/classes/wp_object_cache/) | [wp_cache_get](https://developer.wordpress.org/reference/functions/wp_cache_get/) | [wp_cache_flush_group](https://developer.wordpress.org/reference/functions/wp_cache_flush_group/) | [Transients](https://developer.wordpress.org/apis/transients/) | [Nonces](https://developer.wordpress.org/apis/security/nonces/) | [WP_Object_Cache::incr](https://developer.wordpress.org/reference/classes/wp_object_cache/incr/).
