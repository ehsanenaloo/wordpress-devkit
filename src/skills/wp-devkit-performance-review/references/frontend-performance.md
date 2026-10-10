# Frontend performance evidence

Researched 2026-10-08. Contents: 1 Method and budgets | 2 LCP | 3 INP | 4 CLS | 5 WordPress asset APIs | 6 Images and fonts | 7 Speculative loading | 8 Third parties | 9 Acceptance

## 1. Method and budgets

Define the journey and budget first. Record build, route, device/CPU throttle, viewport, browser, network, cache state, logged-in state and third-party consent state. Compare equivalent repeated runs; separate field experience from synthetic lab results.

Core Web Vitals "good" at the 75th percentile of field loads, split by device: LCP at most 2.5 s, INP at most 200 ms, CLS at most 0.1 (web.dev). INP replaced First Input Delay as the stable responsiveness metric in 2024. Check the current definitions before a contractual claim.

## 2. LCP

LCP decomposes into four sequential parts: time to first byte, resource load delay, resource load duration, element render delay. Guidance suggests roughly 40% / under 10% / 40% / under 10%; treat that as a diagnostic shape, not fixed millisecond targets, and note that speeding one part can shift time into another.

Diagnose:
1. Identify the actual LCP element (DevTools Performance or Lighthouse "LCP element"). On WordPress it is often the hero image, a block cover background, a featured image, or a heading with a web font.
2. High TTFB: page cache miss, slow origin, redirects, TLS. Fix at the server first (see the other references).
3. Load delay: the browser found the resource late (CSS background image, JS-injected image, lazy-loaded). Make the image an `<img>` in the HTML, or preload it.
4. Load duration: oversize image, no modern format, no responsive `srcset`/`sizes`, slow CDN.
5. Render delay: render-blocking CSS/JS, font blocking, main-thread work, client-side rendering.

WordPress behavior to know (verify on the target version):
- Since 6.3 core adds `fetchpriority="high"` to the image it judges most likely to be the LCP image and omits `loading="lazy"` for images likely in the initial viewport (`wp_get_loading_optimization_attributes()`; filters `wp_omit_loading_attr_threshold` default 3, `wp_min_priority_img_pixels` default 50,000). Explicit `fetchpriority`/`loading` attributes you set are preserved.
- Never lazy-load the LCP image. Do not put `fetchpriority="high"` on more than one or two images. Use `fetchpriority="low"` for early but invisible images such as hidden carousel slides.
- Images that appear through `the_content` filters, shortcodes, theme template code or page builders may bypass core's logic; check the rendered HTML.
- `wp_get_attachment_image()` generates `srcset` and `sizes`; custom `sizes` values must match the layout, or the browser selects an oversize source.

## 3. INP

INP is the longest interaction latency observed (ignoring outliers): input delay, processing time and presentation delay. A page-load score cannot prove interaction latency.

Diagnose with real interactions: DevTools Performance trace with CPU throttling while clicking menus, filters, add-to-cart, form fields; look for long tasks (over 50 ms) around the event. Typical WordPress causes: large jQuery handlers on `click` or `scroll`/`resize` without throttling; layout thrash (reads and writes of layout properties interleaved); tag-manager and consent scripts; heavy React hydration; large DOM (page builders); synchronous `admin-ajax` calls blocking UI feedback; WooCommerce cart fragment refresh on every page.

Fixes: do less in the handler, defer non-urgent work after paint (`requestAnimationFrame` then `setTimeout`, or `scheduler.yield()` behind a feature check such as `globalThis.scheduler?.yield`, since MDN marks it not Baseline), debounce input, use passive listeners, reduce DOM size, remove or delay third parties, give immediate visual feedback before network work. Verify with field data (RUM with attribution through the `web-vitals` library) because INP depends on real devices.

## 4. CLS

Observe the whole journey, not just load: reserve space for images and video (`width`/`height` attributes or `aspect-ratio`; core adds dimensions to attachment images), embeds, ads and banners (cookie bars, promo bars) with fixed-height slots; avoid inserting content above existing content; use `font-display: swap` or `optional` with metric-compatible fallback fonts (`size-adjust`) to limit font-swap shifts; animate with `transform`, not layout properties. Layout shifts within 500 ms after a user input are excluded from the metric, so a shift after a click may not count while one on scroll or timer does.

## 5. WordPress asset APIs

