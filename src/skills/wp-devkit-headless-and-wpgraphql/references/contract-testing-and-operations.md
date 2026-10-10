# Contract tests, frontend coupling and operations

Contents: schema and query contract; frontend coupling checks; the WordPress front end in a headless setup; URLs, media and SEO; multisite and i18n; observability; rollout and rollback.

Research date: 2026-10-08. Sources: WPGraphQL source (`src/CLI/Commands.php`, `Request.php`, settings), [WPGraphQL security](https://www.wpgraphql.com/docs/security), [WP REST authentication](https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/), WordPress core `template_redirect` / `rest_api_default_filters` behavior (core source, master).

## Schema and query contract

- Pin versions: WordPress, WPGraphQL, WPGraphQL for ACF, Smart Cache, ACF/SCF, frontend GraphQL client. Upgrade them as a set on staging.
- Snapshot the schema: `wp graphql generate-static-schema --output=schema.graphql` and commit or diff it in CI. A plugin update or field rename that changes the SDL fails the build until the frontend is updated.
- Validate every frontend query document against the snapshot (GraphQL codegen or a validator such as `graphql-inspector`/`graphql-eslint`; tool choice is the project's). Persisted/allow-listed documents should be generated from the same files.
- Contract cases per operation: published node, missing node (null, not a 500), draft/private/password-protected node as anonymous, nullable fields absent, connection with zero, one and more than `first` results, pagination cursors (`pageInfo.hasNextPage`, `endCursor`), and an unexpected mutation error.
- Treat GraphQL errors as data: a response can be HTTP 200 with `errors` and partial `data`. The frontend must not render a half-null page as success without checking `errors`.

## Frontend coupling checks

- Fragments per content type instead of repeated field lists; one place changes when the model changes.
- No hard-coded database IDs for content that exists per environment; use slugs/URIs or settings.
- Nullable fields are variants to model deliberately, not control flow. If a field is null because of authorization, the UI must not tell the user the content does not exist unless that is intended.
- Server-only credentials are not in client bundles or public environment variables; search the build output for them.
- Image URLs, sizes and `srcset` come from the schema (`mediaDetails`, `sourceUrl`, `srcSet`), not guessed paths.
- Do not fetch inside client components with the origin credential; proxy through the frontend server.

## The WordPress front end

Many headless sites keep WordPress at a CMS hostname and redirect public theme requests to the frontend. Check what such a redirect (usually on `template_redirect`) leaves intact: `wp-admin`, `wp-login.php`, `/wp-json/`, `/graphql`, `wp-cron.php`, `admin-ajax.php`, `xmlrpc.php` (usually disable), feeds, sitemaps, `robots.txt`, file uploads and password-protected-post forms. A blanket redirect that catches `/graphql` or cron breaks the system; one that catches nothing leaves a duplicate-content copy indexable by search engines. Confirm with `curl -I` for each path from a clean client. Set `noindex` on the CMS hostname if the theme front end stays reachable.

Also confirm the `home` and `siteurl` options: editor-facing links (permalinks in the editor, preview, "View post") should resolve to the frontend host, while REST/GraphQL absolute URLs must stay on the CMS host. Mismatches show up as broken previews and wrong `uri` values in GraphQL responses.

## URLs, media, SEO

- Canonical, `og:` and sitemap data come from one owner (frontend or an SEO plugin exposed through the schema). Two owners disagree after a slug change.
- Redirects for renamed or removed content need a source of truth (a redirect table in WordPress exposed to the frontend, or framework redirects generated at build). Webhook payloads should include the previous path.
- Media URLs: decide whether the frontend serves originals from WordPress, a CDN, or an image optimizer; hotlink and cache headers differ.

## Multisite and i18n

- Each site has its own GraphQL endpoint path context (`/graphql` under the site's URL); caches and webhooks are per site. Include the site identifier in tags and signatures.
- Translation plugins add language arguments and fields through their own GraphQL extensions. Cache keys and preview routes must include locale; test a draft translation preview.
- Locale-specific slugs break slug-only routing.

## Observability

- Log per request: operation name, query ID, duration, status, authenticated or not (never tokens or variables with personal data). Enable query logs/tracing only on staging.
- Track GraphQL error rate by type, p95 duration of the top operations, cache hit ratio per layer, webhook success ratio and lag between publish and visible change (synthetic canary post).
- Alert on failed webhooks and on a sustained rise in `skipped:` purges (queries too large).

## Rollout and rollback

- Introduce schema changes additively: new field, migrate frontend, deprecate old field (`deprecationReason`), remove later.
- Deploy WordPress-side changes first when additive, frontend first when removing.
- Rollback for a bad frontend deploy is the host's previous build; for a bad schema change it is restoring the previous plugin/field definitions (keep the previous release artifact). Cached responses may persist: purge by key after rollback.

## Looks wrong but is fine

- HTTP 200 with a GraphQL `errors` array for a non-fatal field error that the frontend handles.
- Separate preview and public GraphQL clients/URLs in the frontend.
- Redirecting only public theme URLs from the CMS hostname while leaving admin, API and cron paths intact.
