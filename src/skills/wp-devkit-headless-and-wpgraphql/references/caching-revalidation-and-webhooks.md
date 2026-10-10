# Caching layers, invalidation, revalidation webhooks

Contents: layers and ownership; WPGraphQL Smart Cache; persisted queries; mapping content changes to routes; webhook sender and receiver; Next.js revalidation APIs; failure modes; tests; false positives.

Research date: 2026-10-08. Sources: WPGraphQL Smart Cache docs in the monorepo (`plugins/wp-graphql-smart-cache/docs`: cache-invalidation, on-demand-revalidation, persisted-queries, network-cache, object-cache), [Next.js revalidateTag](https://nextjs.org/docs/app/api-reference/functions/revalidateTag), [Next.js draftMode](https://nextjs.org/docs/app/api-reference/functions/draft-mode), WordPress developer reference for `transition_post_status`, `wp_schedule_single_event`, `hash_hmac`.

## Name the freshness owner for each layer

1. WordPress/object cache (persistent object cache, transients)
2. GraphQL response cache (Smart Cache object cache or network cache)
3. Frontend data cache (framework fetch/data cache)
4. Rendered page cache (ISR/static output, full-route cache)
5. CDN/edge cache and browser cache

For each layer record: TTL, key (what partitions it: query hash, variables, auth state, preview state, locale), invalidation event, and who can purge. A stale page is debugged by walking the layers from the browser back to WordPress with headers (`Age`, `Cache-Control`, `X-GraphQL-Keys`, framework cache headers). Using `no-store` everywhere to avoid staleness is a design smell, not a strategy.

## WPGraphQL Smart Cache

Facts from the plugin docs (monorepo `main`):

- Object cache and network cache for GraphQL responses; network cache works best with GET requests on a supported host. Authenticated requests should not share public caches; verify that your host or CDN keys on or bypasses `Authorization` and cookies.
- Responses are tagged by analysis of the request: operation name, query ID (hash of the document), list types requested, and individual nodes resolved. Tags travel in the `X-GraphQL-Keys` header when type tracking ("query analyzer") is enabled (forced on in debug mode).
- Purge events: publish (not previously public to public) purges `list:<type>`; update of a public node purges the node ID and `skipped:<type>`; delete or unpublish purges the node and `skipped:<type>`. Drafts, new draft posts and new users with no published content do not purge. Terms, users-as-authors, media, comments, menus and (WPGraphQL 2.18+) settings groups are tracked; permalink options trigger a full purge.
- `skipped:<type>`: when too many nodes are returned the key header is truncated to a type-level key, so such queries are purged on any change of that type. Large list queries therefore invalidate often; shrink or paginate them.
- Settings queries before WPGraphQL 2.18 do not purge on change; use a per-document max-age.
- Action `do_action( 'graphql_purge', $key, $event, $graphql_endpoint )` fires for each purge (the third argument is the GraphQL endpoint URL without its scheme, per `Cache/Invalidation.php`). Key shapes: a Relay global ID (base64 of `type:databaseId`), `list:<type>`, `skipped:<type>`, `graphql:Query` (purge all). One editor action can fire several. Batch them per request.
- Persisted queries are stored in a private `graphql_document` post type with allow/deny modes ("Public", "Allow only specific queries", "Deny specific queries"), alias names (query IDs), and a per-document max-age. They reduce upload size and let you lock a public endpoint to known operations. They do not fix poor schema design, expensive resolvers, missing pagination or preview cache separation.
- `wp graphql smart-cache documents audit|purge` manages stored documents. `audit` is the inspection command; treat `purge` (flags `--include-curated`, `--dry-run`, `--yes` per the persisted-queries doc) as destructive and never run it in review, even with `--dry-run` unless the task authorizes it.

## Map content changes to routes (the part most projects get wrong)

For each content change decide which URLs are affected. Minimum list:

| Change | Affected routes |
|---|---|
| Publish new post | Post URL, home/index lists, category/tag/author archives, sitemap, RSS, search index, related-content blocks |
| Edit published post | Post URL and any list that embeds its title/excerpt/image |
| Slug or parent change | Old URL (now redirect or 404), new URL, parents' listings, internal links elsewhere (cannot be fully known: use redirects) |
| Unpublish, trash, delete | The URL (now 404/410), lists, archives, sitemap |
| Scheduled post goes live | Same as publish, triggered by `transition_post_status` from the cron run, not by an editor |
| Term rename or reassignment | Term archive, posts in the term, navigation, facets |
| Menu, widget area, site option change | Everything that renders it; often a full-layout revalidation |
| Media replaced | Pages embedding the image URL and CDN image cache |

Pre-existing slug-only invalidation misses renames: send both the previous and the current path (capture the old permalink in `pre_post_update`/before the change).

## Webhook sender (WordPress side)

```php
add_action( 'graphql_purge', static function ( string $key ) {
	$GLOBALS['site_purge_keys'][ $key ] = true;
	if ( ! has_action( 'shutdown', 'site_flush_purges' ) ) {
		add_action( 'shutdown', 'site_flush_purges', 99 );
	}
}, 10, 1 );

function site_flush_purges(): void {
	$keys = array_keys( $GLOBALS['site_purge_keys'] ?? array() );
	if ( ! $keys ) { return; }
	// Defer delivery out of the editor's request; a transient or table-backed queue is also fine.
	wp_schedule_single_event( time(), 'site_deliver_revalidation', array( $keys ) );
}

add_action( 'site_deliver_revalidation', static function ( array $keys ) {
	$body      = wp_json_encode( array( 'keys' => $keys ) );
	$timestamp = (string) time();
	$signature = hash_hmac( 'sha256', $timestamp . '.' . $body, SITE_REVALIDATE_SECRET );
	$response  = wp_remote_post( SITE_REVALIDATE_URL, array(
		'timeout'     => 5,
		'redirection' => 0,
		'headers'     => array(
			'Content-Type'       => 'application/json',
			'X-Site-Timestamp'   => $timestamp,
			'X-Site-Signature'   => $signature,
		),
		'body'        => $body,
	) );
	$code = is_wp_error( $response ) ? 0 : (int) wp_remote_retrieve_response_code( $response );
	if ( $code < 200 || $code >= 300 ) {
		// Reschedule with backoff and a maximum attempt count; log key count and status, never the secret.
	}
} );
```

Design rules: sign over timestamp plus raw body; set a tolerance window on the receiver; make the receiver idempotent; use a secret from the environment/constants, not the options table; do not follow redirects; do not send the payload through a URL query string (logged by proxies); never block the editor's save on the frontend. Where Action Scheduler is present, `as_enqueue_async_action()` with a small group gives visible failures and retries, the single-event cron route does not.

## Receiver (frontend side, Next.js route handler)

```ts
import { createHmac, timingSafeEqual } from 'node:crypto';
import { revalidatePath, revalidateTag } from 'next/cache';

export async function POST(request: Request) {
  const raw = await request.text();
  const timestamp = request.headers.get('x-site-timestamp') ?? '';
  const given = request.headers.get('x-site-signature') ?? '';
  const expected = createHmac('sha256', process.env.REVALIDATE_SECRET!).update(`${timestamp}.${raw}`).digest('hex');
  const ok = given.length === expected.length && timingSafeEqual(Buffer.from(given), Buffer.from(expected));
  const fresh = Math.abs(Date.now() / 1000 - Number(timestamp)) < 300;
  if (!ok || !fresh) return new Response('Unauthorized', { status: 401 });

  const { keys } = JSON.parse(raw) as { keys: string[] };
  for (const key of keys.slice(0, 200)) {
    revalidateTag(`wp:${key}`, 'max');          // stale-while-revalidate
  }
  return Response.json({ accepted: keys.length });
}
```

- Since Next.js 16, `revalidateTag( tag, profile )` takes a second argument (check the current docs online); `'max'` gives stale-while-revalidate for up to a year. The one-argument form is deprecated and behaves like `{ expire: 0 }`. For a webhook (not a Server Action) `updateTag` is not available; use `revalidateTag( tag, { expire: 0 } )` when stale content must never be served. Tags must be 256 characters or fewer and must have been attached to the cached data (`fetch(..., { next: { tags } })` or `cacheTag` with `'use cache'`), otherwise revalidation does nothing. Revalidation is triggered by the next request, not by the call.
- Older Next.js versions used `revalidateTag( tag )` and `revalidatePath( path )` (one argument): read the installed version's docs before copying.
- Tagging convention: tag each fetch with the same Relay IDs and `list:<type>` keys that Smart Cache emits so the mapping is mechanical.
- Return 2xx only after the revalidation calls were accepted. Count and log accepted/rejected events.

## Failure modes and symptoms

| Symptom | Likely cause | Check |
|---|---|---|
| Content updates in WP, stale on site | Webhook not firing (draft transitions, REST saves skipped), receiver rejects signature, tag mismatch, CDN caching the HTML | WP delivery log; receiver log; compare tags; `curl -I` headers |
| Storm of rebuilds | One webhook per event, full rebuild trigger | Batch on `shutdown`; coalesce within a time window; prefer targeted revalidation |
| New post missing from list | Only the post URL revalidated, not `list:post` or archive tags | Event keys received; list route tags |
| Renamed post shows old URL | Slug-only invalidation | Old and new paths in the payload |
| Preview data in public cache | Preview request shares cache key | Cache partition tests in [preview-and-authentication.md](preview-and-authentication.md) |
| Replayed old webhook reverts content | No idempotency or ordering | Webhook revalidates (re-fetches) rather than carrying content |

Prefer webhooks that say "these keys changed" and make the frontend re-fetch from WPGraphQL, over webhooks that carry the new content; a re-fetch cannot apply stale data out of order.

## Tests that prove it

- Publish, edit, rename slug, unpublish and delete one post; assert the affected pages change within an agreed time and unrelated pages do not rebuild.
- Replay the same signed webhook twice and a webhook older than the tolerance window: second is harmless, third is rejected.
- Break the receiver (503) and confirm the sender logs and retries, and that an operator can replay missed keys.
- Scheduled publish via WP-Cron triggers the same path.

A pass proves the exercised events and routes. It does not prove behavior under hosting-level page caches, third-party plugins that write content without hooks (direct SQL imports), or high-volume bursts.

## Looks wrong but is fine

- Time-based revalidation (ISR interval) as a safety net next to on-demand revalidation.
- A coarse `skipped:<type>` purge for a rarely edited type.
- Full rebuild for global layout changes (menus, theme options) that touch every page.
- Non-blocking `wp_remote_post` (blocking false) for a best-effort notification when a reconciler or time-based safety net exists.
