# Visual regression, devices and performance

Define a reproducible rendering matrix before declaring a visual change safe. Contents: matrix, Playwright method, review rules, performance evidence, a11y automation, sources.

## Matrix

Record browsers and versions, OS, viewport widths, orientation, device pixel ratio, zoom, locale, direction (LTR/RTL), color scheme, reduced-motion and forced-colors preferences, and whether touch is emulated. A minimal pack: Chromium plus WebKit and Firefox for layout-sensitive work; 360, 768, 1280 px; LTR and RTL; one long-translation locale.

## Playwright method

```ts
import { test, expect } from '@playwright/test';
test('pricing page', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/pricing/');
  await page.mouse.move(-1, -1); // remove hover state
  await expect(page).toHaveScreenshot('pricing.png', { fullPage: true, maxDiffPixels: 100 });
});
```

- Reference images are created on first run and stored per browser and platform; the docs advise running tests in the same environment that produced the baselines (use one pinned container or runner image in CI).
- `threshold` (default 0.2) and `maxDiffPixels` set tolerance (`maxDiffPixels` and `maxDiffPixelRatio` have no fixed default; both are configurable in `TestConfig.expect`); use `stylePath` or `mask` to hide volatile elements; `animations` defaults to `"disabled"` and `caret` to `"hide"` (Playwright `toHaveScreenshot` API reference). Check the installed Playwright version for option availability.
- Deterministic fixtures: fixed content and dates, stubbed third-party widgets, self-hosted or stable fonts, `wp-env`/Playground seed or a snapshot; mock network randomness.
- Capture the editor canvas separately from the front end.

Update baselines only with `npx playwright test --update-snapshots` after a reviewed, documented decision tied to the design change; never refresh to turn CI green (engineering contract rule 8).

## Reviewing diffs

A pixel diff is a lead. Inspect clipping, wrapping, focus visibility, reading order and states manually. A passing diff does not prove accessibility, correct behavior or cross-device parity beyond the matrix.

## Performance evidence (Core Web Vitals)

Thresholds at the 75th percentile, per device class: LCP at most 2.5 s, INP at most 200 ms, CLS at most 0.1. Field data (CrUX or your own RUM) is the primary measure; lab data (Lighthouse, WebPageTest) catches regressions but Lighthouse cannot measure INP (it reports Total Blocking Time as a proxy). Report URL, build, device, network, sample and date; label lab vs field. Do not infer production performance from one screenshot or one Lighthouse run.

## Automated accessibility checks

`@axe-core/playwright`: `new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze()` (`wcag22aa` and the other tags are listed in the axe-core API tag table; confirm in the installed axe-core version). Reveal dynamic UI first, scan again after opening menus/dialogs, and avoid `exclude()` on large subtrees. Automation finds only a subset of problems; keyboard, screen-reader and zoom checks remain manual.

## Sources

Research date: 2026-10-08.

- https://playwright.dev/docs/test-snapshots
- https://playwright.dev/docs/accessibility-testing
- https://web.dev/articles/vitals

Further sources: [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots), [Playwright emulation](https://playwright.dev/docs/emulation).
