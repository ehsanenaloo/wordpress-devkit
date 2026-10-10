# Design systems and tokens

Treat tokens as a versioned contract shared by `theme.json`, CSS, blocks and design tools. Contents: token model, mapping to WordPress, change procedure, checks, pitfalls, sources.

## Token model

- Semantic names over literal ones: `surface`, `text-muted`, `action-primary`, `focus-ring`, not `blue-500` at the component level. Keep a primitive layer (raw palette/scale) beneath semantic aliases.
- Categories: color, typography (family, size, line-height, weight), spacing, sizing, radius, border, shadow/elevation, motion (duration, easing), z-index layers, breakpoints/containers.

## Mapping to WordPress

| Token | WordPress carrier | Output |
| --- | --- | --- |
| Color palette | `settings.color.palette` | `--wp--preset--color--{slug}` and `.has-{slug}-color` classes |
| Font sizes | `settings.typography.fontSizes` (+ `fluid`) | `--wp--preset--font-size--{slug}` |
| Spacing | `settings.spacing.spacingSizes` | `--wp--preset--spacing--{slug}` |
| Custom values | `settings.custom` | `--wp--custom--{path}` |
| Element/block styles | `styles.elements`, `styles.blocks` | generated global CSS |

theme.json version 3 (WordPress 6.6+) no longer lets theme presets with default slugs replace the defaults automatically; set `defaultFontSizes`/`defaultSpacingSizes` (and the existing `defaultPalette`) to `false` when reusing those slugs (the dev note reports mixed community results, so test) (`wp-devkit-theme-development` has the detail). Generated CSS must not be hand-edited. If Figma is used, record the variable collection, mode and component-to-code mapping; a design file is intent, not proof of implementation.

## Change procedure

1. Identify source of truth and generators. 2. List consumers with `rg` and the Site Editor (user Global Styles can override). 3. State the compatibility impact: rename vs value change vs removal; keep deprecated aliases for a release. 4. Re-check contrast for each foreground/background pair (text 4.5:1, large text 3:1, UI components and focus indicators 3:1 per WCAG 1.4.3/1.4.11). 5. Verify editor/front parity and dark/forced-colors modes if shipped. 6. Record in the changelog.

## Component documentation

Anatomy, variants, and every state (default, hover, `:focus-visible`, active, disabled, loading, empty, error, success), plus responsive and RTL behavior. Include what the component must not do (for example, no hard-coded colors).

## Pitfalls

- Repeated literals are not by themselves a broken system; verify they should share a token.
- Tokens defined in theme.json and again in `:root` CSS diverge silently; pick one origin.
- Plugin presentation leaking into theme tokens; plugin behavior stays out of the theme.
- Token renames without alias break child themes and custom CSS.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/themes/global-settings-and-styles/introduction-to-theme-json/
- https://make.wordpress.org/core/2024/06/19/theme-json-version-3/
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/

## Sources

Researched 2026-10-08: [theme.json reference](https://developer.wordpress.org/themes/global-settings-and-styles/), [Design Tokens Community Group format](https://www.designtokens.org/tr/drafts/format/).
