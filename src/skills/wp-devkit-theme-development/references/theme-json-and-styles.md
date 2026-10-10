# theme.json, style layers and variations

Contents: versions, layering, presets, fonts, variations, custom CSS, filters, debugging, sources.

## Versions and schema

- `version` controls backward compatibility; `$schema` only drives editor hints. Use a versioned schema URL matching the minimum supported WordPress (for example `https://schemas.wp.org/wp/6.6/theme.json`) or `trunk`.
- Version 2: WordPress 5.9+ (dev note https://make.wordpress.org/core/2022/01/08/updates-for-settings-styles-and-theme-json/). Version 3: the dev note is tagged for 6.6 and recommends updating once the minimum supported WordPress is 6.6 (it does not name the introducing release outright; trunk has `WP_Theme_JSON::LATEST_SCHEMA = 3`). Older versions keep working.
- v3 breaking change: presets using the default slugs (`small`, `medium`, `large`, `x-large` for font sizes; `20` to `80` for spacing sizes) no longer replace the defaults. Set `settings.typography.defaultFontSizes` and/or `settings.spacing.defaultSpacingSizes` to `false` to override them. `spacingSizes` and `spacingScale` are merged and sorted by slug (`spacingSizes` wins on equal slugs). Classic themes get `default-font-sizes` / `default-spacing-sizes` supports. Comments on the dev note report cases where default variables persisted; test the generated CSS.
- Child and parent themes should be moved together; verify merged output rather than assuming.

## Layers (lowest to highest)

WordPress core defaults, block-level defaults, parent theme, child theme, user Global Styles (database), plus block-level user edits in content (the child-themes handbook page gives default, parent, child, user; trunk `WP_Theme_JSON_Resolver` applies the `default`, `blocks`, `theme` and user layers). When a value does not apply, check layers top-down, then specificity of custom CSS. Inspect resolved values with `wp eval 'echo wp_json_encode( wp_get_global_settings( array( "color", "palette" ) ) );'` and `wp_get_global_styles()` (read-only).

## Practical rules

- Prefer `settings`/`styles` over custom CSS so users can edit through Styles and avoid specificity fights; keep CSS only for what theme.json cannot express (`styles.css` string or `style.css`).
- Use semantic preset slugs (`primary`, `surface`) rather than names tied to a value; they survive variations.
- `settings.layout.contentSize`/`wideSize` plus `useRootPaddingAwareAlignments: true` for full-width blocks that respect root padding.
- Fluid typography: `settings.typography.fluid: true` (per size `fluid` true/false/object with `min`/`max`); sizes below 14px stay static by default; verify with long headings at narrow widths.
- Fonts: bundle with `fontFamilies[].fontFace[]` and `src: ["file:./assets/fonts/x.woff2"]` (paths relative to theme.json). Declare `fontWeight` as range (`"300 800"`), `fontStyle`, `fontDisplay: swap`. Licensing must permit self-hosting. Avoid third-party font CDNs unless consent and GDPR basis are documented.
- Appearance tools: `appearanceTools: true` enables a set of controls; list controls explicitly when the theme must stay restrictive.
- `customTemplates`, `templateParts` (with `area`), `patterns` (Pattern Directory slugs) are metadata only; files still live in `/templates`, `/parts`.

## Style variations

- Global style variations: JSON files in `/styles`, optional `title`; selected in Styles and saved to the database as a user customization, so later edits to the variation file do not reach sites that already applied it (switch away and back).
- Block style variations (`.is-style-{name}`): `register_block_style()` on `init` with `name`, `label`, `inline_style`; the handbook warns `style_handle` currently loads in the editor only, not on the front end. Core variations (Button outline, Image rounded, Table stripes...) can be tuned in `styles.blocks.{block}.variations.{name}`; the handbook says custom-registered (`register_block_style`) styles cannot be styled through theme.json (see the section styles note below for partial-registered variations).
- Section styles are a WordPress 6.6 feature (dev note https://make.wordpress.org/core/2024/06/24/section-styles/): block style variation partial JSON files in `/styles` with `title`, `slug` and `blockTypes`, which register the variation and style it. Stated 6.6 limits: only root styles via Global Styles, no variation-level `settings`, no Style Book preview; defining shared variations under `styles.variations` is marked not recommended. The block-style-variations handbook page as served still says custom-registered styles cannot be customized via theme.json, which conflicts with the dev note for partial-registered variations; test on the target version.

## Per-block CSS loading

`wp_enqueue_block_style( $block_name, array( 'handle' => ..., 'src' => ..., 'path' => ... ) )` (5.9+) loads CSS only when the block renders if on-demand block assets are active (`wp_should_load_block_assets_on_demand()`, 6.8+, filter `should_load_block_assets_on_demand`; its default follows `wp_should_load_separate_core_block_assets()` and the `should_load_separate_core_block_assets` filter, which block themes opt into by default and classic themes can enable). Do not use handles of the form `core-{block}-style`; WordPress reserves them. Provide `path` so CSS can be inlined and `-rtl.css` is swapped for RTL sites.

## Filters (PHP)

`wp_theme_json_data_default`, `wp_theme_json_data_theme`, `wp_theme_json_data_user` let code modify data programmatically through `WP_Theme_JSON_Data::update_with()`. Treat as last resort; they hide values from static review. Confirmed in trunk `class-wp-theme-json-resolver.php`: `wp_theme_json_data_default`, `wp_theme_json_data_theme`, `wp_theme_json_data_blocks` and `wp_theme_json_data_user`; `WP_Theme_JSON_Data::update_with()` since 6.1.

## Debug

| Symptom | Evidence | Fix |
| --- | --- | --- |
| Palette change not visible | resolved `wp_get_global_settings`; user Global Styles override | explain override; do not delete user data silently |
| Default presets still appear after adding mine | v3 `default*` flags, version | set `defaultFontSizes`/`defaultSpacingSizes` false |
| Editor and front differ | wrapper classes, `add_editor_style`, layout settings | align layout and style sources |
| Invalid JSON ignored | schema validation in editor, `json_last_error_msg()` | fix syntax, keep `$schema` |
| Font blocked | console CSP/CORS, font path | correct `file:` path and server MIME |

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/themes/global-settings-and-styles/introduction-to-theme-json/
- https://developer.wordpress.org/themes/global-settings-and-styles/styles/
- https://developer.wordpress.org/themes/global-settings-and-styles/settings/typography/
- https://developer.wordpress.org/themes/global-settings-and-styles/style-variations/
- https://developer.wordpress.org/themes/features/block-style-variations/
- https://make.wordpress.org/core/2024/06/19/theme-json-version-3/
- https://developer.wordpress.org/reference/functions/wp_enqueue_block_style/
- https://make.wordpress.org/core/2024/06/24/section-styles/
- https://make.wordpress.org/core/2022/01/08/updates-for-settings-styles-and-theme-json/
- Core source read (trunk, 2026-10-08): `class-wp-theme-json-resolver.php`, `class-wp-theme-json-data.php`, `script-loader.php`, `block-supports/typography.php` (default 14px fluid minimum). Unverified: whether the dev-note report that `defaultFontSizes`/`defaultSpacingSizes: false` sometimes left default variables is fixed in your WordPress version; test the generated CSS.
