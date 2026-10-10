---
name: wp-devkit-phpstan-review
description: "Configure, debug or review PHPStan for WordPress plugins and themes: NEON config and levels, szepeviktor/phpstan-wordpress and WordPress/WooCommerce stubs, undefined symbols, WP_Error and hook typing, baselines, ignores and CI gate coverage that actually fails on type errors."
---

# Static analysis with meaningful coverage

Read `references/engineering-contract.md` first. A review request is read-only: resolve and explain the configuration and its coverage; do not edit config, regenerate a baseline, install packages or bootstrap the project. Run PHPStan only on an inspected target inside the authorized scope, otherwise record it as unexecuted. Implement only when the user authorizes changes.

Hand off: PHPCS/WordPress Coding Standards, PHPUnit and browser tests to `wp-devkit-test-strategy`; CI workflow design and release gates to `wp-devkit-ci-cd-and-release-engineering`; plugin architecture changes to `wp-devkit-plugin-development`; security conclusions to `wp-devkit-security-review` (types do not model permissions).

## Inputs

`composer.lock` (PHPStan, extension, stubs versions), PHP version(s) the code supports and the CI PHP, the exact local and CI commands, the effective config file, first-party source inventory, baseline and ignore policy, and whether WooCommerce, WP-CLI, ACF or other plugin APIs are used. Use `vendor/bin/phpstan diagnose` and `--version` output when execution is allowed.

## Code Review Workflow

1. Resolve the configuration the real command uses. Precedence: `-c/--configuration`, then `phpstan.neon`, `phpstan.neon.dist`, `phpstan.dist.neon` in the working directory. Command-line paths replace `paths`. Follow every `includes:`.
2. Compare analyzed paths and `excludePaths` with the first-party inventory (plugin root files, `src/`, `inc/`, templates, uninstall.php, mu-plugin loaders, CLI classes). Exclusions of failing production files are the first thing to look for.
3. Distinguish analysis from discovery: `paths` are analyzed; `scanFiles`/`scanDirectories` only make symbols known; `bootstrapFiles` are executed by PHP. Confirm the WordPress extension and stubs load once (extension-installer or one explicit include), and that WooCommerce/WP-CLI stubs are present if their symbols are used.
4. Check the level and strictness: numeric level (0 to 10) rather than `max`, a reason for the level, and `treatPhpDocTypesAsCertain`, `phpVersion` and `tmpDir` set deliberately. See `references/config-and-discovery.md`.
5. Triage diagnostics by class: undefined symbol (discovery), real type error, missing PHPDoc, WordPress dynamic types (`WP_Error|T`, hooks, `mixed` options). Correct the real contract; do not add a cast or ignore to silence a true defect. See `references/wordpress-type-patterns.md`.
6. Review suppressions and the baseline: identifiers, paths, counts, `reportUnmatchedIgnoredErrors`, comments, and whether new errors remain visible. See `references/baseline-ignores-and-ci.md`.
7. Verify the gate: CI runs the same command, fails the job on a nonzero exit, is not `continue-on-error`, does not regenerate the baseline, and a deliberate type error would fail it.

Read `references/phpstan-review-workbook.md` for severity, the finding template, false positives and acceptance checks.

## Implementation workflow

1. Run the current command first and keep the output as the baseline of evidence (version, level, error count, exit status).
2. Fix coverage before strictness: include all first-party paths, load stubs, remove blanket excludes; then triage errors by class.
3. Fix real defects and PHPDoc contracts at the source. Prefer precise types (`list<int>`, array shapes, `non-empty-string`, `positive-int`) over `mixed` and casts.
4. Create a baseline only for a reviewed, bounded set of pre-existing errors, once, in its own commit, after coverage is meaningful. Do not refresh it to make CI pass.
5. Prove the gate: a known-valid file passes, a deliberate type error in a first-party file produces a nonzero exit, and the baseline does not hide it.
6. Record versions, level, config, analyzed paths, baseline policy, command and exit code.

## Search Patterns for Quick Detection

Read-only leads from the first-party root; candidates, not findings. They do not run PHPStan. Exit codes: 0 match, 1 none, 2 error.

```sh
scan() { rg -n -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e "$1" "${2:-.}"; }
scan 'level:|paths:|excludePaths|excludes_analyse|includes:|bootstrapFiles:|scanFiles:|scanDirectories:|tmpDir:|treatPhpDocTypesAsCertain|phpVersion:'   # config and coverage
scan 'phpstan-wordpress|wordpress-stubs|woocommerce-stubs|wp-cli-stubs|extension-installer|extension\.neon|stubFiles:'   # extension and stubs
scan 'ignoreErrors:|reportUnmatchedIgnoredErrors|reportIgnoresWithoutComments|baseline|count:|identifier:|rawMessage'   # suppressions
scan '@phpstan-ignore|@phpstan-ignore-(next-)?line|@var\b|@psalm-suppress|\bmixed\b'   # inline escapes
scan 'phpstan\s+(analy[sz]e|clear-result-cache|diagnose)|vendor/bin/phpstan|--configuration|--level|--memory-limit|--generate-baseline|continue-on-error|\|\|\s*true'   # command and CI parity
scan 'apply_filters|do_action|is_wp_error|WP_Error|get_option\(|get_post_meta\(|\$wpdb->get_(row|results)'   # dynamic WordPress boundaries
```

Typical benign hits: a baseline with documented counts in a bounded legacy area, `scanDirectories` for a vendored dependency not meant to be analyzed, `@var` that narrows a `mixed` return from `get_option()` after validation, `|| true` in an unrelated shell step.

## Task-selected resources

- `references/config-and-discovery.md`: levels, config keys, precedence, symbol discovery, extension and stubs, PHP version, cache. Read for configuration and undefined-symbol problems.
- `references/wordpress-type-patterns.md`: how to type WordPress return unions, hooks, options, meta, requests, `$wpdb` and WooCommerce objects without hiding bugs. Read when triaging real diagnostics.
- `references/baseline-ignores-and-ci.md`: baselines, ignore forms, identifiers, CI wiring, adoption strategy, upgrades of PHPStan. Read for suppressions and gates.
- `references/analysis-coverage-fixture.neon.dist`: a minimal disposable config for proving that paths are analyzed; adapt paths, never copy blindly.

## Output Format

Lead with the verdict and reviewed scope. Record PHPStan, extension and stubs versions, PHP version, level, config, analyzed paths, excluded paths, baseline policy, command and exit status. Per finding: severity, `file:line` (config or code), what is uncovered or wrong, impact (what class of defect can now slip through), confidence, minimal fix, and a regression (positive and negative check). Separate resolved findings from excluded or unexecuted code. State whether each change corrects the type contract or the runtime behavior. A green run proves only that the analyzed code satisfies the rules at that level; it says nothing about code outside `paths`, runtime behavior or security.
