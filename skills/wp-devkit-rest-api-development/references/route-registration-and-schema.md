# Route registration, argument schema and validation

Contents: registration rules; controller structure; how arguments are validated (core behavior); schema keywords and coercion; fields and meta; versioning and BC; failure symptoms; sources.

## Registration rules (verified against `register_rest_route()`)

- Call on or after `rest_api_init`. Earlier calls raise `_doing_it_wrong` (5.1+).
- Namespace is the first URL segment: `vendor/v1`; unique per plugin; no leading/trailing slash (notice since 5.4.2). Empty namespace or route returns `false`.
- Every endpoint definition needs `permission_callback`. Omitting it raises a notice since 5.5 (the route still registers, and core treats it as no restriction, so the notice marks a likely vulnerability). Public routes say so explicitly with `'permission_callback' => '__return_true'`.
- `args` entries must be arrays (notice since 6.1). A definition array containing `callback` is one endpoint; otherwise it is a list of endpoints (for example `GET` and `POST` sharing a path).
- `$override = false` merges with an existing route (later keys win); do not collide with core namespaces (`wp/v2`) except deliberately.
- Item routes use named captures: `'/events/(?P<id>[\d]+)'`. The regex only matches the shape; it never authorizes the object.
- Methods: use `WP_REST_Server::READABLE`, `CREATABLE`, `EDITABLE`, `DELETABLE` (these map to `GET`; `POST`; `POST, PUT, PATCH`; `DELETE`).
- Batch support is opt-in per route with `'allow_batch' => array( 'v1' => true )` (5.6); the batch endpoint is `POST /batch/v1`, default 25 sub-requests (`rest_get_max_batch_size` filter), status 207. Batch-friendly callbacks read only from `WP_REST_Request`, return data (no `echo`/`die`/`wp_send_json`), and are safe to call repeatedly. `GET` is not supported in batches.

## Minimal secure shape

```php
add_action( 'rest_api_init', static function () {
	register_rest_route( 'acme/v1', '/events/(?P<id>\d+)', array(
		array(
			'methods'             => WP_REST_Server::EDITABLE,
			'callback'            => 'acme_update_event',
			'permission_callback' => static function ( WP_REST_Request $request ) {
				return current_user_can( 'edit_post', (int) $request['id'] );
			},
			'args'                => array(
				'id'     => array( 'type' => 'integer', 'required' => true ),
				'status' => array(
					'type' => 'string',
					'enum' => array( 'draft', 'publish' ),
				),
				'title'  => array(
					'type'      => 'string',
					'minLength' => 1,
					'maxLength' => 200,
				),
			),
		),
	) );
} );
```

For anything beyond a couple of routes, extend `WP_REST_Controller`: it supplies `get_collection_params()` (page, per_page default 10 max 100, search, context), `get_context_param()`, `prepare_response_for_collection()`, field filtering and schema-driven arg generation through `get_endpoint_args_for_item_schema()`. Cache the generated item schema in `$this->schema` (supported since 5.3; core reported large collection speedups). A controller registers routes in `register_routes()` hooked to `rest_api_init`.

## How arguments are validated (confirmed in `WP_REST_Request`)

Order in dispatch: `has_valid_params()` then `sanitize_params()`.
1. `required => true` is checked first; a missing (`null`) value gives `400 rest_missing_callback_param`.
2. For each arg, an explicit `validate_callback` runs (true/false/`WP_Error`). Core does not add one implicitly here.
3. In `sanitize_params()`: if an arg has a `type` but no `sanitize_callback` key, core uses `rest_parse_request_arg`, which runs `rest_validate_request_arg` then `rest_sanitize_request_arg` against the schema (`400 rest_invalid_param` on failure).
4. If you set your own `sanitize_callback` (for example `absint`), the implicit schema validation is replaced. Add `'validate_callback' => 'rest_validate_request_arg'` to keep type/enum/range validation. Core's own `get_collection_params()` does exactly that.
5. A `validate_callback` of a bare PHP function such as `is_numeric` can emit warnings because core passes three arguments; wrap it in a closure.
6. `default` is applied only when the parameter is absent; `required` has no effect when a default exists.
7. Per-route `validate_callback` (endpoint level) runs after parameter validation and receives the whole request. Validation runs before permission callbacks (single and batch requests), so do not place side effects or data-dependent disclosures in validators.

Consequence: `sanitize_text_field` as the only `sanitize_callback` on an `integer` arg means no type check; `"abc"` reaches your callback sanitized to a string.

## Schema keywords that core implements (draft-04 subset, verified)

