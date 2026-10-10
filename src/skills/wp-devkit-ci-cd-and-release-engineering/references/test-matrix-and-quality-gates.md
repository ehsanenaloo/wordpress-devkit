# Test matrix and quality gates for WordPress projects

Contents: derive the support matrix; gate catalog and what each proves; PHP and WordPress runtimes in CI; multisite and database variants; JavaScript and browser gates; dependency gates; baselines and flaky tests; speed; reference jobs; acceptance.

Researched 2026-10-08. Sources: [PHP compatibility and WordPress versions](https://make.wordpress.org/core/handbook/references/php-compatibility-and-wordpress-versions/) (page modified 2026-08-19), [wp-env](https://developer.wordpress.org/block-editor/reference-guides/packages/packages-env/), [WordPress core version check API](https://api.wordpress.org/core/version-check/1.7/) (reported 7.1.3 on the research date), [Plugin Check action](https://github.com/WordPress/plugin-check-action), [Composer CLI](https://getcomposer.org/doc/03-cli.md), the DevKit tested baseline (WordPress 7.1, PHP 8.3, WooCommerce 10.8; a baseline, not a project promise).

## Derive the matrix from the declared support policy

1. Read the plugin/theme headers: `Requires at least`, `Requires PHP`, `Tested up to`, and `composer.json` `require.php`. These are the project's promise. If they are missing or stale, that is a finding, not a free choice.
2. Test the declared minimum, the newest supported and the current WordPress release, plus trunk/beta as a non-blocking job. A PHP version the WordPress release does not support is not a meaningful cell.
3. WordPress/PHP support at the research date (handbook table re-read in the second pass; 6.2 is 5.6 through 8.2, 6.3 is 7.0 through 8.2): 7.1 and 7.0 support PHP 7.4 through 8.5; 6.9 supports 7.2 through 8.5; 6.8 and 6.7 support 7.2 through 8.4; 6.6 supports 7.2 through 8.3. (The "beta" label was retired in May 2026, so a "supported" cell means core supports it.) WooCommerce, Gutenberg and your own dependencies add narrower floors; read their requirements.
4. Keep the matrix small and meaningful: lowest/lowest, highest/highest, current/current-PHP, plus one multisite cell. A full cross product multiplies cost without finding more defects.

```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    continue-on-error: ${{ matrix.experimental }}   # only the trunk cell is non-blocking
    strategy:
      fail-fast: false
      matrix:
        include:
          - { php: '7.4', wp: '6.2',    multisite: 'no',  experimental: false }  # declared minimums
          - { php: '8.3', wp: 'latest', multisite: 'no',  experimental: false }
          - { php: '8.3', wp: 'latest', multisite: 'yes', experimental: false }
          - { php: '8.5', wp: 'latest', multisite: 'no',  experimental: false }
          - { php: '8.5', wp: 'trunk',  multisite: 'no',  experimental: true  }
```

Required gates never use `continue-on-error`; the aggregate job treats the experimental cell as informational only.

## Gate catalog: what each proves and does not prove

| Gate | Command (discover the project's own first) | Proves | Does not prove |
|---|---|---|---|
| PHP syntax | `composer lint` / `find . -name '*.php' -not -path './vendor/*' -print0 \| xargs -0 -n1 php -l` | Files parse on that PHP | Runtime behavior |
| Coding standards | `vendor/bin/phpcs` (WordPress-Core/Extra/Docs, `PHPCompatibilityWP` with `testVersion`) | Style, many escaping/nonce sniffs, PHP-version compatibility | Authorization correctness; sniff pass is not a security review |
| Static analysis | `vendor/bin/phpstan analyse` with `szepeviktor/phpstan-wordpress` or `php-stubs/*` | Type and symbol errors at the configured level | Behavior; a baseline hides existing errors |
| Unit tests | `vendor/bin/phpunit --testsuite unit` | Pure logic | WordPress integration |
| Integration tests | PHPUnit with the WordPress test library (a database) | Hooks, queries, REST, capabilities in a real WP | Browser behavior, host config |
| Multisite tests | Same with `WP_TESTS_MULTISITE` / `MULTISITE=1` | Per-site tables, network activation | Network admin UI |
| E2E / browser | Playwright (or `wp-env` with the project's Playwright config) | A journey in a browser | Cross-browser matrix unless configured |
| Accessibility | axe in the E2E run | Detectable WCAG issues | Conformance; needs manual review |
| Plugin Check | `wp plugin check <slug>` or the plugin-check action | Directory-readiness checks (headers, escaping, file types, i18n) | A WordPress.org review pass |
| i18n | `wp i18n make-pot` diff, text-domain sniffs | Extractable strings, domain consistency | Translation quality |
| JS | `npm ci && npm run lint && npm test && npm run build` | Lint, unit tests, build success | Browser runtime |
| Dependency audit | `composer audit --locked --no-dev` (exit 0 clean, 1 on findings); `npm audit --omit=dev` | Known advisories in locked prod deps | Unknown vulnerabilities; reachability |
| Package verification | See [packaging-and-artifact-verification.md](packaging-and-artifact-verification.md) | The shipped zip is correct | Behavior on the host |

Coverage thresholds measure executed lines, not assertion quality; use them as a ratchet, not as a proof.

## Running WordPress in CI

- Option A: service containers (MySQL/MariaDB) plus the WordPress test library installed by the project's `bin/install-wp-tests.sh` (the WP-CLI `scaffold plugin-tests` convention). Fast, no Docker-in-Docker.
- Option B: `@wordpress/env` (`wp-env start`, needs Docker; `core` accepts `null` for latest, `WordPress/WordPress#<tag>` or `#master`; `phpVersion`, `mariadbVersion`, `plugins`, `config`, `multisite`). Run commands with `wp-env run <container> ...` (documented containers: `mysql`, `wordpress`, `cli`, `composer`, `phpmyadmin`). The `tests` environment is deprecated in current docs: do not copy older `tests-cli` instructions without checking the installed version.
- Pin the database (MariaDB/MySQL version) in the matrix when the project depends on version-specific SQL.
- Never run tests against a shared or production database. Test suites reset data.

## Baselines, ignores and flaky tests

- A PHPStan or PHPCS baseline is debt with an owner. CI should fail if the baseline grows (compare entry count) and should not be regenerated to make a failure go away (engineering contract rule 8).
- A flaky test is quarantined by a named issue and an expiry, not by `continue-on-error`. Retrying hides nondeterminism: record the retry count and fail on tests that need retries more than a threshold.
- Test data in E2E: create and delete its own content; do not depend on the seed order or the wall clock without freezing time.

## Speed without weakening

- Cache dependency downloads (Composer cache dir, `~/.npm`) keyed by lockfile hash. Do not cache `vendor/` across PHP versions. Caches are an optimization; a cold run must pass.
- Split slow E2E from fast gates; run slow on pull requests that touch relevant paths, but keep the required aggregate check always reporting (see the gates reference).
- Parallelize by job, not by skipping.

## Acceptance for a pipeline change

- A deliberately broken fixture (syntax error, failing test, unescaped output, vulnerable dependency in a throwaway branch) turns the right job red.
- The required aggregate check is red when any gate is red, cancelled or unexpectedly skipped.
- The matrix cells match the declared support policy; the minimum cell really runs the minimum versions (print `php -v` and `wp core version` in the log).
- Running the workflow twice on the same commit gives the same result.

A green pipeline proves the configured gates ran on the matrix. It does not prove behavior on hosts with different PHP extensions, object caches, opcode settings or other plugins.

## Looks wrong but is fine

- An experimental trunk cell with `continue-on-error`, reported but not required.
- Skipping browser tests for docs-only changes when the aggregate check still reports.
- A PHPCS ruleset that excludes `vendor/` and generated build files.
- Different `testVersion` for PHPCompatibility than the matrix's highest PHP (it states the minimum supported).
