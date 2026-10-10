# Authentication, draft access and preview flows

Contents: choose the authentication method; request identity rules; the preview flow end to end; Next.js Draft Mode notes; CORS; failure symptoms; tests; false positives.

Researched 2026-10-08. Sources: [WPGraphQL authentication and authorization](https://www.wpgraphql.com/docs/authentication-and-authorization), [WPGraphQL security](https://www.wpgraphql.com/docs/security), [REST API authentication](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/), [preview_post_link](https://developer.wordpress.org/reference/hooks/preview_post_link/), [rest_allowed_cors_headers](https://developer.wordpress.org/reference/hooks/rest_allowed_cors_headers/), WordPress core source (`user.php`, `rest-api.php`), WPGraphQL source (`RootQuery.php`, `Model/Post.php`), [Next.js draftMode](https://nextjs.org/docs/app/api-reference/functions/draft-mode) (docs v16.4.0).

## Choose the authentication method

| Caller | Method | Notes |
|---|---|---|
| Logged-in editor in wp-admin or same-origin | Cookie plus nonce (`X-WP-Nonce` header or `_wpnonce` param, action `wp_rest`) | Without a nonce WordPress treats the request as unauthenticated (user 0; REST docs). In WPGraphQL a missing nonce downgrades to guest (`viewer` null); an invalid nonce returns HTTP 403 by default; the check accepts a `wp_graphql` or `wp_rest` nonce and, per source comments, moved into `Router.php` in 2.5.4/2.6.0, so check the installed version |
| Server-side frontend (Next.js server, build, edge function) reading drafts | Application Password over HTTPS, or a JWT/headless-login plugin | Core application passwords exist since 5.6; available only over SSL or when `WP_ENVIRONMENT_TYPE` is `local` (`wp_is_application_passwords_available` is filterable). Use a dedicated low-privilege user and keep the credential server-only |
| Browser JS on another origin | No credentials for public content. For per-user data use a token flow built for it | Never ship an application password, JWT secret or webhook secret in client bundles or `NEXT_PUBLIC_*` variables |
| CI/CD, import jobs | Application Password or WP-CLI | Scope the user capabilities to the job |

Details:

- Create a distinct preview user with the minimum capabilities needed (for example an Editor role limited to previewing). A shared administrator application password in the frontend is a privilege escalation path if the frontend server is compromised.
- Application passwords are revocable per credential; document the rotation and failure behavior.
- Header-based tokens (`Authorization`) do not use cookies, so CSRF nonces are not needed for them; cookie requests do need nonces.

## Preview flow end to end

1. Editor clicks Preview. WordPress builds the link with `get_preview_post_link()`, filterable with `preview_post_link( $link, $post )` (args since 4.0). Point it at the frontend's preview route and include only an opaque request: post ID (database ID) and post type, plus a short-lived signed token or a one-time secret known to both sides.
2. The frontend route validates the secret/token in constant time, enters draft/preview mode for this browser session, and redirects only to a path built server-side from the resolved content (never to a `redirect`/`slug` value the caller supplied).
3. The frontend fetches the draft with credentials held on the server: in WPGraphQL, `post(id: $id, idType: DATABASE_ID, asPreview: true)` or `nodeByUri(uri: $uri)` with the preview indicator. When `asPreview` is true the preview revision is returned; if no preview exists or the requester lacks capability, nothing is returned (documented in the schema). Anonymous requests never receive preview data.
4. Preview responses must bypass every shared cache (framework data cache, CDN, persisted-query/object caches) or be keyed so the preview identity partitions them. A preview followed by an anonymous request must return the published version.
5. Exit preview explicitly (route that disables draft mode) and expire the cookie/session.

```ts
// Next.js (App Router, v15+): app/api/preview/route.ts
import { draftMode } from 'next/headers';
import { timingSafeEqual } from 'node:crypto';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const secret = Buffer.from(searchParams.get('secret') ?? '');
  const expected = Buffer.from(process.env.PREVIEW_SECRET ?? '');
  const id = Number(searchParams.get('id'));
  if (!expected.length || secret.length !== expected.length || !timingSafeEqual(secret, expected) || !Number.isInteger(id)) {
    return new Response('Invalid preview request', { status: 401 });
  }
  const path = await resolvePreviewPath(id); // server-side GraphQL call with the preview credential
  if (!path) return new Response('Not found', { status: 404 });
  (await draftMode()).enable();
  return Response.redirect(new URL(path, request.url), 307);
}
```

Notes on that snippet: `draftMode()` is async since Next 15 (`await draftMode()`); `enable()` sets the `__prerender_bypass` cookie, whose value changes with each `next build`; a static `secret` in a URL is weaker than a signed, expiring token, so prefer a token that encodes post ID and expiry (HMAC) if previews can be shared; do not log URLs containing the secret. `resolvePreviewPath` is a placeholder for your own function.

## CORS and cross-origin behavior

- WPGraphQL responds with `Access-Control-Allow-Origin: *` and no `Allow-Credentials`, so browsers do not attach cookies to cross-origin script requests (WPGraphQL security docs).
- Core REST API (`rest_send_cors_headers` in `rest-api.php`) reflects the request `Origin` and sends `Access-Control-Allow-Credentials: true`, with `Vary: Origin`. Cookie authentication still requires the nonce, which a foreign origin cannot obtain, but the reflective policy is why REST write endpoints must never trust origin. To restrict origins, replace the core handler on the `rest_pre_serve_request` filter with your own allow-list (test that it still answers `OPTIONS`) or enforce it at the edge; `rest_allowed_cors_headers` (5.5+; request arg added 6.3) controls allowed request headers only.
- A frontend that proxies GraphQL through its own server avoids exposing the origin credentials and CORS surface to browsers.

## Failure symptoms

| Symptom | Likely cause | Confirm |
|---|---|---|
| Preview shows published content | `asPreview` missing, request unauthenticated, or cached response | Run the same query with the credential and with `curl` anonymously; compare; check cache headers |
| Preview works for admins only | Credential user lacks capability to read the revision | Test with the actual preview user and a draft they cannot edit |
| 403 "Cookie nonce is invalid" | Stale nonce on a cookie-authenticated GraphQL request | Refresh nonce; for server-side use switch to Authorization header |
| Preview link opens wp-admin or 404 | `preview_post_link` returns home URL path mismatch (`home` vs `siteurl`), permalink structure | Inspect the filtered link for that post type |
| Editors see old preview after editing | Persisted/object cache serving the preview query | Check `X-GraphQL-Keys`/cache headers; bypass for preview |
| Draft title leaks in anonymous 404 page | Frontend error rendering the fetched draft | Test with anonymous request; inspect responses |

## Tests that prove the boundary

- Anonymous request for a draft, private, password-protected and trashed node returns null/denied with no title or excerpt leakage.
- Preview-credential request returns the draft; the same query without the credential does not.
- After a preview request, an anonymous request for the same URL returns the published content (cache partition).
- Preview route with a wrong, empty and expired secret returns 401 and sets no cookie; a `redirect`/`slug` parameter cannot send the editor to another origin.
- Rotating the preview credential breaks previews visibly (clear error to the editor), not silently.

A pass proves the tested content states and caches. It does not prove other shared layers (a CDN rule added later), other roles, or security of the frontend host.

## Looks wrong but is fine

- Public GraphQL queries returning published content to anonymous users.
- `Access-Control-Allow-Origin: *` on public GraphQL.
- Application passwords used from a server-side frontend with a least-privilege user over HTTPS.
- A preview route that redirects only to a server-resolved internal path.
