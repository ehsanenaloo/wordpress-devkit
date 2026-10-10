---
name: wp-devkit-theme-development
description: Build, debug or review classic, child, hybrid and block themes: template hierarchy and Site Editor overrides, theme.json versions and style layers, patterns and parts, fonts and images, classic-to-block migration. Not for block internals (block skill) or visual redesign (ui-design).
---

# Theme rendering and customization

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations, clearing Site Editor customizations or untrusted runtime execution. Implementation applies only when the request authorizes changes.

## Inputs

Theme type, active and parent theme, oldest and newest supported WordPress, failing URL and viewport, selected template, `theme.json`, and whether the Site Editor holds saved overrides. Inspect project evidence first; ask only what changes the decision.

## Boundaries

- Block registration, `save`, deprecations, Interactivity: `wp-devkit-block-development`.
- Visual redesign, journeys, tokens as design decisions: `wp-devkit-ui-design`.
- Plugin-owned behavior (CPTs, shortcodes, integrations): keep out of presentation changes.
- Escaping/authorization depth: `wp-devkit-security-review`; WCAG conformance: `wp-devkit-wcag-review`.

## Code Review Workflow

1. Determine the theme type and resolve the request through the template hierarchy; check database overrides before editing a file (`references/template-ownership-and-hierarchy.md`).
2. Resolve styles across core, theme, child and user layers; match `theme.json` version and features to the oldest supported WordPress (`references/theme-json-and-styles.md`).
3. Inspect patterns, parts, enqueueing, images, fonts, i18n and RTL (`references/patterns-assets-and-i18n.md`). Keep plugin-owned behavior out of the theme.
4. For conversion, inventory templates, menus, widgets, shortcodes, Customizer mods and URLs, map each to a destination and keep a rollback (`references/classic-to-block-migration.md`).
5. Use rendered evidence (screens at several widths, keyboard, long translations, RTL). Report missing observations; do not edit templates or user styles during review.

Read `references/theme-development-workbook.md` for the decision table, symptoms, false positives, severity and acceptance checks.

## Implementation workflow

State expected behavior and the owning layer. Change the owner, not a shadowed file. Preserve user customizations; export before any reset. Keep the parent relationship and text domain in child themes. Run the workbook's acceptance checks and report unavailable ones as unexecuted. Deployment and live maintenance need their own scope.

## Search Patterns for Quick Detection

Read-only leads from the first-party root. Matches are candidates; no match proves nothing. Exit 0 = match, 1 = none, 2 = error.

```sh
# identity and parent
rg -n -g '*.{css,php}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'Theme Name:|Template:|Requires PHP:|Requires at least:|Text Domain:' .
# theme.json and tokens
rg -n -g '*.json' -g '!**/{vendor,node_modules,build,dist}/**' -e '"(version|\$schema|settings|styles|fontSizes|spacingSizes|defaultFontSizes|defaultSpacingSizes|palette|useRootPaddingAwareAlignments|fontFace)"' .
# templates, parts, saved ownership
rg -n -g '*.{html,php}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'wp:template-part|wp:post-content|wp:query|get_template_part|block_template_part|wp_template|wp_global_styles' .
# classic lifecycle and loops
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist}/**' -e 'after_setup_theme|wp_head|wp_footer|wp_body_open|have_posts|the_post|wp_reset_postdata|query_posts|pre_get_posts|add_theme_support' .
# patterns and block styles
rg -n -g '*.{php,json}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'Slug:|register_block_pattern|register_block_style|wp_enqueue_block_style|add_editor_style|enqueue_block_assets' .
# assets, images, fonts
rg -n -g '*.{php,html,css,json}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'wp_enqueue_(script|style)|wp_get_attachment_image|srcset|loading=|fetchpriority|fonts\.(googleapis|gstatic)|@font-face' .
# output and legacy surfaces
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist}/**' -e 'echo\s+\$|esc_(html|attr|url)|wp_kses|do_shortcode|dynamic_sidebar|register_nav_menus|get_stylesheet_directory' .
```

Reading the leads: `query_posts` and a loop without `wp_reset_postdata()` matter only when later template tags use the main post; third-party font hosts matter only with a consent/GDPR basis and a performance cost; `get_stylesheet_directory` in a child theme matters only when the file lives in the parent.

## Output Format

Lead with the result and reviewed scope. Confirmed concern: `file:line`, actor, trigger, reachable path, impact, confidence, minimal fix, regression check. Keep candidates and "not established" items separate. Implementation: owner layer, changed files, commands with exit codes, widths/locales checked, unexecuted checks, rollback. A passing render at one width does not establish other widths, locales, plugins or saved user styles.
