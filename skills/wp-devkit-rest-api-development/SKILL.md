---
name: wp-devkit-rest-api-development
description: Build, debug or review WordPress REST routes, argument schemas, authentication, object permissions, responses and pagination. Use for 401/403/400 responses, nonce or Application Password problems, missing permission_callback, collections and caching; not admin screens.
---

# REST contracts and request boundaries

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Inputs and scope

Namespace and route, HTTP method, caller identity and authentication model (cookie, Application Password, custom token, webhook), request/response example, target WordPress version, protected-object policy, consumers (block editor, theme JS, mobile, partner), CDN/page-cache in front of `/wp-json/`.

Inspect project evidence before asking. State material assumptions. Ask only what changes the decision or execution boundary. Follow the existing public contract: route names, fields, status codes and error `code` strings are API.

## Boundaries with sibling skills

Plugin bootstrap, hooks and storage go to `wp-devkit-plugin-development`; the admin screens that call the API go to `wp-devkit-admin-ui-development`; WPGraphQL and decoupled front ends go to `wp-devkit-headless-and-wpgraphql`; broad exploit analysis goes to `wp-devkit-security-review`. This skill owns the request boundary: routes, auth, validation, response and cache behavior.

## Code Review Workflow

1. Find registration (`register_rest_route`, controller `register_routes`, `register_rest_field`, `register_meta` with `show_in_rest`) and trace in dispatch order: authentication, route match, required/`validate_callback` checks, sanitization, `permission_callback`, handler, response conversion (confirmed in `WP_REST_Server::dispatch()` and `respond_to_request()`).
2. Write the expected method, object scope, inputs, response shape and error behavior from the existing contract. Do not add a new endpoint to bypass a failing one.
3. Check object-level authorization for reads and writes, including every identifier in the payload. Intentional public submissions can be valid; assess data exposure, side effects and abuse controls rather than demanding authentication.
4. Check validation at the real boundary: a custom `sanitize_callback` replaces implicit schema validation; parameters resolve body-first; confirm the permission callback and handler read the same identifier.
5. Check responses: whitelisted fields, correct `context`, `WP_Error` with `status`, pagination bounds and headers, and cache headers for private data.
6. Describe anonymous, authorized, wrong-owner and malformed-input checks. Do not issue mutating requests during review.
7. Classify per the contract; keep pattern hits as candidates; use `insufficient evidence` when the auth model, version or CDN rules are unknown.

Read `references/rest-api-development-workbook.md` for symptom triage, worked decisions, benign look-alikes and verification recipes. Load topic references only when in scope:

- `references/route-registration-and-schema.md`: read for registration rules, controllers, how core validates args, schema keywords and coercion, fields/meta, versioning.
- `references/authentication-and-permissions.md`: read for cookie nonces, Application Passwords, 401 vs 403, object checks, public routes, CORS, abuse controls.
- `references/responses-collections-and-caching.md`: read for errors and statuses, pagination, `_fields`/`_embed`, caching and CDN, idempotency, retries.

## Implementation workflow

1. State the contract (method, URL, auth, schema, errors) and affected boundary before editing.
2. Register on `rest_api_init` with an explicit `permission_callback` (a deliberate `__return_true` for public data), schema-typed `args` with `validate_callback => rest_validate_request_arg` whenever a custom sanitizer is used, and `WP_Error` with `status`.
3. Authorize the object, not only the role. Read the identifier one way.
4. Write the failing test first (anonymous, wrong-role, wrong-owner, malformed, boundary), then the fix; re-read the object after denied calls.
5. Report unavailable checks as unexecuted. Deployment, CDN rules and live data changes need their own scope.

## Search Patterns for Quick Detection

Run only the relevant group from the first-party root; narrow `.`. Commands read files and never load WordPress. Hits are leads, not findings; no hit proves nothing (helpers, controllers and multiline arrays hide matches). Exit 0 match, 1 none, 2 error.

```sh
# Registration and controllers
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'register_rest_route|rest_api_init|extends\s+WP_REST_Controller|register_rest_field|show_in_rest' .
# Permission and object policy (read the callbacks; __return_true can be deliberate)
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'permission_callback|__return_true|current_user_can|map_meta_cap|get_current_user_id' .
# Arguments and schema
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e "validate_callback|sanitize_callback|'enum'|'required'|get_param|get_json_params|get_url_params|\\\$_(GET|POST|REQUEST)" .
# Authentication and browser intent
rg -n -g '*.{php,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'X-WP-Nonce|wp_rest|apiFetch|Authorization|rest_authentication_errors|rest_cookie' .
# Responses and errors
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'WP_REST_Response|WP_Error|rest_ensure_response|wp_send_json|\bdie\(|\bexit\(|Cache-Control' .
# Collections and write effects
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'per_page|posts_per_page|orderby|wp_insert_post|wp_update_post|wp_delete_post|update_(post|user)_meta' .
```

Read the match context; confirm reachability and what core already enforces before reporting.

## Acceptance checks

For each changed route: anonymous, subscriber, correct owner, other owner, admin; malformed JSON; missing, wrong-type, boundary and unknown-object inputs; `per_page` over the cap; repeat of a write. Assert status, structured body, stored state after denied calls, and `Cache-Control` for private responses. Commands: PHPUnit via `rest_do_request()`, `curl -i` against a disposable site, Playwright request fixtures, PHPCS and PHPStan. A pass shows tested actors and inputs behave on the tested versions; it does not prove untested roles, multisite, CDN or object-cache behavior.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: `file:line`, actor, trigger, reachable path, impact, confidence, severity (per contract), minimal fix, regression. Candidates and missing evidence separate. Implementation: contract, changed boundaries, commands with exit status, unexecuted checks, residual risk.
