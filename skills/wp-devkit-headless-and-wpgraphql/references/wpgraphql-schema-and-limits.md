# WPGraphQL schema design, exposure and query limits

Contents: what is exposed by default; registering types, fields and connections; visibility and authorization; ACF data; query cost controls and their gaps; N+1 and resolver cost; debug and tracing; CLI; false positives.

Research date: 2026-10-08. Sources: [WPGraphQL security](https://www.wpgraphql.com/docs/security), [authentication and authorization](https://www.wpgraphql.com/docs/authentication-and-authorization), [custom post types](https://www.wpgraphql.com/docs/custom-post-types), [debugging](https://www.wpgraphql.com/docs/debugging), [WPGraphQL vs REST (DataLoader)](https://www.wpgraphql.com/docs/wpgraphql-vs-wp-rest-api), and the WPGraphQL monorepo source (`wp-graphql/wp-graphql`, `main`; requires WordPress 6.0+, PHP 7.4+). Confirm behavior against the installed version; defaults have changed across releases.

## What is exposed

- Core types (posts, pages, media, terms, users, comments, menus, settings) are in the schema. Custom post types and taxonomies are exposed only when registered with `show_in_graphql => true` and a `graphql_single_name` (camel case, starts with a letter); `graphql_plural_name` is optional. Existing types from other plugins can be opted in through the `register_post_type_args` / `register_taxonomy_args` filters.
- Introspection is limited to authenticated requests on production/staging by default; it is on by default only in `local`/`development` environments, or via the "Enable Public Introspection" setting. Public introspection is not a vulnerability by itself, but it widens enumeration of the content model.
- The endpoint defaults to `/graphql` (setting `graphql_endpoint`). "Restrict Endpoint to Authenticated Users" (default off) rejects anonymous operations. A site whose content is entirely public does not need it; a staging, intranet or paywalled site does.
- WPGraphQL does not expose the REST API's data differences automatically: private post types, drafts and users without published content are hidden through the Model layer, not through your frontend.

## Authorization model

- Model layer: each node (`Post`, `User`, `Comment`, ...) decides per request whether it is private, based on status, ownership and capabilities. A private node resolves as `null`; restricted fields resolve as `null` with an error. Revisions inherit access from the parent. Attachments with `inherit` status inherit from the parent post; unattached media is treated as public (override with the `graphql_pre_model_data_is_private` filter).
- Do not rely on a frontend hiding fields. A field you register is reachable by any client that can send the query.
- I found no declarative per-field `auth` option in the current WPGraphQL source. Enforce authorization inside the resolver (`current_user_can( 'edit_post', $id )`) or by not registering the field for anonymous schemas.
- Mutations check capabilities before running; custom mutations must do the same and verify object ownership, not only a generic capability.
- Authentication details are in [preview-and-authentication.md](preview-and-authentication.md).

## Registering schema

```php
add_action( 'graphql_register_types', static function () {
	register_graphql_field( 'Event', 'internalNotes', array(
		'type'        => 'String',
		'description' => __( 'Editor-only notes.', 'site-api' ),
		'resolve'     => static function ( $source ) {
			if ( ! current_user_can( 'edit_post', (int) $source->databaseId ) ) {
				return null;
			}
			return get_post_meta( (int) $source->databaseId, 'internal_notes', true );
		},
	) );

	register_graphql_connection( array(
		'fromType'      => 'RootQuery',
		'toType'        => 'Event',
		'fromFieldName' => 'upcomingEvents',
		'resolve'       => static function ( $source, array $args, $context, $info ) {
			$resolver = new \WPGraphQL\Data\Connection\PostObjectConnectionResolver( $source, $args, $context, $info, 'event' );
			$resolver->set_query_arg( 'meta_key', 'event_start' );
			$resolver->set_query_arg( 'orderby', 'meta_value' );
			$resolver->set_query_arg( 'order', 'ASC' );
			return $resolver->get_connection();
		},
	) );
} );
```

- Use a connection resolver, not a hand-built `WP_Query` with `posts_per_page => -1`. The resolver applies cursor pagination, the `first/last` bounds and the maximum amount.
- Register in `graphql_register_types`. Registering earlier breaks type resolution. `register_graphql_object_type`, `register_graphql_mutation`, `register_graphql_enum` follow the same pattern.
- Keep the contract domain-oriented: expose `heroImage` as a media node connection rather than `heroImageUrl` read from raw meta; use enums for fixed vocabularies; add nullability deliberately (null should mean "absent", not "schema drift").
- Name changes are breaking changes for every deployed frontend. Deprecate with `deprecationReason` in the field config and keep the old field one release.
- Meta-as-API (`get_post_meta` in the resolver) is acceptable for a single node field; inside a list resolver it becomes N+1 unless meta is primed (see below).

## ACF-backed data

Use the separate WPGraphQL for ACF plugin (monorepo `plugins/wp-graphql-acf`; WordPress 6.1+, PHP 7.4+; ACF Free/PRO and ACF Extended supported). Field groups, post types and taxonomies are opted in through ACF admin settings, or through the keys in PHP/JSON definitions. Consequences: the GraphQL field name is derived from the ACF field name or a GraphQL-specific name; renaming an ACF field renames a GraphQL field (breaking change); a group exposed to GraphQL exposes all its fields. The `wp-devkit-acf-and-content-modeling` skill covers the storage side (schema authority, keys, return formats).

## Query cost controls (and what they do not do)

| Control | Default and facts |
|---|---|
| Max items per connection | 100 per page; filter `graphql_connection_max_query_amount` (can lower or raise; raising is the risk) |
| Query depth limiting | Setting `query_depth_enabled`; max depth default 15; filter `graphql_query_depth_max` (return 0 for no limit). The code default is off; activation of a new install saves it as on (see `WPGraphQL.php` and `QueryDepth.php`), so sites that pre-date the setting may still have it off. Introspection-only operations are exempt. |
| Batching | Enabled by default; `batch_limit` default 10 operations per request; filter `graphql_is_batch_queries_enabled` |
| Introspection | Authenticated-only outside local/development |
| Complexity / cost analysis | Not available (the upstream feature request [#3922](https://github.com/wp-graphql/wp-graphql/issues/3922), "query complexity (cost analysis) limiting", was still open on 2026-10-08). Depth limiting does not stop wide queries or alias repetition (`a: posts{...} b: posts{...}`) |
| Rate limiting | Not provided; use the edge (CDN/WAF) or a persisted-query allow list |

Practical review: send the largest query the frontend actually needs and measure; then a hostile one (aliases x 50, nested connections to the depth limit, `first: 100` at each level) against staging and compare time and DB queries. An allow-list of persisted queries (Smart Cache "Allow only specific queries") is the strongest control for a public endpoint whose consumers are known.

## Resolver cost

- WPGraphQL batches related-object loading with DataLoaders (for example a list of posts and their authors becomes one posts query and one user query). Resolvers that bypass loaders (`get_post( $id )` or `get_user_by()` per node) lose that.
- Prime caches for list resolvers: `update_meta_cache( 'post', $ids )`, `_prime_post_caches()`, `update_object_term_cache()`; or use the loader (`$context->get_loader( 'post' )->load_deferred( $id )`).
- Enable "GraphQL Query Logs" and "Tracing" temporarily on staging: query logs add SQL, timing and stack to `extensions.queries`, tracing adds per-field durations. Turn both off afterwards.
- Count queries for 1, 10 and 100 nodes: a flat count means batching works; a linear count is N+1.

## Debug mode

`GRAPHQL_DEBUG` (constant) or the Debug Mode setting returns more descriptive errors and forces public introspection and type tracking on. Treat it as a development tool: with it on, errors can expose implementation details. Do not enable it in production; if a production incident requires it, enable briefly and restrict by IP or role at the edge.

## CLI and snapshots

`wp graphql generate-static-schema [--output=<file>]` writes the SDL schema. Commit it (or its hash) in the frontend repo or CI to detect unintended schema changes between plugin updates or field edits.

## Looks wrong but is fine

- Public read-only queries for published content with no authentication.
- `first: 100` with a persisted/allow-listed query whose cost was measured.
- `get_post_meta` in a resolver for a single-node field.
- `Access-Control-Allow-Origin: *` on the GraphQL response: cookie credentials are not sent cross-origin, and requests with a nonce or Authorization header are explicit.
- Introspection enabled in `local` environments.
