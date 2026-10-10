# Theme development workbook

Apply [the engineering contract](engineering-contract.md) first. Contents: evidence, decision table, symptom table, false positives, severity, acceptance, reports, sources.

## Evidence to collect

Theme type (classic, hybrid, block, child), active and parent theme (`wp theme list`), oldest and newest supported WordPress, failing URL and viewport, the template the request resolves to, `theme.json` (and `/styles`), whether the Site Editor has saved overrides (`wp_template`, `wp_template_part`, `wp_global_styles`), active plugins that inject templates, styles or blocks, and the locale and direction.

## Decision table

| Decision | Rule |
| --- | --- |
| Where to change | The layer that owns the output: user DB override, child, parent, plugin. Explain an override before touching it. |
| theme.json version | 2 for min WP 5.9 to 6.5, 3 once min WP is 6.6; apply the v3 `default*` flags when custom font/spacing presets reuse default slugs. |
| CSS vs theme.json | theme.json for tokens and block styles users may edit; CSS for behavior it cannot express; `wp_enqueue_block_style` for per-block CSS. |
| Hybrid vs full block | See [classic-to-block-migration.md](classic-to-block-migration.md). Do not convert as a side effect of a bug fix. |
| Business logic | CPTs, taxonomies, shortcodes and integrations belong in plugins; a theme switch must not remove content access. |
| Images | Let core assign `loading`/`fetchpriority`; override only for a measured LCP element. |

## Symptom table

| Symptom | Evidence | Owner | Reference |
| --- | --- | --- | --- |
| File edit has no effect | resolved template vs DB override | template ownership | [template-ownership-and-hierarchy.md](template-ownership-and-hierarchy.md) |
| Wrong post data after a loop | missing `wp_reset_postdata` | classic loop | [template-ownership-and-hierarchy.md](template-ownership-and-hierarchy.md) |
| Color/font not applied | resolved global settings and user styles | style layers | [theme-json-and-styles.md](theme-json-and-styles.md) |
| Default presets still show | theme.json `version`, `default*` flag | v3 migration | [theme-json-and-styles.md](theme-json-and-styles.md) |
| Pattern missing | header, slug, categories, `Inserter` | patterns | [patterns-assets-and-i18n.md](patterns-assets-and-i18n.md) |
| Hero image lazy-loaded | markup attributes, LCP | images | [patterns-assets-and-i18n.md](patterns-assets-and-i18n.md) |
| Lost menus/widgets after switch | inventory | migration | [classic-to-block-migration.md](classic-to-block-migration.md) |

## Looks wrong but is fine

- A saved Site Editor template overriding a theme file (intentional customization).
- A classic theme with `theme.json` and `block-template-parts` but PHP templates (hybrid).
- `theme.json` at version 2 on a theme supporting WordPress below 6.6.
- Missing `patterns/`, `styles/` or `parts/` folders.
- Logo or assets resolved from the parent theme in a child theme through `get_theme_file_uri()` (parent fallback is intended; `get_stylesheet_directory_uri()` would not fall back).
- Custom CSS next to theme.json for behavior it cannot express (focus rings, animations).
- `add_theme_support( 'post-thumbnails' )` in a block theme.

Insufficient evidence outcome: if only source is available (no resolved template, DB state or rendered page), report ownership as "not established" and name the command or screenshot needed.

## Severity

CRITICAL: unescaped attacker-influenced output in a template or pattern that is reachable, or a migration that makes published content inaccessible. WARNING: broken template selection for a content type, lost customizations on update, editor/front divergence, missing `wp_head`/`wp_footer`, failing a11y basics. INFO: optional features, schema version lag with no failing behavior.

## Acceptance checks

1. `php -l` / `phpcs --standard=WordPress` (project config) for PHP, `npx wp-scripts lint-style` if present, and JSON validity of `theme.json` and `/styles`.
2. Resolved settings check: `wp eval 'echo wp_json_encode( wp_get_global_settings( array( "typography","fontSizes" ) ) );'` shows the intended presets.
3. Render check per template type with and without content (empty search, 404, long title, missing featured image), at 360, 768, 1280 px, 200% zoom, RTL and a long translation.
4. Site Editor opens each template and part without validation warnings; saved customizations survive a theme update (test with a staged customization).
5. Theme Check plugin or the .org theme review requirements when distributing.

A pass does not prove performance on real devices, plugin interactions, or every user's saved Global Styles.

## Reports

Review finding: `file:line` | actor | trigger | reachable path | impact | confidence | fix | regression. Change report: owner layer, files, commands and exit codes, screenshots/widths, unexecuted checks, rollback.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/themes/templates/template-hierarchy/
- https://developer.wordpress.org/themes/global-settings-and-styles/introduction-to-theme-json/
- https://make.wordpress.org/core/2024/06/19/theme-json-version-3/
