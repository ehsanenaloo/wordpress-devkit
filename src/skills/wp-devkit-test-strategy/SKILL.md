---
name: wp-devkit-test-strategy
description: Plan, write, debug or review WordPress tests: choose the layer (unit, WP integration, REST/AJAX, WooCommerce HPOS, Playwright), prove a regression fails first, fix flaky or order-dependent suites, CI exit propagation and skipped tests. Use for PHPUnit, wp-env and browser test strategy.
---

# Regressions that prove WordPress behavior

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Boundary with sibling skills

This skill decides what to test, at which layer, how to isolate it and whether the run proves anything. Domain correctness belongs to the owner skill (`wp-devkit-security-review`, `wp-devkit-woocommerce-dev`, `wp-devkit-rest-api-development`, `wp-devkit-block-development`, `wp-devkit-accessibility-review`). Static typing is `wp-devkit-phpstan-review`; pipeline design is `wp-devkit-ci-cd-and-release-engineering`. Use this skill when the question is "does a test exist that would have caught this?".

## Inputs and scope

The behavior or invariant, the failing trigger or bug report, declared WordPress/PHP/WooCommerce/Node support range, configured commands (`composer.json`, `package.json`, `phpunit.xml*`, `playwright.config.*`, CI files), existing fixtures, and whether a disposable runtime (wp-env, Docker, Playground) is available and authorized. Never point a test run at production data or the live database.

## Code Review Workflow

1. State the observable behavior and the failure the regression must distinguish. Find the real runner and how failure reaches the CI exit status.
2. Pick the cheapest layer that still contains the failing boundary (`references/test-layers-and-setup.md`): pure unit, WP integration (hooks, capabilities, storage, REST, AJAX, cron, HTTP), browser journey, or manual check. A mock that replaces the failing boundary proves nothing about it.
3. Define controls: a positive case, the denied/invalid/empty/failed-dependency case, and repeat, concurrency or migration cases when promised. Assert persisted state and side effects, not only the response.
4. Check isolation: test-owned data, reset of globals, current user, options, transients, cron, object cache, files, multisite state; no dependence on order or the clock.
5. Check reliability: no arbitrary sleeps, no silent retries or skips, `.only` blocked in CI, exit codes propagated, skipped tests listed, required checks cannot be disabled by a flag.
6. Report: suitable layer, the regression that fails before the fix, controls, runner and versions, what is not covered.

Read `references/test-strategy-workbook.md` first for decision rules, false positives and the finding format.

## References (read only what the task touches)

- `references/test-layers-and-setup.md` - read for layer choice, PHPUnit and WordPress test-suite setup, wp-env, version matrix, base classes and isolation rules.
- `references/wordpress-test-recipes.md` - read for REST, AJAX, capability, HTTP, cron, mail, multisite and block-serialization test patterns with code.
- `references/woocommerce-and-data-tests.md` - read for HPOS storage matrix, orders, webhooks, Action Scheduler, migrations, large data and cache behavior.
- `references/browser-and-e2e-tests.md` - read for Playwright and wp-env journeys, WordPress e2e utilities, determinism, traces, visual and accessibility checks.
- `references/ci-and-evidence.md` - read for exit propagation, fail-on flags, flake policy, matrices, artifacts, coverage meaning and baseline/snapshot policy.

## Implementation workflow

State the invariant and the layer, write the regression first, run it against the unfixed behavior when possible and record that it fails for the right reason, then fix and rerun. Keep tests next to the project's existing conventions and runner. Do not weaken or delete an existing test, regenerate snapshots or baselines, or widen ignores to turn a run green; if an expectation legitimately changes, explain it. Report commands with exit codes and list checks you could not run. Deployment and live-data work are out of scope.

## Search Patterns for Quick Detection

Leads only; they read files and run nothing. Exit 0 match, 1 no match, 2 error. Shared exclusions: `-g '!**/{vendor,node_modules,build,dist,coverage,backups}/**'`.

```sh
# What tests exist and how they are run
rg -n -g '*.{php,js,jsx,ts,tsx,json,xml,dist,yml,yaml}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'extends\s+(WP_UnitTestCase|WP_Ajax_UnitTestCase|WP_Test_REST_TestCase|TestCase)|describe\(|\btest\(|#\[Test\]|@test' -e 'phpunit|WP_TESTS_DIR|wp-env|playwright' .
# Mocks that may replace the boundary under test
rg -n -g '*.{php,js,ts}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'createMock|getMockBuilder|Mockery|Brain\\Monkey|WP_Mock|jest\.mock|vi\.mock|pre_http_request' .
# Disabled, skipped, retried or order-dependent tests
rg -n -g '*.{php,js,ts,xml,dist,json,yml,yaml}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'markTestSkipped|markTestIncomplete|@group\s+skip|\.skip\(|\.only\(|test\.fixme|retries|continue-on-error|@depends|waitForTimeout|sleep\(' .
# Exit-status leaks in scripts and workflows
rg -n -g '*.{yml,yaml,sh,json}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '\|\s*tee|\|\|\s*true|set \+e|--passWithNoTests|--pass-with-no-tests|failOnWarning="false"|exit 0' .
# Behavior owners that need denied/malformed/failed-dependency cases
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'register_rest_route|wp_ajax_|admin_post_|wp_schedule_|as_schedule_|dbDelta|register_activation_hook|wc_get_order|process_payment' .
```

## Output Format

Lead with the verdict and scope: behaviors reviewed, layers present, runner and versions found. For each confirmed gap give: behavior and file:line, why current tests would pass while it is broken (mock boundary, missing negative case, shared state, swallowed exit), impact, confidence, the proposed regression (layer, fixture, steps, assertions on persisted state), and how to prove it fails first. Separate confirmed gaps, candidates needing execution, and insufficient evidence. For implementation add files changed, commands with exit codes, before/after results, skipped or unavailable checks, and residual risk.
