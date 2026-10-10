# Schema authority: Local JSON, PHP registration, database, sync

Contents: who is the schema authority; Local JSON paths and filters; sync semantics; PHP registration; ACF WP-CLI; key and name stability; environment drift checks; plugin edition and fork notes; failure symptoms; false positives.

Researched 2026-10-08. Sources: [ACF Local JSON](https://www.advancedcustomfields.com/resources/local-json/), [Register fields via PHP](https://www.advancedcustomfields.com/resources/register-fields-via-php/), [ACF WP-CLI](https://www.advancedcustomfields.com/resources/wp-cli/), [Secure Custom Fields docs](https://developer.wordpress.org/secure-custom-fields/). The ACF docs do not state JSON-versus-database precedence explicitly; verify with a test in the target version.

## Establish the authority

A field definition can exist in three places: the database (field group posts created in the admin), Local JSON files, and PHP (`acf_add_local_field_group`). Find out which exist and which wins before diagnosing "field missing/different" bugs.

```sh
rg --files -g 'acf-json/**' -g '**/acf-json/**' -g '!vendor' -g '!node_modules'
rg -n "acf/settings/(save_json|load_json)|acf/json/(save_paths|load_paths|save_file_name)|acf_add_local_field_group|acf/include_fields|acf/init" --glob '*.php'
wp acf json status          # ACF 6.8+; read-only
wp post list --post-type=acf-field-group --fields=ID,post_title,post_status
```

Healthy target: field definitions are code. They are edited in a development environment, exported to JSON committed to git, reviewed in the same pull request as the templates/blocks that consume them, and imported by deployment. Production admin edits are exceptions that get exported back.

## Local JSON

- Default folder is `acf-json` in the (child) theme. It must be writable where definitions are edited and only readable in production if edits are disabled there. Add an empty `index.php` to prevent directory listing.
- Stored objects: field groups, post types, taxonomies and UI options pages.
- Filters: `acf/settings/save_json` (universal save path; ACF 6.2+ accepts `key=`, `name=` and `type=` modifiers with `acf-field-group`, `acf-post-type`, `acf-taxonomy`, `acf-ui-options-page`, most specific wins), `acf/json/save_paths` (6.2+, route items by settings), `acf/json/save_file_name` (default file name is the item key), `acf/settings/load_json` (add load folders; a custom save path must also be added to the load list or ACF will not read it back).
- Move JSON out of a theme into a plugin or mu-plugin when the schema must survive theme switches or is shared across a multisite network:

```php
add_filter( 'acf/settings/save_json', static fn() => WP_PLUGIN_DIR . '/site-schema/acf-json' );
add_filter( 'acf/settings/load_json', static function ( array $paths ): array {
	$paths[] = WP_PLUGIN_DIR . '/site-schema/acf-json';
	return $paths;
} );
```

- Accidentally ignored `acf-json` (check `.gitignore`), or JSON saved to a path that is not loaded elsewhere, is the most common silent schema drift.

## Sync semantics

- An item is "available to sync" when it is absent from the database or its JSON `modified` value is later than the database post's modified time. Because `modified` is a timestamp, two developers editing the same group produce merge conflicts in JSON and a "later wins" outcome; review the JSON diff, not just the admin screen.
- Sync imports JSON into the database. Neither the Local JSON page nor the [WP-CLI page](https://www.advancedcustomfields.com/resources/wp-cli/) says whether it removes database items whose JSON file was deleted (check the installed version); test it on staging and plan an explicit removal step for retired groups.
- Deploy: run sync as a release step (`wp acf json sync` on ACF 6.8+ writes to the database; `wp acf json import` and `export` move items to or from files; `status` reports). Before 6.8 or on hosts without CLI, use the admin Sync action. Do not run sync, import or export during a read-only review.
- JSON loading reduces database reads at runtime; it does not remove the need to sync if the admin UI lists database copies.

## PHP registration

`acf_add_local_field_group()` is documented for use at file root (guarded) or in an `acf/init` callback. Group keys start with `group_`, field keys with `field_`, and every key must be unique; with duplicate keys the later registration overrides the earlier. Fields registered in code are not editable on the Field Groups admin screen. Some settings (for example radio `save_other_choice`) do not work for PHP-registered fields.

Use PHP registration for plugin-shipped fields that site admins must not edit, and Local JSON for fields edited in the admin. Registering the same key in both is allowed but ambiguous; avoid it and, if found, report which copy the test environment loads.

## Keys and names are contracts

- The field key (`field_...`) is the stored reference (`_fieldname` meta holds it). The field name (meta key) is what queries, REST and templates use. Label changes are free. Name changes orphan stored values. Key changes break the reference for existing values until rewritten.
- Duplicating a field group in the admin and editing only labels creates new keys but identical names: two groups writing the same meta key with different settings (return format, type). Rename names for the new context or use clone fields.
- Use stable, prefixed names (`acme_event_capacity`). Do not regenerate keys during a refactor; if keys must change, migrate the reference meta too ([meta-queries-and-field-migrations.md](meta-queries-and-field-migrations.md)).

## Environment drift check (read-only)

1. List JSON items and their `modified` values. Compare to database items (`wp acf json status`, or `wp post list --post-type=acf-field-group --fields=ID,post_title,post_modified`).
2. Compare the committed JSON between branches (`git diff --stat -- '**/acf-json/*.json'`).
3. A fresh clone plus `wp acf json sync` on an empty database should reproduce the schema. If it does not, the repo is not the authority.
4. Look for field groups whose location rules differ between environments (post type slugs, block names, page templates).

## Edition and fork notes

- ACF Blocks, repeaters, flexible content, clone, options pages and some other features are ACF PRO. Confirm the edition before recommending a feature. License handling and updates differ for PRO; a lapsed license stops updates but field data remains in the database.
- WordPress.org also distributes Secure Custom Fields (SCF), a fork of ACF (documented at developer.wordpress.org/secure-custom-fields; WordPress 6.2+, PHP 7.4+). It exposes ACF-style APIs but is a different plugin with its own release cadence. Identify which plugin is active (`wp plugin list --fields=name,version,status`) before citing ACF behavior or a version number, and do not assume parity of newer ACF features (for example the ACF 6.8 CLI commands) in SCF.
- Recent ACF releases are security-relevant. The [official ACF changelog](https://www.advancedcustomfields.com/changelog/) (read 2026-10-08) lists, among others: 6.8.7 server-side validation so Image and Gallery fields accept only image files and read-permission enforcement for Post Object, Page Link and Relationship AJAX searches; 6.8.10 read-permission checks for Relationship, Post Object, Image, Gallery and File values in REST responses; 6.7.1 and 6.7.2 AJAX query restrictions and capability checks. WP-CLI `wp acf json` arrived in 6.8.0. Recommend keeping ACF current, and check the target's version rather than assuming a fix is present.

## Symptoms and causes

| Symptom | Likely cause | Confirm |
|---|---|---|
| Fields present locally, missing in production | JSON not deployed or not synced; custom `load_json` path missing in production | `wp acf json status` (ACF 6.8.0+, per the WP-CLI page: ACF 6.8 or later, WP-CLI 2.0 or later); list `acf-json` on the server |
| Field group appears twice | Same key in JSON and PHP, or a copy in the database | `wp post list --post-type=acf-field-group`, grep `acf_add_local_field_group` |
| Editors see old settings after deploy | Database copy newer than JSON, or sync not run | Compare `modified` values |
| Value saved but template shows raw ID / unformatted | Missing reference meta (`_name` key) for the stored value | `wp post meta get <id> _field_name` |

## Looks wrong but is fine

- Field groups only in Local JSON with no database copy: that is the intended state.
- `acf-json` committed in a plugin, not the theme.
- PHP-registered plugin fields absent from the admin Field Groups list.
- A pending "sync available" notice on a developer machine right after pulling new JSON: that is the normal import step.
