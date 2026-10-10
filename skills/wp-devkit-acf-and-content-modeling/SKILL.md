---
name: wp-devkit-acf-and-content-modeling
description: "Design, debug or review WordPress content models and ACF. Use for CPT vs taxonomy vs field choices, Local JSON/PHP schema drift, missing or unformatted values, ACF validation and REST exposure, meta_query slowness and safe field renames or backfills."
---

# Editorial models and field evolution

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, schema or data changes, `wp acf json sync|import`, backfills, or running untrusted code. Use the implementation path only when the request authorizes changes.

## Inputs to establish

ACF edition and version (or Secure Custom Fields), WordPress version, where field definitions live (database, Local JSON path, PHP), field keys and names involved, return formats, record volume per post type, consumers of the data (templates, blocks, REST, GraphQL, feeds, imports), multisite and translation plugin use, and whether a disposable copy of the site exists.

Inspect project evidence before asking. State material assumptions.

## Route the task

| Question | Read |
|---|---|
| Is this a CPT, taxonomy, field, options page or block? Post type, capability or REST registration arguments? | `references/content-modeling-decisions.md` |
| Field group missing/different between environments; JSON vs PHP vs database; sync; keys vs names | `references/schema-authority-and-sync.md` |
| Wrong or unformatted value, `update_field` result, validation, REST/GraphQL exposure, escaping, ACF Blocks | `references/values-validation-and-output.md` |
| Slow archive or filter, `meta_query`, date/number comparison, rename a field, backfill, remove old data | `references/meta-queries-and-field-migrations.md` |

Hand off: block structure and Interactivity API to `wp-devkit-block-development`; WPGraphQL schema and caching to `wp-devkit-headless-and-wpgraphql`; REST route design and permissions to `wp-devkit-rest-api-development`; deployment of schema changes to `wp-devkit-ci-cd-and-release-engineering`; broad data upgrade strategy to `wp-devkit-migration-upgrade-review`; XSS or authorization defects with a reachable path to `wp-devkit-security-review`; measured whole-site slowness to `wp-devkit-performance-review`.

## Code Review Workflow

1. Name the entities, their lifecycle needs and their consumers. Check the modeling choice against the decision table before judging field types.
2. Find the schema authority (database, Local JSON, PHP) and verify duplicates, load paths and key/name stability. Do not conclude from one file.
3. Trace each value from storage through formatting to the sink. Check return format, reference meta, escaping at output and exposure through REST/GraphQL.
4. Check every write path (admin, `acf_form`, REST, import, WP-CLI, `update_field` calls) enforces the same domain rules.
5. For queries, count participating records, inspect key/type/format, and measure or EXPLAIN before calling a query slow.
6. For a model change, map old to new, list consumers, and define backfill, dual-read, verification and rollback. Review does not run them.

A finding needs a reachable path and impact. A different modeling opinion without a demonstrated cost is INFO. Insufficient evidence (no data volume, no access to the production schema) is a valid outcome: say what is missing and how to get it.

## Implementation workflow

1. Define expected behavior and the smallest affected boundary; name the schema authority you will edit.
2. Edit definitions in the authority (JSON/PHP), never only in a production admin screen. Keep field keys; change names only with a migration.
3. Write the migration idempotent, resumable and dry-run by default; test on a copy; keep the old data until verified.
4. Update every consumer in the same change set (templates, blocks, REST/GraphQL, imports).
5. Run the acceptance checks; report unavailable checks as unexecuted. Deployment and live data changes need their own task scope and a backup.

## Search Patterns for Quick Detection

Read-only leads from the project root; matches are candidates, not findings. Exit 0 means a match, 1 none, 2 an error.

```sh
rg -n -g '*.php' -g '!vendor' -g '!node_modules' -e 'register_post_type|register_taxonomy|register_(post|term)_meta|show_in_rest|capability_type|map_meta_cap' .
rg -n -g '*.php' -g '*.json' -g '!vendor' -g '!node_modules' -e 'acf_add_local_field_group|acf/settings/(save|load)_json|acf/json/|return_format|"key": "(field|group)_' .
rg -n -g '*.php' -g '!vendor' -g '!node_modules' -e 'update_field|add_row|update_row|acf/validate_value|acf/save_post|acf_form' .
rg -n -g '*.php' -g '!vendor' -g '!node_modules' -e "meta_query|'meta_key'|orderby.*meta_value|LIKE|get_field\(|the_field\(|get_sub_field\(" .
```

No match does not prove absence (helpers, generated code, JSON-only schemas). Output escaping is judged at the final sink, not by the presence of `get_field`.

## Acceptance checks

- Schema: `wp acf json status` (ACF 6.8+, read-only) or compare `acf-json` against the database list; a fresh checkout plus sync reproduces the schema on a disposable site.
- Values: `wp post meta list <id>` for stored value and reference; render the page; compare `get_field( $name, $id, false )` and formatted output.
- Validation: an invalid value rejected on each write path (admin form, REST, import).
- REST: `GET /wp-json/wp/v2/<type>/<id>?acf_format=standard` as anonymous and as a low-privilege user; no unintended fields.
- Queries: `EXPLAIN` or Query Monitor numbers before and after, on realistic volume.
- Migration: counts old vs new vs mismatched equal expectations; rollback path tested before old data is deleted.
- Static: `phpcs` WordPress standards and project PHPStan, if configured.

A pass proves the tested paths, volume and versions. It does not prove production data cleanliness, untested write paths, other consumers of the old field, or behavior of a different ACF/SCF edition.

## Output Format

Review: result and scope first. Each confirmed finding: severity per the contract, file:line, actor, trigger, reachable path, impact, confidence, minimal remediation, regression check. Candidates and missing evidence in a separate list. Modeling recommendations state the decision, the reason, affected consumers and migration needs.

Implementation: changed boundaries, schema authority edited, migration steps with dry-run output, commands run with exit status, checks not run, residual risk, rollback.

## References

- `references/content-modeling-decisions.md`: read for CPT/taxonomy/field choice and registration arguments.
- `references/schema-authority-and-sync.md`: read for Local JSON, PHP, database, sync and drift.
- `references/values-validation-and-output.md`: read for reads, writes, validation, REST, escaping, blocks.
- `references/meta-queries-and-field-migrations.md`: read for meta-query cost, renames, backfills.
