# Patterns, template parts, assets, images and i18n

Contents: patterns, parts, enqueueing, images and LCP, internationalization and RTL, accessibility basics, sources.

## Patterns

Files in `/patterns` register automatically when they have a header. Keys: `Title`, `Slug` (namespaced `theme/pattern`), `Categories`, `Keywords`, `Viewport Width`, `Block Types`, `Post Types`, `Template Types`, `Inserter`. A pattern is either header-based or `register_block_pattern()` (camelCase keys, `source`), never both. Header patterns cannot be registered conditionally; unregister them instead. Categories `audio` and `video` arrived in 6.4; for the `query` category the handbook says to use `posts` instead.

Pattern files are PHP; translate and escape dynamic text:

```php
<?php
/**
 * Title: Hero
 * Slug: acme/hero
 * Categories: banner
 */
?>
<!-- wp:heading -->
<h2 class="wp-block-heading"><?php echo esc_html_x( 'Welcome', 'Hero heading', 'acme' ); ?></h2>
<!-- /wp:heading -->
<!-- wp:image -->
<figure class="wp-block-image"><img src="<?php echo esc_url( get_theme_file_uri( 'assets/images/hero.jpg' ) ); ?>" alt="<?php echo esc_attr_x( 'Team at work', 'Hero image alt', 'acme' ); ?>"/></figure>
<!-- /wp:image -->
```

Hard-coded absolute URLs, uploads ids and site-specific page ids break portability.

## Template parts

Block parts live in `/parts` and are referenced as `<!-- wp:template-part {"slug":"header","area":"header","tagName":"header"} /-->`. Declare `area` in `templateParts` of theme.json. Navigation menus belong to the Navigation block (a `wp_navigation` post), not hard-coded links; fallback behavior when no menu exists should be checked, not assumed.

## Enqueueing

- `wp_enqueue_scripts` for front assets; `enqueue_block_assets` for assets needed in both editor and front; `add_editor_style()` for editor-only CSS in classic/hybrid themes.
- Version assets with `wp_get_theme()->get('Version')` or file mtime; never leave `ver` empty if caching proxies are in use.
- Load scripts with `strategy => 'defer'` (6.3+ `wp_enqueue_script` args) and only on templates that need them (`is_singular()`, `has_block()`).
- Do not dequeue core block styles globally to save bytes; rely on on-demand loading (`wp_enqueue_block_style`) first.

## Images and LCP

- Core decides `loading="lazy"` vs `fetchpriority="high"` via `wp_get_loading_optimization_attributes()` (6.3+): the likely LCP image gets `fetchpriority="high"` (size threshold 50,000 square pixels by default, filter `wp_min_priority_img_pixels`), the first few images (default threshold 3, filter `wp_omit_loading_attr_threshold`) are not lazy-loaded.
- Use `wp_get_attachment_image()` / `get_header_image_tag()` so `srcset`, `sizes`, dimensions and these attributes are generated. If a hand-written `<img>` is the hero, add `width`, `height` and `fetchpriority="high"` yourself and do not add `loading="lazy"`.
- Meaningful `alt` for informative images; empty `alt=""` for decorative.

## Internationalization and RTL

- Text domain equals theme slug; `load_theme_textdomain()` on `after_setup_theme` (child: `load_child_theme_textdomain()` with its own unique domain). Block themes can also ship `/languages` JSON for editor strings.
- Wrap strings with `__`, `_x`, `_n`, `esc_html__`; no variable text domains; no string concatenation of translatable fragments.
- RTL: use logical CSS (`margin-inline-start`) or ship `rtl.css`; `wp_enqueue_block_style` with `path` swaps `-rtl.css`. Test Arabic or Hebrew content, mirrored navigation, long translations (German) and mixed direction.

## Accessibility basics owned by the theme

Skip link, landmark structure (`header`, `nav`, `main`, `footer`), visible focus, heading order from templates, 44px touch targets where feasible. Deep conformance work goes to the WCAG/accessibility skills.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/themes/patterns/registering-patterns/
- https://make.wordpress.org/core/2023/07/13/image-performance-enhancements-in-wordpress-6-3/
- https://developer.wordpress.org/reference/functions/wp_enqueue_block_style/
- https://developer.wordpress.org/themes/advanced-topics/child-themes/
- https://developer.wordpress.org/themes/patterns/using-php-in-patterns/
- Core source read (trunk, 2026-10-08): `media.php` (`wp_get_loading_optimization_attributes` since 6.3, `wp_omit_loading_attr_threshold` default 3, `wp_min_priority_img_pixels` default 50000), `functions.php`/`theme.php` (`block_template_part` since 5.9).

Confirmed: pattern header keys, `audio`/`video` categories in 6.4, header patterns cannot be registered conditionally (unregister with `unregister_block_pattern()`), a pattern uses either header or `register_block_pattern()`; pattern files may use any i18n function. Check the installed version before shipping `/languages` JSON for editor strings in block themes.
