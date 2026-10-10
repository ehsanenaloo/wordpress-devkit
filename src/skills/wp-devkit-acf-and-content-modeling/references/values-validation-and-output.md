# Field values: read, write, validate, expose, output

Contents: read paths and formatting; write paths; validation; REST and headless exposure; escaping at output; ACF Blocks; nested fields and storage; failure symptoms; false positives.

Researched 2026-10-08. Sources: [get_field](https://www.advancedcustomfields.com/resources/get_field/), [update_field](https://www.advancedcustomfields.com/resources/update_field/), [acf/validate_value](https://www.advancedcustomfields.com/resources/acf-validate_value/), [acf/save_post](https://www.advancedcustomfields.com/resources/acf-save_post/), [ACF REST integration](https://www.advancedcustomfields.com/resources/wp-rest-api-integration/), [HTML escaping](https://www.advancedcustomfields.com/resources/html-escaping/), [Create your first ACF block](https://www.advancedcustomfields.com/resources/create-your-first-acf-block/), [ACF Blocks V3 release notes](https://wpengine.com/blog/acf-6-6-release).

## Read paths

- `get_field( $selector, $post_id = false, $format_value = true, $escape_html = false )`. Formatting turns stored IDs into objects/arrays according to the field's return format (image object, post object, formatted date). `$format_value = false` returns the stored value. `$escape_html = true` (6.2.6+ per the docs page) returns an HTML-safe value and needs `$format_value = true` (otherwise `_doing_it_wrong`). The docs say returned values must be escaped with an appropriate function before output.
- Post ID formats: `false` = current post, `123`, `'user_2'`, `'category_3'` / `'taxonomyname_4'`, `'option'`. Inside loops or `switch_to_blog`, pass the ID explicitly.
- Since ACF 5.11, `get_field()` no longer returns arbitrary meta or options not tied to an ACF field.
- Each `get_field()` for an unformatted scalar is cheap after the post's meta is primed; formatted relational values (image, post object) trigger extra lookups per call. In loops, prime caches (`update_meta_cache`, `_prime_post_caches`) or fetch `get_fields( $id )` once and reuse.
- Return format is part of the contract. Changing Image from array to ID changes every template and every REST/GraphQL consumer, not the stored data.

## Write paths

`update_field( $selector, $value, $post_id )`:

- Use the field key (`field_...`) when the post has no value yet. Stored values carry a reference to their field key; without it ACF cannot format the value later (for example an image field returns an ID instead of an object). Names are fine for updating an existing value.
- Return value (per the [update_field docs](https://www.advancedcustomfields.com/resources/update_field/)): meta ID (int) when a new value is saved to a field that had none, `true` on success, `false` on failure and also `false` when the new value equals the stored one. Do not treat `false` as failure without re-reading the value.
- Repeater and flexible content take nested arrays; flexible rows need `acf_fc_layout`.
- Image/File/Gallery take attachment IDs.
- It writes. It is not an authorization check and the docs do not say it runs the admin-form validation pipeline. In the source of Secure Custom Fields (the ACF-derived fork; ACF itself is closed source, so check ACF proper) `acf_update_value()` does not call `acf_validate_value()`, form validation runs through `acf_validate_save_post()` on `$_POST['acf']`, and REST writes are checked by core schema validation plus the `acf/validate_rest_value/type=` filter. Test on the installed version whether your `acf/validate_value` rules apply to importers, WP-CLI scripts and REST writes.

```php
$ok = update_field( 'field_65a1b2c3d4e5f', absint( $capacity ), $event_id );
if ( false === $ok && absint( $capacity ) !== (int) get_field( 'event_capacity', $event_id, false ) ) {
	// real failure, not just "unchanged"
}
```

Import paths (CSV, REST, WP-CLI, sync jobs) must each enforce the same domain rules as the editor form. Put the rules in one function and call it from `acf/validate_value`, REST `sanitize`/`validate` code and import code.

## Validation

```php
add_filter( 'acf/validate_value/key=field_65a1b2c3d4e5f', static function ( $valid, $value, $field, $input_name ) {
	if ( true !== $valid ) {
		return $valid;                      // keep earlier errors
	}
	return ( (int) $value >= 0 && (int) $value <= 5000 )
		? true
		: __( 'Capacity must be between 0 and 5000.', 'site-schema' );
}, 10, 4 );
```

- Variants: `acf/validate_value`, `/type=`, `/name=`, `/key=`. Return `true` or an error string. Added in ACF 5.0.0; the docs page is from 2022, so re-check against the installed version.
- Validation runs before the value is saved by the ACF form pipeline. It does not replace sanitization at the sink and does not constrain code that writes post meta directly.
- `acf/save_post`: priority below 10 runs before ACF saves (`$_POST['acf']` holds submitted values keyed by field key); default priority 10 runs after. The action does not receive `$post` or `$updated`. Use it for derived data, with its own nonce/capability reasoning when it reads `$_POST` (the ACF docs examples do not show these checks).

## REST and headless exposure

- Field groups are hidden from REST by default; enable "Show in REST API" on the group (ACF 5.11+). Values appear under `acf` on the object. Default format is `light`; `?acf_format=standard` runs the value formatter (attachment objects instead of IDs); `acf/settings/rest_api_format` sets the site default. `acf/rest/get_fields` controls which fields appear per method (return an empty array to disable), `acf/rest/format_value_for_rest` adjusts output, `acf/settings/rest_api_enabled` returning false disables ACF REST entirely. Message, Accordion and Tab fields are not supported.
- Writes: POST bodies include an `acf` object; `null` clears; invalid values produce a 400. The docs only state that writes must be authenticated and do not describe capability checks beyond the post's own edit permission. Confirm: an author-level user cannot write fields on posts they cannot edit, and a field containing HTML does not bypass `unfiltered_html` rules.
- Show-in-REST on a group exposes every field in it, including internal notes or emails. Split public and private fields into separate groups. Draft/private post values follow the object's status permissions; do not assume they are hidden.
- Options-page fields are not covered by the REST integration page; expose them through a custom route with a `permission_callback`.
- For WPGraphQL exposure see `wp-devkit-headless-and-wpgraphql`.

## Escape at the sink

ACF escapes its own admin/`acf_form()` HTML (`acf_esc_html()` through `wp_kses` with the `acf` context) but the docs state `get_field()` API values are not covered. Treat every field as untrusted input to the template:

| Field content | Output |
|---|---|
| Text, number, select label | `esc_html()` |
| URL, Link field `url` | `esc_url()`; add `rel` for `target="_blank"` |
| Link `title`, target | `esc_html()`, `esc_attr()` |
| WYSIWYG, textarea with HTML | `wp_kses_post()` |
| Attribute | `esc_attr()` |
| JS context | `wp_json_encode()` / `wp_add_inline_script` data |

`the_field()`/`the_sub_field()`: from ACF 6.2.7 output of these is passed through ACF's allowed-HTML filter and ACF Shortcode output from 6.2.5 (per the escaping page). Do not rely on that to remove escaping from custom templates; extend allowed tags with the `wp_kses_allowed_html` filter in the `acf` context only when needed.

## ACF Blocks

- ACF Blocks are an ACF PRO feature. Register through `block.json` with an `acf` object (`mode`: `preview`, `auto`, `edit`; `renderTemplate`: PHP file). The field group uses the location rule "Block is equal to" the block. Block version 3 (ACF 6.6+, WordPress 6.2+) is opt-in with `"blockVersion": 3` in the `acf` object or the `acf/blocks/default_block_version` filter; a `blockVersion` in `block.json` wins. V3 moves field editing to a sidebar and prepares for the iframe editor.
- Templates receive `$block`, `$is_preview`, `$post_id`. Escape every field as above; use `get_block_wrapper_attributes()` for wrapper attributes. For users without `unfiltered_html`, block content passes `wp_kses_post()`.
- Validate custom block fields on the block's own save path, not only in a metabox.
- For general block structure, deprecations and Interactivity API, use `wp-devkit-block-development`.

## Nested fields and storage

Observe with `wp post meta list <id>`: repeaters store a row count under the field name and sub-values under `{name}_{index}_{sub}`, each with an underscore-prefixed reference meta holding the field key (the ACF docs pages do not describe storage; the layout is confirmed only by ACF support-forum answers, so inspect the real meta). Consequences: deleting a row needs the rest of the rows re-indexed by ACF, not hand-edited meta; direct meta deletes leave orphans; row-level SQL is fragile. Enable repeater pagination (6.0+) only for admin UX on large repeaters; it does not affect templates, REST, nested repeaters, flexible content or blocks.

## Symptoms and fixes

| Symptom | Likely cause | Fix and proof |
|---|---|---|
| `update_field()` returned false, value is correct | Value unchanged | Compare with raw stored value before alarming |
| New value saved but template returns ID/string | Reference meta missing (name used on first write) | Rewrite with the field key; assert `get_field` returns the formatted type |
| Validation passes in admin, bad data via import | Rules live only in `acf/validate_value` | Shared validator called from the import; test with bad row |
| REST output differs from template | `acf_format` light vs standard | Request `?acf_format=standard` or normalize in a controller |
| Raw HTML appears in front end | Escaping omitted for WYSIWYG | Add `wp_kses_post()`; test with `<script>` payload in the field |

## Looks wrong but is fine

- `wp_kses_post( get_field( 'body' ) )` for WYSIWYG output.
- `get_field( 'x', $id, false )` reading raw values in a migration.
- `update_field()` with a field name on a post that already has the value.
- Group-level "Show in REST API" on a group that contains only public fields.
