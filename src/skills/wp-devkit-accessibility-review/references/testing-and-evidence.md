# Testing and evidence for accessibility work

Contents: [What automation can and cannot see](#what-automation-can-and-cannot-see) - [Manual script](#manual-script) - [Assistive technology matrix](#assistive-technology-matrix) - [axe with Playwright](#axe-with-playwright) - [Rendered-DOM regression assertions](#rendered-dom-regression-assertions) - [Evidence record](#evidence-record) - [What a pass does not prove](#what-a-pass-does-not-prove) - [Sources](#sources)

## What automation can and cannot see

axe-core (and tools built on it: Lighthouse, Pa11y variants, `@axe-core/playwright`) tests the DOM it is given at that moment. It finds missing names, invalid ARIA, many contrast failures, duplicate ids and missing landmarks. It reports uncertain items in `incomplete` ("needs review"); those are manual work, not passes. It cannot judge focus order, key handling, usefulness of alt text or labels, announcement quality, reading order, motion, timing or whether a custom widget follows its pattern. Rules run only on the state present when `analyze()` is called, so scan after opening dialogs, expanding menus and triggering errors. Iframes need axe present in each frame; open shadow DOM is traversed. Tag filters are cumulative only if you list every tag you want.

## Manual script

Run in a fresh profile at 100% zoom, then repeat the layout rows.

1. Keyboard only (no pointer): reach and operate every control; Tab and Shift+Tab order matches reading order; visible focus indicator on each stop; Enter/Space/Escape/arrow behavior matches the pattern; no trap; skip link works.
2. Focus lifecycle: open and close every overlay; trigger, remove or re-render the opener; complete a destructive action; submit invalid data. Note where focus lands each time.
3. Zoom: browser zoom 200% and 400% (equivalent to 320 CSS px width); text-only zoom 200%; no horizontal scroll for text content; no clipped controls; sticky bars do not hide the focused element.
4. Text spacing: apply the WCAG spacing values (line height 1.5, paragraph spacing 2 times, letter spacing 0.12 em, word spacing 0.16 em) with a bookmarklet or user stylesheet; nothing clips or overlaps.
5. Color and contrast: measure text (4.5:1, 3:1 for large text) and UI component/state boundaries (3:1) in default, hover, focus, active, disabled-looking and error states; check dark mode and forced colors (Windows High Contrast / `forced-colors: active`).
6. Motion and timing: emulate `prefers-reduced-motion: reduce`; pause controls for auto-moving content over five seconds; session timeout warnings.
7. Screen reader: walk the journey and record what is announced for names, roles, states, errors, live updates and page changes.
8. Mobile: portrait and landscape, system text size increase, touch target size and spacing, VoiceOver/TalkBack swipe through any overlay.

## Assistive technology matrix

Choose pairs the audience actually uses; the choice is yours to justify, not fixed by this skill. A defensible minimum for a public site: NVDA with Firefox or Chrome on Windows, VoiceOver with Safari on macOS and iOS, TalkBack with Chrome on Android; add JAWS with Chrome or Edge for enterprise audiences. Record screen reader, browser and OS versions in the evidence. One pair passing says nothing about the others. Voice control (Dragon, Voice Control) is the check for label-in-name issues.

## axe with Playwright

```ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const TAGS = [ 'wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa' ];

test( 'filter dialog has no detectable violations', async ( { page } ) => {
	await page.goto( '/shop/' );
	await page.getByRole( 'button', { name: 'Filters' } ).click();
	await page.getByRole( 'dialog', { name: 'Filters' } ).waitFor();

	const results = await new AxeBuilder( { page } )
		.withTags( TAGS )
		.include( '[role="dialog"], dialog' )
		.analyze();

	expect( results.violations ).toEqual( [] );
	// Review results.incomplete manually; do not ignore it.
} );

test( 'checkout error state', async ( { page } ) => {
	await page.goto( '/checkout/' );
	await page.getByRole( 'button', { name: 'Place order' } ).click();
	await expect( page.locator( '[aria-invalid="true"]' ).first() ).toBeVisible();
	const results = await new AxeBuilder( { page } ).withTags( TAGS ).analyze();
	expect( results.violations ).toEqual( [] );
} );
```

Rules: `exclude()` and `disableRules()` silence checks, so each needs a written reason and an owner (see the contract: never broaden ignores to turn CI green). `wcag22aa` is an axe tag name; confirm your installed axe-core version includes the rule you need (for example target size). Run against a seeded disposable site, not production. Do not treat a lower violation count as a score.

## Rendered-DOM regression assertions

Assert behavior, not only absence of axe violations. Role-based locators double as name checks.

```ts
test( 'disclosure menu follows its contract', async ( { page } ) => {
	await page.goto( '/' );
	const toggle = page.getByRole( 'button', { name: 'Products' } );
	await expect( toggle ).toHaveAttribute( 'aria-expanded', 'false' );
	await toggle.focus();
	await page.keyboard.press( 'Enter' );
	await expect( toggle ).toHaveAttribute( 'aria-expanded', 'true' );
	await expect( page.getByRole( 'link', { name: 'Shoes' } ) ).toBeVisible();
	await page.keyboard.press( 'Escape' );
	await expect( toggle ).toHaveAttribute( 'aria-expanded', 'false' );
	await expect( toggle ).toBeFocused();
} );

test( 'modal returns focus', async ( { page } ) => {
	await page.goto( '/' );
	const opener = page.getByRole( 'button', { name: 'Open cart' } );
	await opener.click();
	await expect( page.getByRole( 'dialog' ) ).toBeVisible();
	await page.keyboard.press( 'Escape' );
	await expect( opener ).toBeFocused();
} );
```

These prove the scripted keys and states only. They run in Chromium unless projects add Firefox/WebKit.

## Evidence record

```text
Build: commit or release id, WordPress/theme/plugin versions, environment URL (no secrets)
Journey and state: steps, user type, viewport, zoom, locale
Tools: axe-core and @axe-core/playwright versions, Playwright version, browser versions
Assistive tech: screen reader + version, browser + version, OS
Result per check: pass / fail / not run, with artifact (trace, screenshot, recording, notes)
Commands run: command, exit status
Not tested: list
```

Keep the same record for the retest on the same build. Redact personal data from recordings and traces.

## What a pass does not prove

A clean axe run, a passing Playwright keyboard test or one screen-reader walkthrough proves only the sampled states in that environment. It does not prove conformance, other assistive technology, content added later, third-party iframes, or real-user usability. Conformance status is produced by `wp-devkit-wcag-review` with a defined scope.

## Sources

Reviewed 2026-10-08.

- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)
- [axe-core API (tags, runOnly, incomplete, iframes)](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md)
- [WCAG 2.2 Text Spacing understanding](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html)
- [WCAG-EM](https://www.w3.org/TR/WCAG-EM/)