- Enqueue with `wp_enqueue_script()` / `wp_enqueue_style()` only where needed (conditional on the template, block presence or route); handle dependencies; use version strings for caching.
- Loading strategy: since 6.3 pass `array( 'strategy' => 'defer', 'in_footer' => true )` as the fifth argument; strategy is resolved against the dependency tree (a deferred script with a blocking dependent or an "after" inline script can fall back to blocking). Do not add `defer`/`async` by string-replacing in `script_loader_tag`, which ignores dependency order; on cores older than 6.3 the array form is truthy as `$in_footer`, so use `wp_script_add_data( $handle, 'strategy', 'defer' )` as a fallback.
- Since 6.9 scripts and script modules accept `fetchpriority` in `$args`; block view modules and `comment-reply` default to low.
- Script Modules (`wp_register_script_module()` / `wp_enqueue_script_module()`, 6.5+) are deferred ES modules; the Interactivity API uses them.
- 6.9 front-end changes: classic themes load block styles on demand (less CSS than the combined `wp-block-library`); styles inline up to a raised 40 KB limit (`styles_inline_size_limit`); assets of blocks that render nothing are dequeued (`enqueue_empty_block_content_assets` to keep); a template-enhancement output buffer exists for HTML post-processing (use the HTML API, never regex on the buffer, and do not force the buffer off). Re-measure after upgrading to 6.9 or later: late-enqueued styles are hoisted, which can change TTFB slightly.
- Removing core assets (`wp-block-library`, `global-styles`, emoji, `wp-embed`, jQuery Migrate) is a trade-off: test every template, the editor and logged-in views; deregistering jQuery breaks dependents.
- Critical CSS: inline only above-the-fold CSS per template and load the rest asynchronously; tools must regenerate on theme/plugin changes. Prefer reducing CSS first.
- Bundles: split by route; avoid shipping the editor bundle to visitors; check `@wordpress/*` packages are externalized to core's copies (use `@wordpress/scripts`, which generates `*.asset.php` dependency lists).
- Heartbeat and `admin-ajax` polling on the front end add requests; see the background reference.
- Cache headers on static assets: long `max-age` with versioned URLs; compression (Brotli/gzip) at the edge.

## 6. Images and fonts

- Serve right-sized, modern formats (WebP, AVIF where supported; WordPress generates WebP sub-sizes when the image library supports it, and AVIF upload and sub-size support exists since 6.5 only when the server image library (Imagick or GD) supports AVIF: verify the target). Set max upload dimensions and compress at upload.
- Lazy-load below-the-fold images and iframes (`loading="lazy"` is on by default for `img` and `iframe` in core).
- Self-host and subset fonts, `preload` only the one or two fonts used above the fold (with `crossorigin`), `font-display` chosen deliberately. Block themes register fonts via `theme.json` font faces; check they are not all preloaded.
- Background images in CSS are discovered late; prefer `<img>` with `object-fit` for LCP candidates.
- Video: poster images, `preload="none"` or `metadata`, lazy embeds (facade for YouTube/Vimeo).

## 7. Speculative loading

WordPress 6.8 added speculative loading using the Speculation Rules API: by default `prefetch` with `conservative` eagerness for eligible same-site links, disabled for logged-in users and sites without pretty permalinks. The `wp_speculation_rules_configuration` filter changes mode (`prefetch` or `prerender`) and eagerness (`conservative`, `moderate`, `eager`) or disables it with `null`; exclude paths with `wp_speculation_rules_href_exclude_paths` (for example `/cart/*`, `/checkout/*`) and use the `no-prerender` class on a link to avoid prerendering. Prerendering executes the page's JavaScript and analytics: check that analytics, consent, ads, and state-changing GET URLs do not misfire. It improves perceived navigation, not the metrics of the landing load.

## 8. Third parties

Inventory scripts by origin (DevTools Network, WebPageTest "domains" view, Lighthouse third-party summary). For each: owner, purpose, consent requirement, size, main-thread time. Load after consent and after interaction where allowed, use `defer`/`async`, facades for embeds, and remove duplicates (two analytics tags, unused pixels). Measure with consent granted and denied; compliance behavior is a requirement, not a casualty of optimization.

## 9. Acceptance

- Field p75 for LCP, INP and CLS with cohort, time window and sample size; lab traces before/after (network and main-thread) under the same throttling.
- Test cold and warm cache, mobile and desktop, slow network, first interaction, authenticated/private pages, failed asset loads, and the checkout path.
- Preserve accessibility (focus order, reduced motion, text alternatives), consent, checkout and navigation behavior. A passing Lighthouse score does not prove field performance or functional correctness.

Sources: [Core Web Vitals](https://web.dev/articles/vitals) | [Optimize LCP](https://web.dev/articles/optimize-lcp) | [INP](https://web.dev/articles/inp) | [CLS](https://web.dev/articles/cls) | [Image performance in 6.3](https://make.wordpress.org/core/2023/07/13/image-performance-enhancements-in-wordpress-6-3/) | [Script strategy in 6.3](https://make.wordpress.org/core/2023/07/14/registering-scripts-with-async-and-defer-attributes-in-wordpress-6-3/) | [6.9 frontend performance](https://make.wordpress.org/core/2025/11/18/wordpress-6-9-frontend-performance-field-guide/) | [Speculative loading in 6.8](https://make.wordpress.org/core/2025/03/06/speculative-loading-in-6-8/). | [core speculative-loading.php](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/speculative-loading.php) | [MDN scheduler.yield](https://developer.mozilla.org/en-US/docs/Web/API/Scheduler/yield)