- `type` (single or list; evaluated in order). Omitting `type` raises a notice. Lists matter: `['boolean','string']` turns `"1"` into `true`, the reverse order keeps `"1"`.
- Strings: `minLength`, `maxLength`, `pattern` (not auto-anchored; no flags), `format` (`date-time`, `uri`, `email`, `ip`, `uuid`, `hex-color`).
- Numbers: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`.
- Arrays: `items`, `minItems`, `maxItems`, `uniqueItems`. Objects: `properties`, `additionalProperties`, `patternProperties`, `minProperties`, `maxProperties`. Combinators: `oneOf`, `anyOf` (give each subschema a `title` for readable errors).
- `enum` is used by core endpoints (for example `context`) and works for arg validation; it is not in the schema article's keyword list, so test it on your lowest supported version.
- Coercion of non-JSON input: integer accepts numeric strings with zero fraction; boolean accepts `0/1/"0"/"1"/"true"/"false"`; array accepts comma-separated strings; null needs a JSON body. Use `required` arrays on objects (v4 style) for nested objects; top-level `get_item_schema()` keeps v3-style per-property `required`.
- Request bodies: JSON bodies are parsed into params; `get_json_params()` for raw JSON, `get_body_params()` for form bodies, `get_file_params()` for uploads. `get_param()` / `$request['id']` return the first match in this order (confirmed in `get_parameter_order()`): JSON body, form body (POST/PUT/PATCH/DELETE), query string, URL captures, defaults. Filter: `rest_request_parameter_order`. A body or query `id` therefore shadows the URL `{id}`. The permission callback and the handler must read the identifier the same way (both `$request['id']`, or both `get_url_params()`); a mix is an object-authorization bypass candidate. Never read `$_GET`/`$_POST` in handlers.

## Fields, meta and responses of core types

- Adding fields to core types: `register_rest_field( $type, $name, array( 'get_callback' =>, 'update_callback' =>, 'schema' => ) )` on `rest_api_init`. Omit `update_callback` for read-only. Adding fields is safe; removing or changing core fields can break wp-admin, the block editor and clients. Offer opt-in parameters instead.
- Meta: `register_meta()`/`register_post_meta()` with `show_in_rest` (use the array form with a `schema` for arrays/objects) exposes meta through core endpoints and applies `auth_callback`/`sanitize_callback`. Protected (underscore) keys need an explicit `auth_callback`. A meta with `show_in_rest` true and a weak `auth_callback` is a write path.
- Do not expose private fields in `context=view`; use `context => array( 'edit' )` for editor-only data.
- `show_in_index` (default true) lists the route in the index; set false for internal routes, which is discoverability only and not protection.

## Versioning and compatibility

- `vendor/v1` becomes `v2` for breaking changes; keep v1 working through a deprecation window and add a `Deprecation`/documentation note; additive changes (new optional fields/params) stay in v1.
- Treat route names, status codes, error `code` strings, pagination headers and field names as public contract. Changing an error `code` breaks clients that branch on it.
- Clients detect the namespace through the index (`/wp-json/`, `namespaces`).

## Failure symptoms

| Symptom | Evidence | Fix |
|---|---|---|
| `400 rest_invalid_param` on valid-looking input | Compare `type`/`enum`/range with the payload; check coercion order for union types | Fix schema or caller; do not drop validation |
| Invalid type accepted | Custom `sanitize_callback` without `validate_callback` | Add `rest_validate_request_arg` |
| Notice `permission_callback` missing | Debug log on `rest_api_init` | Add real callback or explicit `__return_true` for public data |
| Route 404 | Namespace/regex mismatch, registered before `rest_api_init`, non-pretty permalinks (`?rest_route=/ns/v1/...`) | Fix registration, test both URL forms |
| Batch sub-request exits the response | Callback uses `wp_send_json` or `die` | Return `WP_REST_Response` |

## Sources

Research date: 2026-10-08.

- `register_rest_route`: https://developer.wordpress.org/reference/functions/register_rest_route/
- Adding custom endpoints: https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/
- Schema: https://developer.wordpress.org/rest-api/extending-the-rest-api/schema/
- Controller classes: https://developer.wordpress.org/rest-api/extending-the-rest-api/controller-classes/
- Modifying responses: https://developer.wordpress.org/rest-api/extending-the-rest-api/modifying-responses/
- Batch framework 5.6: https://make.wordpress.org/core/2020/11/20/rest-api-batch-framework-in-wordpress-5-6/
- Core source read (wordpress-develop trunk): `class-wp-rest-request.php` (`has_valid_params`, `sanitize_params`), `rest-api.php`, `class-wp-rest-controller.php`.
