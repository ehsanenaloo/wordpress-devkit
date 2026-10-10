# Test strategy workbook

Contents: [Decision rules](#decision-rules) - [Test-gap heuristics](#test-gap-heuristics) - [Looks wrong but is fine](#looks-wrong-but-is-fine) - [Looks fine but is wrong](#looks-fine-but-is-wrong) - [Severity](#severity) - [Finding template](#finding-template) - [Symptom to cause](#symptom-to-cause) - [Acceptance checks](#acceptance-checks) - [Sources](#sources)

Apply [the engineering contract](engineering-contract.md) first. Detail files: [layers and setup](test-layers-and-setup.md), [recipes](wordpress-test-recipes.md), [WooCommerce and data](woocommerce-and-data-tests.md), [browser](browser-and-e2e-tests.md), [CI and evidence](ci-and-evidence.md).

## Decision rules

| Question | Rule |
| --- | --- |
| Which layer? | The layer where the behavior is decided. Hooks, capabilities, storage, REST, AJAX, cron: WordPress integration. Pure logic: unit. Journey, JavaScript, focus: browser. |
| What does the regression assert? | The observable outcome and persisted state, including that a denied action changed nothing. Not that a function was called. |
| What proves it is causal? | It fails on the unfixed code for the stated reason, passes on the fix, and the positive control still passes. |
| Mock or real? | Mock only what you do not own and the test does not claim to verify (third-party HTTP). Never mock the capability check, the data store or the hook that the test is about. |
| What is isolated? | Everything the test writes: users, options, posts, transients, cron events, files, caches, globals, static state. Cleanup runs on failure too. |
| What blocks CI? | Failures, errors, empty suites, required skips, `test.only`, flaky-tolerant retries beyond policy. |
| What is a flake? | A test whose result changes without a code change. It has a cause (shared data, order, clock, network, animation) and an owner. |

## Test-gap heuristics

For each behavior owner found by the search patterns, ask whether a test would fail if the guard were removed:

- Capability and ownership checks: is there a test as a low-privilege user and as another user's object, and does it assert no side effect?
- Escaping and sanitization on output: does a test render hostile input?
- Nonce-only protection: CSRF cover is not authorization; there should be a capability test as well.
- Input validation: boundaries (0, -1, max, max+1), type confusion, arrays where strings expected, unicode.
- Failure handling: external call returns error or times out; partial write; job interrupted.
- Idempotency: the same request, webhook or job twice.
- Upgrade/migration: previous version data shape, rerun, interruption.
- Uninstall: data removed or kept as documented.
- Multisite and HPOS: if supported, tested in that mode.
- Privacy: exporter/eraser behavior if personal data is stored.
- Accessibility and responsive: keyboard path for critical UI.

Report a gap as confirmed only after looking for the test by behavior, not by name: grep the test directory for the function, route, hook or option; open the nearest test. "No test file with this name" is a lead.

## Looks wrong but is fine

- A pure function tested with no WordPress: correct layer for pure logic.
- A mocked HTTP client for a third-party API, with separate sandbox smoke tests: correct.
- Tests that call the handler function directly instead of through HTTP when a separate HTTP-layer test covers auth transport.
- `markTestSkipped` for a feature missing on an older WordPress version in a matrix where the cell exists specifically to test that version.
- Retries enabled locally for developer comfort when CI runs with retries 0 or reports flakes as failures.
- Low line coverage in generated code, vendor code, or thin glue files.
- A snapshot update in a commit that also changes the intended output, with the diff reviewed.
- `sleep`-free polling with a bounded timeout.

## Looks fine but is wrong

- Response-only assertions: the endpoint returns 403 but the write already happened.
- A "permission test" that mocks `current_user_can()`.
- Tests that pass because the database retains data from an earlier test or a previous run.
- Shared fixtures mutated by tests (a "shop" user whose cart persists).
- A browser test that waits a fixed time, passing locally and failing in CI.
- `phpunit | tee` in a workflow so CI is green after failures.
- Coverage threshold met by tests that execute lines without assertions (`beStrictAboutTestsThatDoNotTestAnything` off, or assertion-free tests).
- An HPOS claim backed by one legacy-mode run.
- Test passes because an exception thrown for a different reason (missing function) satisfies `expectException`.
- Baseline or snapshot refreshed in the same commit as the code that broke it.

## Severity

CRITICAL: no test or a masked test covers a code path that can cause reachable compromise, irreversible data loss or financial error (permission, payment, migration, delete), or CI is demonstrably green while the suite fails.
WARNING: a supported behavior lacks a regression, tests are order-dependent or flaky, or required environments are skipped silently.
INFO: structure, speed, naming or coverage-quality improvements.
A missing test is a candidate until you show the behavior can actually fail in a reachable way; state the absent evidence rather than inflating severity.

## Finding template

```text
[WARNING] path/to/code.php:LINE (behavior)
Gap: what is untested or wrongly tested, and why current tests pass while it is broken
Evidence: searched <patterns/dirs>, found <tests>, observed <mocked boundary / missing negative case / shared state / exit swallowed>
Impact: what breaks undetected (release, data, security)
Confidence: confirmed | probable | candidate (needs execution)
Proposed regression: layer, fixture, steps, assertions on persisted state, controls
Proof plan: how to show it fails first (revert fix, mutate guard, canary)
```

## Symptom to cause

| Symptom | Evidence to gather | Usual cause and fix |
| --- | --- | --- |
| Passes locally, fails in CI | Versions, DB, locale, timezone, parallelism, file permissions | Hidden dependency on environment: pin versions, fix timezone and locale, isolate data |
| Passes alone, fails in suite | Run the test alone and with random order; inspect static/global state | Leaked state: reset globals, singletons, filters; clean up in tear_down |
| Fails only on the Nth run | Persistent data from the previous run, unique-key collisions | Test DB not reset or non-unique fixtures; use factories and a fresh DB |
| `Call to undefined function wc_*` in unit tests | Bootstrap load order | WooCommerce not loaded in `muplugins_loaded`; load dependencies before the plugin |
| Notice "incorrect usage" fails the test | Which function emitted it | Real bug in registration timing (for example `register_rest_route` outside `rest_api_init`); fix, or mark expected deliberately |
| `exit`/`die` kills the PHPUnit process | Handler calls `wp_die`/`exit` | Use `WP_Ajax_UnitTestCase`, or filter `wp_die_handler`, or refactor the handler to return |
| CI green with failing tests | Step shell and pipes, `continue-on-error`, `|| true`, exit-code wrappers | Propagate exit status; add canary |
| Playwright test flaky on checkout | Trace; race with ajax updates (checkout recalculation) | Wait for the response or a stable state, not a timer |
| Snapshot diffs on every machine | Fonts, OS, device pixel ratio | Pin container, mask dynamic regions |

## Acceptance checks

- Every claimed regression has a recorded failing run on the unfixed behavior (or a documented mutation) and a passing run after the fix, with command and exit status.
- Each regression includes a positive control and at least one negative/failure control relevant to the risk.
- Tests create and remove their own data; running the suite twice or in random order gives the same result.
- A deliberately failing canary makes CI red; skipped and flaky tests are listed with owners.
- The CI matrix covers the declared minimum and latest versions and the storage/multisite modes claimed.
- No baseline, snapshot or ignore was widened to obtain the result.

A pass proves the executed assertions for the recorded environment. It does not prove untested layers or versions, production configuration, concurrency at scale or third-party behavior.

## Sources

Reviewed 2026-10-08.

- [WordPress core automated testing handbook](https://make.wordpress.org/core/handbook/testing/automated-testing/)
- [Writing PHPUnit tests](https://make.wordpress.org/core/handbook/testing/automated-testing/writing-phpunit-tests/)
- [Playwright test configuration](https://playwright.dev/docs/test-configuration)
- [WordPress debugging](https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/)
