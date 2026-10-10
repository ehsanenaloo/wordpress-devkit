# WordPress accessibility surfaces

Contents: [Standard and ownership](#standard-and-ownership) - [Theme basics](#theme-basics) - [Core APIs worth knowing](#core-apis-worth-knowing) - [Block editor and blocks](#block-editor-and-blocks) - [Admin screens](#admin-screens) - [WooCommerce](#woocommerce) - [Internationalization and multisite](#internationalization-and-multisite) - [Version notes](#version-notes) - [Sources](#sources)

Use this file to decide who owns a defect and which core mechanism already solves it. Apply the engineering contract first.

## Standard and ownership

WordPress states that code in the project is expected to meet WCAG 2.2 level AA. Plugins and themes that target the wordpress.org directory, and enterprise clients, are usually held to the same bar. The theme directory "accessibility-ready" tag has a published checklist (skip link, named landmarks, full keyboard operation, labeled fields, logical headings, underlined body links, descriptive links, contrast, alt text, reflow and text spacing, no unexpected context change, warning before new-window links, hover/focus content, accessibility statement, screen reader text).

Before writing a finding, identify the owner of the markup:

| Output comes from | Typical fix location |
| --- | --- |
| Core template function or block (`get_search_form`, `wp_nav_menu`, `comment_form`, core blocks) | Theme support flags and arguments first; report upstream only after reproducing on a default theme. |
| Theme template or `theme.json` | Theme PR. Check child-theme overrides and Site Editor user customizations (stored in the database, not in files). |
| Plugin shortcode, block or admin page | Plugin PR; the page builder or widget vendor if the markup is vendor generated. |
| WooCommerce template override in the theme | Update the override against the current core template (System Status lists overridden and outdated templates). |
| Third-party embed (maps, chat, consent banner, payment iframe) | Vendor; record as a third-party boundary, not a first-party defect. |

## Theme basics

```php
<?php
// Opt in to semantic markup for core-generated forms and captions.
add_action( 'after_setup_theme', static function () {
	add_theme_support(
		'html5',
		array( 'search-form', 'comment-form', 'comment-list', 'gallery', 'caption' )
	);
} );
```

- `html5` accepts `comment-list`, `comment-form`, `search-form`, `gallery`, `caption`. The `script` and `style` values are deprecated as of WordPress 7.0 and unused; do not report their absence.
- Search form: with `search-form` support the default is an `<input type="search">`; a theme `searchform.php` replaces it entirely, so inspect that file. Pass `aria_label` to `get_search_form()` to distinguish several search forms on one page.
- Menus: `wp_nav_menu()` with `container => 'nav'` and `container_aria_label` (WordPress 5.5+) names the landmark. Several `nav` landmarks on a page need distinct names. `Walker_Nav_Menu` sets `aria-current="page"` on the current item; custom walkers and `nav_menu_link_attributes` filters that rebuild attributes can drop it.
- Block themes: core enqueues a skip link for block-template pages (`wp_enqueue_block_template_skip_link()`, WordPress 6.4+). For classic themes, add your own first-in-body link to the main landmark and make the target exist. Do not report a missing skip link on a block theme before checking rendered output.
- `title-tag` support lets core produce the document title; changing titles on route change in a headless or Interactivity-driven page needs an explicit update and announcement.

Visually-hidden text that must stay readable by assistive technology:

```css
.screen-reader-text {
	border: 0;
	clip-path: inset(50%);
	height: 1px;
	margin: -1px;
	overflow: hidden;
	padding: 0;
	position: absolute;
	width: 1px;
	word-wrap: normal !important;
}
.screen-reader-text:focus {
	background: #fff;
	clip-path: none;
	color: #000;
	display: block;
	height: auto;
	padding: 0.75rem 1rem;
	width: auto;
	z-index: 100000;
}
```

The `:focus` variant is for skip links; plain screen-reader text must not become focusable. Do not hide text with `display:none` if it is meant to be read.

Link purpose for repeated "Read more" links (escape and allow only the span):

```php
<?php
function mytheme_read_more_link( $post = null ) {
	$title = get_the_title( $post );
	return sprintf(
		'<a href="%1$s">%2$s<span class="screen-reader-text"> %3$s</span></a>',
		esc_url( get_permalink( $post ) ),
		esc_html__( 'Read more', 'mytheme' ),
		/* translators: %s: post title. */
		esc_html( sprintf( __( 'about %s', 'mytheme' ), $title ) )
	);
}
```

## Core APIs worth knowing

- JavaScript announcement: `import { speak } from '@wordpress/a11y'; speak( message, 'polite' | 'assertive' )`. Default is polite. Classic scripts depend on the core handle `wp-a11y` and call `wp.a11y.speak()`. Use it for results the user did not move focus to (search result counts, "saved", ajax errors). Use assertive sparingly.
- PHP has no announcement API; render a status region or emit JS.
- `wp_admin_notice( $message, $args )` (6.4+) with `type`, `dismissible`, `id`, `additional_classes`, `attributes`, `paragraph_wrap`. Pass `attributes => array( 'role' => 'alert' )` only for urgent failures; routine success notices should be polite status.
- Settings API: `add_settings_error()` and `settings_errors()` render notices after a save; tie field-level messages to inputs with `aria-describedby`.
- `esc_attr__()` / `esc_html__()` for every `aria-label` and screen-reader string so translations are present.

## Block editor and blocks

- Use `@wordpress/components` rather than hand-built controls: `Button` with `label` for icon-only buttons, `VisuallyHidden`, `Modal` (retains focus until dismissed; the docs do not state focus return, so verify it), `Popover`, `Notice`, `Tooltip`. Wrapping them in extra `div`s with click handlers re-creates the problems they solve.
- Generate ids with `useInstanceId`/`useId` so label and `aria-describedby` links stay unique when a block appears many times.
- Dynamic blocks: check the server-rendered `render_callback` output, not only `edit.js`. Duplicate ids from repeated block instances are a common defect.
- Interactivity API directives (`data-wp-on--keydown`, `data-wp-bind--aria-expanded`) keep ARIA state in sync only if you bind it; assert the attribute in the rendered DOM after interaction.
- Block `apiVersion` 3 means the block should work inside the iframed editor (WordPress 6.3 iframes the editor when all registered blocks are version 3+; 7.0 checks the blocks in the post content; the block API versions page says newer releases always iframe): editor-only scripts that target the global `document` can miss canvas content, so resolve elements through the block's own `ownerDocument` (general DOM technique, not in the versions page). Check against the target WordPress version.
- Allow authors to supply alt text, link labels and heading level (`level` attribute) instead of hardcoding; provide a documented default of empty alt only for decorative images.

## Admin screens

- Extend `WP_List_Table` instead of hand-built tables so captions, `scope`, bulk-action labels and keyboard-visible row actions come for free.
- Each setting field needs a `<label for>` (the `label_for` argument of `add_settings_field()`) and description text linked by `aria-describedby`.
- Admin modals: prefer the `Modal` component or native `<dialog>`; the legacy thickbox pattern traps poorly.
- Do not hard-code colors: admin color schemes and high-contrast browser modes change backgrounds. Test with a non-default scheme and with forced colors.
- Notices injected by JavaScript are not announced by arriving in the DOM; call `wp.a11y.speak()` or insert into a pre-existing status region.
- Dashboard widgets and meta boxes are reorderable by keyboard and drag; custom widgets must not break the move buttons.

## WooCommerce

- Classic shortcode checkout and the Checkout block are different code paths with different markup and validation behavior. Test the one the site uses; both if both are reachable.
- Inspect the rendered notice containers (cart/checkout errors) for a live role: the classic error notice template renders `<ul class="woocommerce-error" role="alert">` in current trunk, but other notice types, the Checkout block and older template versions were not verified. Confirm that an error moves the user to the summary or announces it, and that each invalid field is linked to its message.
- Mini-cart drawers, quantity steppers, variation pickers, coupon toggles, gallery zoom and payment iframes are the usual hot spots: each needs the interactive-patterns checks.
- Payment provider iframes are third-party boundaries: verify the host page labels around them, focus entry and exit, and that 3-D Secure challenges are reachable by keyboard.
- Template overrides freeze old markup. Compare `@version` of overrides with the installed WooCommerce templates before attributing a defect to current core.

## Internationalization and multisite

- Set `lang` through `language_attributes()`; mark foreign-language passages with `lang` when content mixes languages. Check RTL with `is_rtl()` and logical CSS properties; screen-reader-only strings must be translatable.
- On multisite, each subsite may run a different theme and locale: sample at least one site per theme and language in scope.
- Truncated or machine-translated labels can break "label in name": visible text and accessible name must stay aligned per locale.

## Version notes

Core behaviors cited above were checked (`container_aria_label` 5.5.0 and the `html5` `script`/`style` deprecation in 7.0.0 re-confirmed in the function reference on 2026-10-08) on 2026-10-08 against the developer reference: `wp_admin_notice` 6.4+, `container_aria_label` 5.5+, block-template skip link function 6.4+, `html5` `script`/`style` deprecated in 7.0. The nav menu `aria-current="page"` is emitted by `Walker_Nav_Menu::start_el()` in current source (confirmed 2026-10-08); its introduction version is unverified. The `wp-a11y` handle is confirmed only as a script dependency in `script-loader.php`; the `@wordpress/a11y` docs do not document classic-script usage, so check the installed WordPress. Determine the target project's minimum WordPress and re-read the function reference before relying on a newer argument.

## Sources

Reviewed 2026-10-08.

- [WordPress accessibility coding standards](https://developer.wordpress.org/coding-standards/wordpress-coding-standards/accessibility/)
- [Theme accessibility-ready required checks](https://make.wordpress.org/themes/handbook/review/accessibility/required/)
- [@wordpress/a11y package](https://developer.wordpress.org/block-editor/reference-guides/packages/packages-a11y/)
- [wp_admin_notice](https://developer.wordpress.org/reference/functions/wp_admin_notice/)
- [add_theme_support (html5 values)](https://developer.wordpress.org/reference/functions/add_theme_support/)
- [get_search_form](https://developer.wordpress.org/reference/functions/get_search_form/)
- [wp_nav_menu](https://developer.wordpress.org/reference/functions/wp_nav_menu/)
- [Walker_Nav_Menu::start_el](https://developer.wordpress.org/reference/classes/walker_nav_menu/start_el/)
- [wp_enqueue_block_template_skip_link](https://developer.wordpress.org/reference/functions/wp_enqueue_block_template_skip_link/)
