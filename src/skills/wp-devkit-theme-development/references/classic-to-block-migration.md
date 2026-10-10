# Classic, hybrid and block migration

Contents: choose a path, inventory, mapping table, hybrid steps, cutover and rollback, verification, sources.

## Choose a path

| Path | When | Cost |
| --- | --- | --- |
| Stay classic | Heavy PHP template logic, page builder dependence, short horizon | No Site Editor |
| Hybrid | Incremental: add `theme.json`, `add_theme_support( 'block-template-parts' )`, block parts/patterns, keep PHP templates | Two systems to maintain; still a classic theme internally |
| Full block theme | Marketing/content sites, design-system alignment | Rebuild templates, navigation, widgets; user data must be mapped |

`theme.json` in a classic theme provides settings and styles (and editor presets) but does not turn it into a block theme. Only `templates/index.html` does that, which moves editing to the Site Editor; widgets and Customizer-based settings need an explicit plan.

## Inventory before any change

Templates and parts (`header.php`, `single.php`, `archive.php`, custom page templates), `functions.php` (theme supports, menus, sidebars, image sizes, CPT/taxonomy registration that belongs in a plugin), widgets and sidebars, Customizer settings (`wp theme mod list`), shortcodes in content, page-builder content, menu locations, and URLs (permalinks, canonical, redirects).

```sh
wp theme mod list
wp menu location list
wp widget list sidebar-1 --format=table
wp post list --post_type=page,post --s='[' --fields=ID,post_title   # rough shortcode lead only
```

## Mapping

| Classic | Block-theme destination |
| --- | --- |
| `add_theme_support( 'editor-color-palette' )`, font sizes | `settings.color.palette`, `settings.typography.fontSizes` |
| `header.php`/`footer.php` | `parts/header.html`, `parts/footer.html` |
| `single.php`, `archive.php` | `templates/single.html`, `templates/archive.html` with Post/Query Loop blocks |
| `register_nav_menus()` + `wp_nav_menu()` | Navigation block (`wp_navigation` post); menus must be converted/created |
| Sidebars/widgets | Template part with blocks; legacy widgets can be placed with the Legacy Widget block during transition |
| Customizer colors/CSS | Global Styles / `theme.json`; saved theme mods are not migrated automatically |
| Page templates | `customTemplates` + `templates/*.html` |
| `post_class()`/loop logic | Blocks and dynamic blocks; PHP-only logic moves to a plugin or a custom block |

`add_theme_support()` for features that still apply (`post-thumbnails`, `html5`, `title-tag`, `responsive-embeds`) remains valid in block themes.

## Hybrid steps

1. Add `theme.json` with `$schema`, `version`, palette/typography matching existing CSS values.
2. Remove duplicated `add_theme_support` palette calls only after verifying the editor shows the same presets.
3. Add `block-template-parts` support and migrate header/footer to parts that classic templates call via `block_template_part( 'header' )`.
4. Add patterns for repeatable sections.
5. Convert templates one at a time; keep the PHP fallback until the block version is verified.

## Cutover and rollback

- Do the work on a staging copy of production data. Export the DB and `wp_template*` posts first.
- Keep the old theme installed and inactive; switching back is the rollback. Note that Customizer theme mods are per theme and persist.
- Keep CPT/taxonomy registration in a plugin so switching themes does not delete content access.
- Redirects: confirm permalinks unchanged (`wp rewrite flush` is a write; run it only on the target environment during the approved window).

## Verification

Per template type render home, single, page, archive, search with results and empty, 404, a password-protected post, paginated archive, and a post with comments. Check navigation at mobile/desktop, legacy shortcodes, widgets area replacement, image sizes, editor/front parity, RTL and a long translation, and `wp_head`/`wp_footer` output (analytics, plugin scripts). Visual diff against the pre-migration site; a new home page screenshot alone does not prove the migration.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/themes/block-themes/
- https://developer.wordpress.org/themes/core/theme-structure/
- https://developer.wordpress.org/themes/global-settings-and-styles/introduction-to-theme-json/
- Core source read (trunk, 2026-10-08): `theme.php` lists `block-template-parts` as a theme support (since 6.1) and `class-wp-theme.php` `is_block_theme()` checks `templates/index.html`. The earlier Trac #64241 / changeset 54176 reference came from a search result and was not re-read.
