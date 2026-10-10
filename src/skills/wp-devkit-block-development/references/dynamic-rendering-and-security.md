# Dynamic rendering, escaping and caching

Contents: render contract, wrapper attributes, escaping, inner blocks, query/performance, multisite and caching, sources.

## Render contract

`render.php` (metadata `render`, 6.1+) or `render_callback` receives `$attributes`, `$content` (serialized inner blocks, already rendered), `$block` (`WP_Block`, with `context`, `inner_blocks`, `parsed_block`). It returns a string; do not `echo` unless using the `render.php` file form, which is output-buffered by core.

```php
<?php
// render.php: $attributes, $content, $block are provided by core.
$message = isset( $attributes['message'] ) ? (string) $attributes['message'] : '';
if ( '' === $message ) {
    return; // render nothing for empty state
}
?>
<div <?php echo get_block_wrapper_attributes( array( 'data-kind' => 'notice' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped by core. ?>>
    <?php echo esc_html( $message ); ?>
    <?php echo $content; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- rendered inner blocks. ?>
</div>
```

- `get_block_wrapper_attributes( $extra )` (5.6+) escapes every value with `esc_attr`, merges `class` lists, filters `style` through `safecss_filter_attr`, and for `id`/`aria-label` prefers the non-empty extra value. It rejects booleans, null, arrays. Call it on the outermost element only; omitting it drops alignment, colors, spacing and custom class names that supports generate.
- Use `esc_html`, `esc_attr`, `esc_url`, `wp_kses_post` for the actual output context. `$content` is trusted rendered block output; do not run it through `esc_html` (breaks nested blocks) or `strip_tags`.
- Attributes are untrusted: any user who can edit a post (or craft block comment JSON via REST with `unfiltered_html`-less roles) controls them. A `type: string` attribute can still contain markup. Validate numbers with `absint()`/`min()`, enums with `in_array( ..., true )`, URLs with `esc_url`.
- Early `return` with empty output is valid and preferred over rendering empty wrappers.

## Inner blocks

A dynamic container keeps children by saving `<InnerBlocks.Content />`. `$content` is then the rendered children. If the PHP wants to wrap or filter children, use `$block->inner_blocks` or `render_block_data`/`render_block` filters rather than regexing `$content`. For a parent that renders children individually, call `$block->render()` per inner block (`WP_Block::render()` in trunk skips rendering inner content when the block type has a truthy `skip_inner_blocks` property; check the installed core for the version that introduced it and how to set it before relying on it).

## Editor preview

Use `ServerSideRender` (`@wordpress/server-side-render`) only for simple previews: it issues a REST request per attribute change. For frequent edits, mirror the output in `edit()`. PHP-only blocks (WordPress 7.0, `supports.autoRegister`) rely on it; see [bindings-and-php-only-blocks.md](bindings-and-php-only-blocks.md).

## Performance and caching

- `render.php` runs on every request for every instance. Avoid unbounded `WP_Query` (`posts_per_page => -1`), set `no_found_rows => true` when not paginating, `fields => 'ids'` when only ids are needed, and `update_post_meta_cache`/`update_post_term_cache` false when unused.
- Cache expensive results with `wp_cache_get/set` (object cache, group + invalidation hook on `save_post`/`deleted_post`) or transients when no persistent cache exists. Key by the attributes and locale. Never key by user unless output differs by user, and never page-cache output that includes nonces or per-user data without an Edge-Side/ajax boundary.
- Block-level rendering cost shows in Query Monitor under "Blocks"/hooks; confirm with it rather than guessing.

## Multisite and context

`switch_to_blog()` inside a render callback must be paired with `restore_current_blog()` in a `finally`; options and attachment URLs differ per site. Do not hard-code site ids in attributes. Context (`usesContext: ["postId","postType","queryId"]`) is available to `edit` and to render (`$block->context`), not to `save`.

## Review heuristics: looks wrong but is fine

- `save: () => null` on a leaf dynamic block.
- `echo $content;` without escaping when `$content` is the render callback parameter (verify it is not a user-supplied attribute).
- A block with no `render` key and static `save` markup.
- `apiVersion` 2 in a legacy block that still works; report as INFO/compat, not a defect.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/reference/functions/get_block_wrapper_attributes/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-metadata/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-edit-save/
- Core source read (trunk, 2026-10-08): `get_block_wrapper_attributes()` in `class-wp-block-supports.php` (merges `class`, `style`, `id`, `aria-label`; casts scalars; rejects bool/null/array), `WP_Block::render()` in `class-wp-block.php`
