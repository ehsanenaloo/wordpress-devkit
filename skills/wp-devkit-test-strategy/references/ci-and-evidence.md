# CI reliability and evidence

Contents: [Exit status propagation](#exit-status-propagation) - [Fail-on options](#fail-on-options) - [Skips, retries and flakes](#skips-retries-and-flakes) - [Workflow shape](#workflow-shape) - [Matrix design](#matrix-design) - [Coverage and mutation testing](#coverage-and-mutation-testing) - [Baselines and snapshots](#baselines-and-snapshots) - [Evidence record](#evidence-record) - [What a green run does not prove](#what-a-green-run-does-not-prove) - [Sources](#sources)

## Exit status propagation

A test that fails but leaves CI green is the worst defect in a test setup. Check each link:

- Pipes: in GitHub Actions the default Linux shell is `bash -e {0}` without `pipefail`; an explicit `shell: bash` adds `-eo pipefail`. A step like `phpunit | tee log.txt` therefore returns `tee`'s status under the default shell. Use `shell: bash`, or `set -o pipefail`, or avoid the pipe (use a reporter that writes a file).
- `|| true`, `; exit 0`, `set +e`, `continue-on-error: true`, `if: always()` on the test step itself, and `--passWithNoTests` / `--pass-with-no-tests` each mask failures or an empty suite. Grep for them (SKILL.md patterns) and require a written reason.
- Wrapper scripts and Composer scripts must return the child's exit code; Node scripts must not swallow rejected promises. Verify with a canary: add a deliberately failing test on a throwaway branch and confirm the job turns red, then remove it.
- An empty or mis-globbed test directory should fail (`failOnEmptyTestSuite`, Playwright's default of failing when no tests are found unless the pass flag is set). Assert the expected test count in the run summary for critical suites.
- Docker/wp-env: `wp-env run ... vendor/bin/phpunit` must propagate the exit code to the CI step; confirm.
- Timeouts: set `timeout-minutes` on jobs and a test timeout; a timed-out job is a failure, not a skip.

## Fail-on options

Defaults differ by tool and version. Read the installed version's documentation and set options explicitly.

- PHPUnit 10 and later: `failOnWarning`, `failOnRisky`, `failOnDeprecation`, `failOnNotice`, `failOnSkipped`, `failOnIncomplete`, `failOnEmptyTestSuite` are attributes of the `<phpunit>` element and default to false (checked in the 11.5 configuration documentation); `beStrictAboutTestsThatDoNotTestAnything` defaults to true; `requireCoverageMetadata` defaults to false. Core's WordPress test library currently runs PHPUnit 9, whose configuration schema differs (no `failOnDeprecation`; deprecations were converted with `convertDeprecationsToExceptions`). Match the config to the actual runner version.
- Playwright: `forbidOnly` (error on `test.only`), `retries`, and `failOnFlakyTests` / `--fail-on-flaky-tests` where available; `--max-failures` for early stop.
- Skipped tests that guard a required environment (no WooCommerce, no Redis) must fail in CI where the environment is provisioned: fail the run if the skip count is nonzero for required suites.

## Skips, retries and flakes

- A skip, `markTestIncomplete`, `test.fixme`, `.skip`, `@group skip` or `retries` is a decision with an owner and an expiry, recorded in the report as unexecuted or flaky, not as pass.
- Flaky policy: a retried pass is reported as flaky, tracked with a ticket, root-caused (shared data, ordering, timeouts, animations, network, clocks) and fixed. Quarantine moves a test to a non-blocking job only with a deadline; quarantined tests still run and are reported.
- Arbitrary sleeps are never the fix. Await a condition (`expect.poll`, `waitForResponse`, polling a queue with a bound).
- Order dependence: run PHPUnit with random order locally (`--order-by=random`; listed in the PHPUnit 9.6 and later CLI docs; check your version) and record the seed on failure. WordPress core-library suites may depend on defaults; isolate your tests instead of relying on order.

## Workflow shape

```yaml
name: tests
on: [ pull_request ]
permissions:
  contents: read
jobs:
  phpunit:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    strategy:
      fail-fast: false
      matrix:
        php: [ '7.4', '8.2', '8.4' ]
        wp: [ 'latest', 'trunk' ]
        include:
          - php: '7.4'
            wp: '6.5'   # Declared minimum.
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
        ports: [ '3306:3306' ]
        options: >-
          --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: shivammathur/setup-php@v2
        with:
          php-version: ${{ matrix.php }}
          coverage: none
      - run: composer install --no-interaction --prefer-dist
      - name: Install WordPress test library
        shell: bash
        run: bin/install-wp-tests.sh wordpress_test root root 127.0.0.1 ${{ matrix.wp }} true
      - name: PHPUnit
        shell: bash
        run: vendor/bin/phpunit --fail-on-warning --fail-on-risky
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: phpunit-${{ matrix.php }}-${{ matrix.wp }}
          path: build/logs/
          retention-days: 7
```

The `--fail-on-risky`, `--fail-on-warning`, `--fail-on-incomplete` and `--fail-on-skipped` flags are listed in the PHPUnit 9.6 CLI docs; older versions may lack them, so confirm with `vendor/bin/phpunit --help`, or set the equivalent attributes in `phpunit.xml.dist`. Pin actions to a full commit SHA in security-sensitive repositories; floating tags are shown for brevity. Check the arguments of your generated `install-wp-tests.sh` (the last argument skips database creation when the service already provides it in some versions). Use `pull_request`, not `pull_request_target`, for untrusted code; do not expose secrets to fork builds. Run the browser job separately (wp-env or a prebuilt site) and the WooCommerce HPOS matrix as another dimension.

## Matrix design

Pick cells from declared support, not from every combination: minimum and latest WordPress (plus trunk for early warning), minimum and newest supported PHP (look up the PHP range the core compatibility table lists for each WordPress version, and confirm your declared range), single site and multisite, WooCommerce legacy/HPOS-sync/HPOS storage when orders are touched, with and without a persistent object cache for cache-sensitive code. Test the built release artifact (the zip users install) at least once, not only the source tree: missing built assets and wrong file lists are release defects.

## Coverage and mutation testing

Line coverage says code ran, not that its behavior was asserted. Use it to find untested files, not as a gate on its own. Require tests for changed risk areas (capability checks, escaping, migrations, money) rather than a percentage. Mutation testing (for example Infection) answers whether tests fail when logic changes; run it on pure-logic packages and changed files, not the entire WordPress-bound suite. Coverage drivers (PCOV, Xdebug) must be installed explicitly; a missing driver is an unexecuted check.

## Baselines and snapshots

PHPStan baselines, visual snapshots, expected-output fixtures and ignore lists are allowed to change only through a reviewed change that states why. Never regenerate a baseline or update snapshots to turn a failing run green, and never broaden an ignore pattern for that purpose. Show the diff of the baseline in the pull request.

## Evidence record

```text
Command(s): exact command lines (phpunit, playwright, wp-env)
Versions:   WordPress, PHP, WooCommerce, plugin/theme commit, PHPUnit, Node, Playwright, browser
Mode:       single/multisite, HPOS mode, object cache backend
Result:     exit status; counts for passed / failed / skipped / flaky / not run
Before/after: failing result on the unfixed code and passing result on the fix
Artifacts:  trace/log paths (redacted)
Not run:    list, with reason
```

## What a green run does not prove

A green run proves that the executed assertions held for the tested versions, data and mode. It does not prove untested layers, other PHP/WordPress/WooCommerce versions, concurrency or scale, third-party behavior, live configuration, or absence of defects. A green run with skipped required tests or with retried passes is a weaker result and must be described that way.

## Sources

Reviewed 2026-10-08.

- [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax): default shell `bash -e {0}`; `shell: bash` adds `-eo pipefail`
- [PHPUnit 11.5 configuration](https://docs.phpunit.de/en/11.5/configuration.html): fail-on attributes and defaults
- [PHPUnit versions used by WordPress core](https://make.wordpress.org/core/handbook/references/phpunit-compatibility-and-wordpress-versions/)
- [Playwright test configuration](https://playwright.dev/docs/test-configuration)
- [Composer audit](https://getcomposer.org/doc/03-cli.md#audit) for dependency advisory checks in the pipeline
