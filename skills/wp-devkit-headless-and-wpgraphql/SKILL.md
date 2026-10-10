---
name: wp-devkit-headless-and-wpgraphql
description: "Build, debug or review decoupled WordPress with WPGraphQL: schema exposure, draft and preview access, authentication, query limits, Smart Cache and persisted queries, and webhook-driven frontend revalidation. Plain REST routes and ACF storage design belong to the sibling skills."
---

# Decoupled WordPress and WPGraphQL

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, rebuild or revalidation triggers, cache purges, credential creation, or sending queries that mutate data. Use the implementation path only when the request authorizes changes.

## Inputs to establish

WordPress, WPGraphQL (and WPGraphQL for ACF, Smart Cache) versions and settings (introspection, depth, batching, endpoint restriction, debug); frontend framework and version with its caching model; query documents or fragments; visibility policy for draft/private/password-protected/embargoed content; preview credential and token flow; cache layers (object, GraphQL, framework, CDN) and who purges them; hosting topology (CMS hostname, redirects of the theme front end); multisite and translation plugins.

Inspect project evidence first. State assumptions. Ask only what changes the decision.

## Route the task

| Symptom or goal | Read |
|---|---|
| What is exposed; custom type/field/connection; unbounded query, N+1, depth or batching; ACF fields in the schema | `references/wpgraphql-schema-and-limits.md` |
| Draft or private content leaks or is missing; preview broken; credential, CORS or nonce errors | `references/preview-and-authentication.md` |
| Stale pages, rebuild storms, webhook, Smart Cache, persisted queries, `revalidateTag` | `references/caching-revalidation-and-webhooks.md` |
| Schema drift between releases, contract tests, redirects of the WP front end, URLs, i18n, observability, rollout | `references/contract-testing-and-operations.md` |

Hand off: REST route design and permissions to `wp-devkit-rest-api-development`; ACF storage, keys and migrations to `wp-devkit-acf-and-content-modeling`; reachable XSS/authorization/SSRF defects to `wp-devkit-security-review`; slow queries and object cache tuning to `wp-devkit-performance-review`; pipeline and deploy mechanics to `wp-devkit-ci-cd-and-release-engineering`; Gutenberg block output to `wp-devkit-block-development`.

## Code Review Workflow

1. Follow one rendered route back to its query document, resolver and content model. Keep the schema names consumers already use.
2. Compare anonymous, low-privilege and preview-credential reads of published, draft, private, password-protected, scheduled and trashed content. A hidden frontend field does not protect an origin resolver.
3. Trace the preview path: link generation, secret/token validation, redirect target, credential location, `asPreview` use and cache partition.
4. Check endpoint settings (introspection, depth, batch limit, connection maximum, debug mode, endpoint restriction) against the exposure of the site. Measure the cost of a worst-case query on staging before calling it a risk.
5. For caching, name the freshness owner of each layer and the event that invalidates it; map content changes (publish, rename, unpublish, scheduled, term, menu) to affected routes.
6. Check webhook authentication (signature over raw body plus timestamp), replay handling, retries and visibility of failures.
7. Report the visibility and freshness boundary with the evidence gathered. Do not trigger rebuilds, purges or revalidation during review.

Insufficient evidence is a valid outcome (no staging, no frontend access, unknown CDN behavior): state what is unverified and the check that settles it.

## Implementation workflow

1. Define the behavior, the layer being changed (schema, auth, cache, frontend) and the supported versions.
2. Make schema changes additive; deprecate before removal; update query documents and the schema snapshot together.
3. Put credentials in server-only configuration; never in client bundles.
4. Implement, then run the acceptance checks; record commands and exit status; report unavailable checks as unexecuted.
5. Deployment, cache purges and live revalidation are separate task scopes.

## Search Patterns for Quick Detection

Read-only leads from the project root; a match is a candidate, not a finding. Exit 0 = match, 1 = none, 2 = error.

```sh
rg -n -g '*.php' -g '!vendor' -g '!node_modules' -e 'register_graphql_|graphql_register_types|show_in_graphql|graphql_single_name|graphql_connection_max_query_amount|graphql_query_depth_max|GRAPHQL_DEBUG' .
rg -n -g '*.{ts,tsx,js,jsx,mjs,php}' -g '!vendor' -g '!node_modules' -e 'asPreview|draftMode|preview_post_link|NEXT_PUBLIC_[A-Z_]*(SECRET|TOKEN|PASSWORD)|Authorization' .
rg -n -g '*.{ts,tsx,js,jsx,mjs,php}' -g '!vendor' -g '!node_modules' -e 'revalidateTag|revalidatePath|graphql_purge|X-GraphQL-Keys|hash_hmac|timingSafeEqual|wp_remote_post' .
rg -n -g '*.php' -g '!vendor' -g '!node_modules' -e "posts_per_page'? *=> *-1|get_post_meta|get_user_by\(|get_post\(" .
```

No match proves nothing: schema can come from plugins, UI settings or generated code, and secrets can be injected at build time.

## Acceptance checks

- Anonymous vs credentialed queries for each visibility state return the expected data and no leakage (title, excerpt, existence).
- `wp graphql generate-static-schema` diff is reviewed; frontend queries validate against it.
- Worst-case query (aliases, nested connections to the depth limit, `first: 100`) stays within the agreed time and query count on staging; query count is flat when node count grows.
- Preview then anonymous request for the same URL returns published content.
- Webhook: wrong signature, stale timestamp and replay are rejected or harmless; failed delivery is visible and retried; publish/rename/unpublish update the right routes.
- Static checks as configured (phpcs, PHPStan, TypeScript, lint).

A pass proves the exercised states, caches and versions. It does not prove behavior behind a different CDN rule, other roles or locales, high load, or security of the frontend host.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: severity per the contract, file:line, actor, trigger, reachable path, impact, confidence, minimal fix, regression test. Candidates and unverified items in a separate list.

Implementation: changed boundaries, schema or contract changes (additive or breaking), commands run with exit status, checks not run, residual risk, rollback.

## References

- `references/wpgraphql-schema-and-limits.md`: read for exposure, registration, authorization model, query limits and resolver cost.
- `references/preview-and-authentication.md`: read for auth methods, preview flow, CORS and boundary tests.
- `references/caching-revalidation-and-webhooks.md`: read for cache layers, Smart Cache, route mapping, webhook sender/receiver, Next.js revalidation.
- `references/contract-testing-and-operations.md`: read for schema snapshots, frontend coupling, WP front-end redirects, observability and rollout.
