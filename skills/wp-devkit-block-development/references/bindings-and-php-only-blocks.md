# Block Bindings and PHP-only blocks

Contents: Block Bindings, custom source, security, PHP-only registration, sources.

## Block Bindings (WordPress 6.5+)

Version history from the handbook: 6.5 introduced the API; 6.7 added the `block_bindings_source_value` filter, JS source registration and helpers; 6.9 added `core/post-data`, `core/term-data` and the `block_bindings_supported_attributes` filters.

Default bindable attributes: `core/image` (id, url, title, alt, caption), `core/heading` and `core/paragraph` (content), `core/button` (url, text, linkTarget, rel), `core/navigation-link` and `core/navigation-submenu` (url), `core/post-date` (datetime). Sources: `core/post-meta` (meta must be registered with `show_in_rest`; keys starting with `_` are protected and cannot be bound), `core/post-data` (date, modified, link), `core/term-data`, `core/pattern-overrides`.

Block markup:

```html
<!-- wp:paragraph {"metadata":{"bindings":{"content":{"source":"core/post-meta","args":{"key":"acme_subtitle"}}}}} -->
<p></p>
<!-- /wp:paragraph -->
```

Custom server source:

```php
add_action( 'init', static function () {
    register_block_bindings_source(
        'acme/price',
        array(
            'label'              => __( 'Price', 'acme' ),
            'uses_context'       => array( 'postId' ),
            'get_value_callback' => static function ( array $source_args, WP_Block $block, string $attribute ) {
                $post_id = (int) ( $block->context['postId'] ?? 0 );
                if ( ! $post_id || ! current_user_can( 'read_post', $post_id ) ) {
                    return null;
                }
                return esc_html( (string) get_post_meta( $post_id, 'acme_price', true ) );
            },
        )
    );
} );
```

Notes: the callback runs at render for every bound instance, so avoid heavy queries. The handbook examples do not show capability checks; add them whenever a source reads data the viewer might not be allowed to see (private posts, protected meta). Editing a bound value in the editor is off unless the JS source's `canUserEditValue` returns true. In 6.9 and later additional attributes are opted in through `block_bindings_supported_attributes` and `block_bindings_supported_attributes_{$block_type}`.

Failure signs: bound attribute shows the static fallback (unsupported block/attribute, or meta not exposed in REST); value correct on the front, empty in the editor (JS source missing or `getValues` absent).

## PHP-only blocks (WordPress 7.0)

Per the 2026-03-03 core dev note: `register_block_type( $name, array( ..., 'render_callback' => ..., 'supports' => array( 'autoRegister' => true ) ) )` makes the block appear in the editor without JavaScript; the editor renders it via ServerSideRender and generates inspector controls from `string`, `number`, `integer`, `boolean` and enum-string attributes. Limits stated there: no sourced attributes, no `save`, no inner blocks, `local` role attributes get no control, `postId` context only on initial render (tracked upstream). The dev note documents no feature-detection function and does not label the feature experimental or stable (core's own editor hook is the `__unstableAutoRegisterBlocks` global, `_wp_enqueue_auto_register_blocks()` @since 7.0.0, which only lists blocks that also have a `render_callback`). A version guard such as `is_wp_version_compatible( '7.0' )` is a commenter's suggestion, not documented API. Choose this only for simple server-rendered blocks; use the JS path for anything interactive or nested.

```php
register_block_type( 'acme/notice', array(
    'title'           => __( 'Notice', 'acme' ),
    'attributes'      => array( 'message' => array( 'type' => 'string', 'label' => __( 'Message', 'acme' ), 'default' => '' ) ),
    'render_callback' => static fn( $attrs ) => '' === $attrs['message'] ? '' : '<p>' . esc_html( $attrs['message'] ) . '</p>',
    'supports'        => array( 'autoRegister' => true ),
) );
```

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-bindings/
- https://make.wordpress.org/core/2026/03/03/php-only-block-registration/
- Core source read (trunk): `blocks.php` `_wp_enqueue_auto_register_blocks()`

Confirmed 2026-10-08 in the bindings handbook page: version history (6.5, 6.7, 6.9), default bindable attributes, `core/post-meta`/`post-data`/`term-data`/`pattern-overrides` args, protected meta rule, `get_value_callback` parameters, supported-attributes filters, no documented permission checks. The 7.0 pattern-overrides opt-in detail is unverified and was removed.
