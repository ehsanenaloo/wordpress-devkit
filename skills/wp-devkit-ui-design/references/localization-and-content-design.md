# Localization, RTL and content design

Design content behavior for every supported locale before calling UI complete. Contents: locale matrix, WordPress i18n rules, RTL, stress data, content states, sources.

## Locale matrix

For each supported locale: language and script, plural categories, date/time/number/currency formats, timezone, direction, and whether a translation exists. Record unsupported or unreviewed locales rather than implying coverage.

## WordPress i18n rules that affect UI

- Complete translatable sentences with placeholders: `sprintf( __( 'Posted by %s on %s', 'td' ), $author, $date )` (add a `/* translators: 1: author 2: date */` comment); never concatenate fragments.
- Plurals via `_n( '%s item', '%s items', $n, 'td' )`; context with `_x()`; escape late with `esc_html__()`/`esc_attr__()`.
- In JavaScript use `@wordpress/i18n` (`__`, `_n`, `sprintf`) with `wp_set_script_translations()`; for `theme.json` and `block.json` strings use the `textdomain` mechanism.
- Text domain matches the plugin/theme slug and is a literal string: the plugin handbook says not to use variables or constants for it. Translator comments must start with `translators:` and be the last comment before the call; use numbered placeholders such as `%1$s` to let translators reorder.
- Dates/numbers: `wp_date()` (localized date, since 5.3.0), `number_format_i18n()` (core function, not covered by the fetched i18n page); do not hard-code separators or `d/m/Y`.

## RTL

- Logical properties (`margin-inline-start`, `padding-inline`, `inset-inline-end`, `text-align: start`, `border-start-start-radius`) instead of left/right. For legacy CSS, WordPress loads `rtl.css` or `*-rtl.css` variants.
- Mirror direction-bearing icons (arrows, back/forward, progress) but not logos, media controls with universal meaning, or numbers/phone numbers.
- Test mixed direction: Latin product names, URLs, emails and numbers inside Arabic or Hebrew text; use `dir="auto"` or `<bdi>` for user-generated strings.
- Set `lang` and `dir` on the document and on inline foreign-language passages (WCAG 3.1.1, 3.1.2).

## Stress data

Pseudolocalization (accent plus roughly 30-40 percent expansion), a German-like long compound, CJK without spaces (no break opportunities), emoji, 100+ character names, one-letter names, empty and very large counts, long unbroken tokens. Check wrapping, truncation (`text-overflow` hiding meaning), tooltips and focus order.

## Content states and tone

Headings, labels, buttons, help text, errors, empty states, consent text and alt text each need: clear task language, no jargon, no blame in errors, a next action, and a screen-reader reading that makes sense alone ("Read more" links need context via text or `aria-label` that includes the visible text). Alt text conveys purpose, not file names; decorative images use `alt=""`.

## Sources

Research date: 2026-10-08.

- https://developer.wordpress.org/apis/internationalization/
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/ (WCAG 2.2 context; 3.1.x unchanged from 2.1)

Further sources: [W3C internationalization: bidirectional text](https://www.w3.org/International/articles/inline-bidi-markup/), [WordPress i18n handbook](https://developer.wordpress.org/apis/internationalization/).
