# Template ownership and hierarchy

Contents: theme type detection, precedence, hierarchy gotchas, classic loop rules, plugin templates, how to confirm, sources.

## Theme type detection

- Block theme: `style.css` plus `templates/index.html` (the only required template). `/block-templates` is a legacy location. `wp_is_block_theme()` defers to `WP_Theme::is_block_theme()`, which checks for `templates/index.html` or the legacy `block-templates/index.html` (see `class-wp-theme.php` in core).
- Classic theme: PHP templates (`index.php`, `style.css`). A `theme.json`, patterns, or `add_theme_support( 'block-template-parts' )` do not make it a block theme; these produce a "hybrid", a community term, still classic internally.
- Child theme: `style.css` header `Template:` must equal the parent folder name exactly. Block child themes override parent templates, parts and patterns by same name (a pattern also needs the same `Slug`); child `functions.php` loads before the parent's and does not replace it.

## Precedence (block themes)

1. User-saved template/part in the database (`wp_template`, `wp_template_part` post types).
2. Child theme `/templates`.
3. Parent theme `/templates`.

Plugins can add templates (`register_block_template()`, WordPress 6.7+, name form `plugin_uri//template_name`). A saved database template shadows a changed theme file without any code defect.

Global Styles customizations are stored in a `wp_global_styles` post per theme and sit above `theme.json`.

## Confirm which layer is rendering (read-only where possible)

```sh
wp theme list --fields=name,status,version,parent
wp eval 'var_dump( wp_is_block_theme() );'
wp post list --post_type=wp_template,wp_template_part,wp_global_styles --post_status=any --fields=ID,post_type,post_name,post_status,post_modified
```

In the Site Editor the Templates list marks customized entries and offers "Clear customizations". Do not clear them on a live or client site without an export (Site Editor export, or `wp post get <id> --field=post_content`) and owner approval; the content is user data. Report ownership, then propose the change.

## Hierarchy gotchas

- `front-page` always wins over the Reading setting; `home` is the posts index, not necessarily the home page. Static front page + posts page: posts page uses `home` then `index`.
- Attachment pages are off by default on new installs since 6.4; do not design around them without checking `wp option get wp_attachment_pages_enabled`.
- Embed templates are not supported by the block templates system; they must be PHP files in the theme root.
- Custom (page) templates in a block theme are declared under `customTemplates` in `theme.json` (`name`, `title`, `postTypes`); filenames must not shadow hierarchy names.

## Classic template rules

- After any secondary `WP_Query` loop call `wp_reset_postdata()`. After `query_posts()` (avoid it; use `pre_get_posts` for the main query) the global is clobbered.
- Change the main query only in `pre_get_posts`, guarded with `$query->is_main_query() && ! is_admin()`.
- Escape late: `esc_html( get_the_title() )` is redundant for `the_title()` output, but escape custom fields and options (`esc_attr`, `esc_url`, `wp_kses_post`).
- Keep `wp_head()`, `wp_footer()`, `wp_body_open()`, `body_class()`, `post_class()` in place; removing them breaks plugins and block styles.
- Pagination uses the main query; custom loops need `paged` handling and `paginate_links()` with the custom `max_num_pages`.

## Sources

Research date: 2026-10-08.

- https://developer.wordpress.org/themes/templates/template-hierarchy/
- https://developer.wordpress.org/themes/templates/templates/
- https://developer.wordpress.org/themes/core/theme-structure/
- https://developer.wordpress.org/themes/advanced-topics/child-themes/
- https://developer.wordpress.org/reference/functions/register_block_template/

Primary source notes: `register_block_template()` since 6.7 with name form `plugin_uri//template_name`; `wp_attachment_pages_enabled` option (core `wp-admin/includes/schema.php` and `upgrade.php`) and attachment pages off by default for new installs since 6.4; `front-page` precedence, `home` meaning and embed-template rule (template-hierarchy page); child `functions.php` loads immediately before the parent's, `Template` must match the parent folder name, block child themes override templates/parts/patterns by name (patterns also by `Slug`) (child-themes page); one `wp_global_styles` post per theme resolved by `WP_Theme_JSON_Resolver::get_user_data_from_wp_global_styles()` (core).
