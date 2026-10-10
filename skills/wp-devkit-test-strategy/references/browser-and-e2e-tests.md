# Browser and end-to-end tests

Contents: [When to use the browser layer](#when-to-use-the-browser-layer) - [Environment](#environment) - [Playwright configuration](#playwright-configuration) - [Test data and isolation](#test-data-and-isolation) - [WordPress e2e utilities](#wordpress-e2e-utilities) - [Writing stable tests](#writing-stable-tests) - [Visual and accessibility checks](#visual-and-accessibility-checks) - [Failure artifacts](#failure-artifacts) - [Sources](#sources)

Use browser tests for complete journeys and behavior that only exists in a browser (editor interaction, JavaScript state, focus, responsive layout). Keep enumeration of edge cases at lower layers.

## When to use the browser layer

Good: checkout from cart to confirmation, login and password reset, block insertion and save in the editor, settings page save with success and error states, keyboard and focus flows, cookie-based REST authentication. Poor: permission matrices, input validation permutations, SQL behavior, anything a PHP integration test can reach.

## Environment

- Run against a disposable site seeded for the test: wp-env (`testsPort` default 8889 keeps the test site separate from development on 8888), a CI container, or Playground for light journeys. Never run write tests against staging with real customers or production.
- Pin versions of WordPress, plugins, theme, PHP and the browser build so a failing run is reproducible. Record them in the run output.
- Disable unrelated noise: welcome guide in the editor, update checks, email sending (capture mail with a catcher such as MailHog or Mailpit), external HTTP calls (mock at the server or stub third-party scripts).
- Payment gateways run in sandbox mode with published test credentials or are stubbed; do not put live keys in any test environment.

## Playwright configuration

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig( {
	testDir: './tests/e2e',
	fullyParallel: false, // Shared WordPress state: parallelize only when each worker has its own site.
	forbidOnly: !! process.env.CI, // Fail the run if test.only is committed.
	retries: process.env.CI ? 1 : 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: [ [ 'list' ], [ 'html', { open: 'never' } ] ],
	use: {
		baseURL: process.env.WP_BASE_URL || 'http://localhost:8889',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
	},
	expect: { timeout: 10_000 },
	projects: [ { name: 'chromium', use: { ...devices[ 'Desktop Chrome' ] } } ],
} );
```

Notes: `retries` convert a flaky test into a pass; pair retries with a flake report and, on Playwright versions that support it, `failOnFlakyTests` (a `TestConfig` option since Playwright 1.52, with CLI flag `--fail-on-flaky-tests`). `expect.timeout` defaults to 5 seconds for web-first assertions. `forbidOnly` exits with an error when `test.only` is present. `trace: 'on-first-retry'` collects a trace only for retried tests.

## Test data and isolation

- Create the data a test needs through the REST API or WP-CLI in a setup step (users, products, posts) and delete only what the test created.
- One user per role per test file; authenticate once in a setup project and reuse `storageState`.
- Parallel workers need separate sites or separate data namespaces (unique slugs, separate carts); sessions and nonces expire, so do not share a logged-in state past its lifetime.
- Clean up even when the test fails (`afterEach`/fixture teardown), and make the seed idempotent so a retry starts from a known state.
- Date-dependent logic: set the system clock in the environment or use Playwright's `page.clock` API where supported; do not depend on today's date.

## WordPress e2e utilities

`@wordpress/e2e-test-utils-playwright` extends Playwright's `test` with fixtures `admin`, `editor`, `pageUtils` and `requestUtils`, and exports `expect`. `admin.visitAdminPage( 'options-general.php' )` loads an admin screen; `editor` helpers drive the block editor, and in newer editor versions the editor canvas is an iframe, so select canvas elements through `editor.canvas`; `requestUtils` talks to the REST API for setup. Method names change between package versions: read the installed package's README and types before using a helper in a plan. `wp-scripts test-e2e` is documented as the Playwright-powered E2E runner, with `test-playwright` as an alias (wp-scripts docs).

## Writing stable tests

```ts
import { test, expect } from '@playwright/test';

test( 'guest can check out with the sandbox gateway', async ( { page } ) => {
	await page.goto( '/product/test-widget/' );
	await page.getByRole( 'button', { name: 'Add to cart' } ).click();
	await expect( page.getByRole( 'status' ) ).toContainText( 'added to your cart' );

	await page.goto( '/checkout/' );
	await page.getByLabel( 'Email address' ).fill( 'buyer@example.test' );
	// ...fill required fields with test data...
	await page.getByRole( 'button', { name: 'Place order' } ).click();

	await expect( page ).toHaveURL( /order-received/ );
	await expect( page.getByRole( 'heading', { name: /thank you/i } ) ).toBeVisible();
} );
```

Rules:

- Locate by role, label and visible text (`getByRole`, `getByLabel`); use `data-testid` only for elements without accessible handles. Role locators also give a basic accessibility check for free.
- Use web-first assertions (`expect( locator ).toBeVisible()`, `toHaveText`) that retry; use `expect.poll()` or `toPass()` for non-DOM conditions. Do not use `waitForTimeout`; wait for the network response (`page.waitForResponse`) or a state.
- Assert the outcome that matters (order exists, setting persisted after reload, file was created), not only that a message appeared. After a save, reload and re-read.
- Keep a test short and single-purpose; share setup through fixtures rather than long scripts that cascade failures.
- Wait for the editor to be ready (the editor data stores) before interacting; autosave and heartbeat can interleave actions, so disable or account for them.
- Handle third-party iframes (payment fields) with `frameLocator`; if sandbox cards are unavailable, stub the gateway and say so in the report.

## Visual and accessibility checks

- Screenshots (`toHaveScreenshot`) are brittle across OS, fonts and GPU. Run them in one pinned container, mask dynamic regions (dates, ads), and treat updating snapshots as a reviewed change, never an automatic step. Do not refresh a baseline to make a failing run pass; explain each intentional change.
- Accessibility: add `@axe-core/playwright` scans after opening dialogs and triggering errors, and keyboard assertions for focus return and Escape. Automated scans cover a subset; see `wp-devkit-accessibility-review` for manual checks.
- Responsive: run at least one narrow viewport project (320 to 390 px) for navigation and checkout.

## Failure artifacts

Keep traces, screenshots, videos on failure, browser console errors, WordPress `debug.log` and server responses as CI artifacts with a short retention, redacted of tokens, emails and cookies. Treat a console error or PHP notice during a journey as a failure unless allow-listed with a reason. Upload artifacts with an always-run step so failed jobs still produce them.

## Sources

Reviewed 2026-10-08.

- [Playwright test configuration](https://playwright.dev/docs/test-configuration): `forbidOnly`, `retries`, `workers`, `trace`, `expect.timeout`
- [Playwright accessibility testing](https://playwright.dev/docs/accessibility-testing)
- [@wordpress/e2e-test-utils-playwright](https://developer.wordpress.org/block-editor/reference-guides/packages/packages-e2e-test-utils-playwright/): fixtures `admin`, `editor`, `pageUtils`, `requestUtils`
- [@wordpress/env](https://developer.wordpress.org/block-editor/reference-guides/packages/packages-env/): ports and mappings
- `failOnFlakyTests` is a `TestConfig` option since Playwright 1.52 (release notes and API docs via search); `--fail-on-flaky-tests`, `--forbid-only`, `--pass-with-no-tests` and `--max-failures` are in the [Playwright CLI docs](https://playwright.dev/docs/test-cli). The e2e utils page documents only the fixtures and `editor.canvas`, not individual `requestUtils` methods.
