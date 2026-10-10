# WordPress UI surfaces and ownership

Contents: surface map, editor/frontend parity, admin UI, page builders, change ownership, sources.

## Surface map: find the owner before designing

| Surface | Owner of markup/style | Typical levers |
| --- | --- | --- |
| Block theme front end | `theme.json` (settings, styles, variations), templates, patterns, block CSS | tokens in theme.json, `styles.blocks.*`, `wp_enqueue_block_style` |
| Classic theme front end | PHP templates, `style.css`, Customizer | CSS custom properties, `add_theme_support`, template parts |
| Block editor canvas | iframe, `add_editor_style`, `editorStyle`, `theme.json` | same tokens as front; editor chrome is not themeable |
| Plugin front-end blocks | block `style`/`viewStyle` | scope selectors to `.wp-block-{ns}-{name}` |
| wp-admin screens | WordPress admin CSS, `@wordpress/components` | `wp-components` style dependency; admin color scheme variable `--wp-admin-theme-color` (used by core's own admin styles per Trac changesets; not documented on the components reference, so confirm in the installed core `common.css`) |
| Page builder (Elementor etc.) | builder document in post meta | edit in the builder; verify public output, not only the document |

For wp-admin plugin screens hand off to `wp-devkit-admin-ui-development`; this skill defines the journey and visual rules, that skill owns admin implementation.

## Editor/frontend parity

- Both read the same `theme.json` tokens; parity bugs usually mean a style exists in only one of `style.css`, `editorStyle`, `add_editor_style`.
- The post editor canvas is an iframe: per the block API versions page, WordPress 6.3 iframes it when all registered blocks use apiVersion 3 or higher, 7.0 checks the blocks in the post content, and WordPress 7.1 always iframes it. Admin CSS no longer leaks into content, so styles must be loaded into the iframe explicitly.
- Compare resolved values, not screenshots alone: `getComputedStyle` for font-size, line-height, max-width, spacing at the same viewport.
- Layout width comes from `settings.layout.contentSize`/`wideSize`; a container with hard-coded `max-width` fights it.

## Components

`@wordpress/components` supplies Button, TextControl, Modal, Notice, Popover and others. In WordPress, depend on the `wp-components` style handle so ordering is correct; outside it import the package CSS (`style-rtl.css` for RTL). Popovers render at the end of the document body unless a `Popover.Slot` is rendered higher in the tree (Popover component docs). Check the `wp-components` handle and the `style-rtl.css` file name against the installed WordPress and `@wordpress/components` package. Prefer these over bespoke controls for admin and editor UI: they carry keyboard and ARIA behavior.

## Changing a shared token (ownership checklist)

1. Find the source (theme.json preset, CSS custom property, Figma variable) and generated outputs.
2. List consumers: `rg -n '\-\-wp--preset--color--accent|var\(--accent' -g '*.{css,json,php,html}'`.
3. Check user Global Styles overrides in the database; they can mask or conflict with the change.
4. Re-run contrast on every foreground/background pairing the token touches.
5. Document deprecation if a token is renamed; keep the old name as an alias for one release.

## Sources

Research date: 2026-10-08.

- https://developer.wordpress.org/block-editor/reference-guides/components/
- https://developer.wordpress.org/themes/global-settings-and-styles/introduction-to-theme-json/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-api-versions/
