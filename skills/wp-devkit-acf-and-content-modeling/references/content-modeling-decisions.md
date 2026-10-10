# Content modeling decisions

Contents: decision table; registration arguments that matter; meta registration; modeling smells; relationships and ownership; multilingual and multisite notes; model-change checklist; false positives.

Researched 2026-10-08. Sources: [register_post_type](https://developer.wordpress.org/reference/functions/register_post_type/), [register_meta](https://developer.wordpress.org/reference/functions/register_meta/), [ACF Repeater](https://www.advancedcustomfields.com/resources/repeater/). Only the first 100,000 characters of the `register_post_type` page were read; arguments not listed here need a re-read.

## Choose the container

| Need | Use | Why |
|---|---|---|
| Own URL, archive, publishing workflow, owner, revisions, reuse on many pages | Custom post type | First-class lifecycle and permissions |
| Shared, browsable classification used for filtering | Taxonomy (term meta for term attributes) | Indexed term relationships, archives, consistent values |
| Attribute of one parent object | Field / post meta | No lifecycle of its own |
| Short ordered list owned by one parent, never queried across parents | Repeater / array field | Rows are meta of the parent |
| Editor-composed page sections within design-system limits | Flexible content or blocks | Bounded layouts, content stays with the page |
| Site-wide singleton settings | Options page | Not for per-page, per-locale or per-user data |
| User attributes | User meta fields | Location rule "User" |

Signals that the model is wrong: templates branch on a `type` meta of a catch-all CPT; categories typed as free text or comma-separated strings; "rows" that need URLs, search or ownership living inside a repeater; flexible layouts that are near-duplicates; options-page data that really varies by page or locale.

## Registration arguments that decide behavior

- Post type key: at most 20 characters, `sanitize_key` rules, prefix it (core reserves `post`, `page`, `attachment`, `revision`, `nav_menu_item`, `wp_block`, `wp_template`, `wp_navigation` and others). Renaming a key orphans existing posts unless migrated.
- Visibility: `public` defaults to false. `publicly_queryable`, `exclude_from_search`, `show_ui`, `show_in_nav_menus` inherit from `public` unless set. Setting inherited options individually does not behave identically to `public` (Trac 18950). Decide per type whether it has a front-end URL.
- `show_in_rest` defaults to false and must be true for the block editor and for REST/headless clients; `rest_base` defaults to the key; `rest_namespace` defaults to `wp/v2` (5.9+).
- Capabilities: `capability_type` defaults to `post`, so editors of normal posts can edit your type unless you set `capability_type`/`capabilities` with `map_meta_cap`. Sensitive types (applications, internal records) need explicit capabilities; `public => false` is not an authorization model.
- `supports`: defaults to title and editor. Add `custom-fields` for posts whose registered meta must appear in the REST API (the [register_meta reference](https://developer.wordpress.org/reference/functions/register_meta/) states that a post type must declare support for custom fields for registered meta to be accessible via REST), `revisions`, `author`, `thumbnail`.
- `delete_with_user`: unset means posts are trashed on user deletion only when the type supports `author`.
- `template` and `template_lock` (`all`, `insert`, `contentOnly`) predefine and lock the editor structure.
- Rewrite rules: call `flush_rewrite_rules()` only on activation, deactivation or theme switch, never on every request. After changing `rewrite`/`has_archive`, a flush (or Settings > Permalinks save) is a deployment step; in CI use `wp rewrite flush`.

## Register meta so REST, auth and sanitization are explicit

```php
add_action( 'init', function () {
	register_post_meta( 'event', 'event_capacity', array(
		'type'              => 'integer',
		'single'            => true,
		'default'           => 0,
		'show_in_rest'      => true,
		'sanitize_callback' => 'absint',
		'auth_callback'     => static fn() => current_user_can( 'edit_events' ),
	) );
} );
```

- `auth_callback` omitted means non-protected meta is writable by anyone who can edit the object; protected keys (underscore prefix) default to denied. State the intended capability.
- An `array`/`object` meta with `show_in_rest` needs `show_in_rest.schema.items`, or registration returns false.
- `default` must match `type`; `revisions_enabled` (6.4+) stores the key in revisions; `label` is 6.7+.
- ACF registers its own fields. Registering the same key with `register_post_meta` too can double-handle sanitization; pick one owner per key and test the REST write.

## Relationships

- Post Object / Relationship / User fields store IDs (or arrays of IDs). Return format (object, ID) changes what templates receive. Changing return format is a consumer change, not a storage change; storage is the same but templates, REST and GraphQL output change.
- Bidirectional relations are two stored lists that can drift. Choose one owning side or maintain both transactionally (on `acf/save_post`).
- Deleting a referenced post leaves stale IDs. Templates must tolerate missing targets; consider cleanup on `before_delete_post`.
- Relationship pickers over very large sets load slowly in admin; restrict by post type, filter, taxonomy.

## Multilingual and multisite

- Translation plugins (WPML, Polylang) duplicate or sync posts and meta; each has its own ACF compatibility rules (field "translate/copy/ignore" settings). Check the plugin's mode before changing field names.
- Multisite: field groups can be per-site (database) or shared (Local JSON in a shared plugin/mu-plugin). Options pages and `get_field( ..., 'option' )` are per-site; `switch_to_blog` changes which postmeta is read, so pass explicit IDs.

## Changing a model safely

1. Inventory consumers: templates, blocks, REST/GraphQL, feeds, search, exports, imports, shortcodes.
2. Add the new structure alongside the old; keep the old key until consumers moved.
3. Backfill idempotently in batches (see [meta-queries-and-field-migrations.md](meta-queries-and-field-migrations.md)).
4. Dual-read during rollout if releases are not atomic; remove the old key later in a separate release.
5. Verify counts: old rows, new rows, mismatches, and a sample of rendered pages.

## Looks wrong but is fine

- A repeater with a handful of rows that is never queried across posts.
- Options-page data for a true site-wide singleton.
- `public => false` types with `show_ui => true` for admin-only records, when capabilities are also set.
- A post-type key different from its label or slug.
- Flexible content on landing pages with a governed, documented layout set.
