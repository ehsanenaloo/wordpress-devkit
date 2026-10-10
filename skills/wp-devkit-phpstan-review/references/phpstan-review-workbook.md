# PHPStan review workbook

Apply [the engineering contract](engineering-contract.md) first.

Contents: 1 What a meaningful gate is | 2 Severity | 3 Finding template | 4 Symptom to cause | 5 Looks wrong but is fine | 6 Looks fine but is wrong | 7 Coverage fixture | 8 Acceptance checks | 9 Sources

## 1. What a meaningful gate is

A gate is meaningful when all hold: (a) every first-party PHP file that ships is under `paths` and not excluded; (b) the analysis can resolve the symbols it needs (WordPress, WooCommerce, WP-CLI, vendor) so it reports real errors instead of "unknown function" noise; (c) the level and rules are chosen on purpose and pinned; (d) suppressions are narrow, commented and counted; (e) CI runs the same command, with a pinned PHP and lockfile, and fails the build on a nonzero exit; (f) a deliberate type error in first-party code would turn the gate red. Review these six in order; a failure of an earlier one voids the evidential value of the later ones.

## 2. Severity

PHPStan findings use the contract's severities by demonstrated impact on the gate or code:

| Situation | Severity |
|---|---|
| Gate cannot fail (all first-party paths excluded, `continue-on-error`, `|| true`, errors discarded, baseline regenerated on each run, wrong working directory with no files analyzed) | CRITICAL when it is the project's release or quality gate, since defects ship unseen |
| A failing first-party module excluded from analysis; blanket `ignoreErrors` patterns hiding a class of defect; baseline entries covering newly written code; extension/stubs not loaded so WordPress calls are untyped | WARNING |
| Level lower than the team's policy without reason; missing PHPDoc improving inference; unmatched ignore entries; cosmetic config | INFO |
| A real type error that implies a runtime defect (nullable dereference, `WP_Error` used as an array, wrong argument type) | By the runtime impact, not by the PHPStan level |

## 3. Finding template

```text
[SEVERITY][confidence: confirmed|probable|candidate] Short title
Location : phpstan.neon:LINE | .github/workflows/x.yml:LINE | path/file.php:LINE
Config   : resolved config file, level, paths, excludePaths, baseline, extension/stubs versions
Gap      : what is not analyzed, suppressed or untyped
Impact   : class of defect that can now reach production
Evidence : commands run with versions and exit status; commands not run
Fix      : minimal change (restore path, load stubs, correct PHPDoc, remove ignore)
Regression: positive control passes, deliberate error fails with nonzero exit
```

## 4. Symptom to cause

| Symptom | Evidence | Likely cause and action |
|---|---|---|
| "Function add_action not found", hundreds of undefined WordPress symbols | `phpstan diagnose`, loaded extensions | Extension/stubs not loaded; install `szepeviktor/phpstan-wordpress` (requires PHPStan 2.x) with extension-installer or an explicit `includes:` entry, not both |
| "Class WC_Order not found" | Woo stubs present? | Add `php-stubs/woocommerce-stubs` via `bootstrapFiles`; mind the optional packages stub file |
| No errors, suspiciously fast | `-v` output, file count, `paths` | Paths empty or wrong relative to the config location; CLI path override |
| CI green, local red (or reverse) | Compare PHP, lockfile, config, working dir, memory | Config discovery differs; local uses `phpstan.neon` override that CI lacks; different PHP version |
| New code never reports errors | Baseline entries and counts; broad `ignoreErrors` regex | Baseline too broad; entries without path/count; regenerate only after review |
| `Access to undefined constant ABSPATH` / `WP_*` | Constants defined by extension vs project | Extension defines core constants via bootstrap; project constants defined in analyzed code are discovered; otherwise add a bootstrap or `scanFiles` |
| Errors about `mixed` everywhere at higher levels | Level 9/10 | Expected for options, meta, request data; add types at the boundary (see patterns) |
| Result cache stale or odd results after upgrade | `tmpDir`, version changes | `phpstan clear-result-cache`; do not commit `tmpDir` |
| "Ignored error pattern was not matched" | `reportUnmatchedIgnoredErrors` | The error was fixed or moved; remove the entry (do not disable the check) |

## 5. Looks wrong but is fine

- A baseline file that exists, is reviewed, has per-file counts, carries a note on scope, and is used while the team pays down legacy errors, with new errors still failing CI.
- `scanDirectories` or `scanFiles` for vendored or generated code that must be known but not analyzed.
- Level 5 or 6 on a mature plugin with a documented plan to raise it.
- `@var` or an assert that narrows a `mixed` value after validation (`is_string()` checks, `absint()`), not before.
- `bootstrapFiles` that defines environment constants and has no side effects beyond `define()`.
- `phpstan.neon.dist` committed with a developer-local `phpstan.neon` ignored by Git, provided CI uses the dist file explicitly (`-c phpstan.neon.dist`) so local overrides cannot change the gate.
- Excluding `tests/`, `vendor/` or `node_modules/` (confirm tests are analyzed with a separate config if the project wants that).
- `ignoreErrors` with `identifier` and `path` plus a comment for a known stub gap.

## 6. Looks fine but is wrong

- `excludePaths` (or the legacy `excludes_analyse`) listing a first-party endpoint, admin screen, uninstall or WooCommerce integration file because it "has too many errors".
- `analyse` command running from a different working directory so relative `paths` resolve to nothing, with `--no-progress` hiding the "no files" outcome.
- CI step with `continue-on-error: true`, `|| true`, `set +e`, or a wrapper script that swallows the exit code.
- `--generate-baseline` in the CI job, a pre-commit hook or a "fix lint" automation.
- `ignoreErrors` regex like `#Call to an undefined#` with no path, or a message pattern that matches unrelated future errors.
- `treatPhpDocTypesAsCertain` left true while PHPDoc is inaccurate, producing "always true" assumptions that mask bugs, or false everywhere to avoid fixing docs.
- Extension required in `composer.json` but not loaded: extension-installer absent, its plugin not allowed by Composer, or the package listed under `extra.phpstan/extension-installer.ignore` in `composer.json`.
- Stubs loaded twice (extension-installer plus a manual include), producing duplicate-definition errors that then get ignored.
- `level: max` with no pin: upgrading PHPStan silently adds a level and breaks CI, or the team lowers to `5` to recover.
- Casting (`(int)`, `(string)`) or `@var` to make an error disappear when the value can be `WP_Error` or `false`.

## 7. Coverage fixture

[analysis-coverage-fixture.neon.dist](analysis-coverage-fixture.neon.dist) is a minimal config to run against a disposable copy to show that the chosen paths are really analyzed. Adapt `paths`; keep `reportUnmatchedIgnoredErrors`. The expected experiment: a valid file using `add_action()` passes, a file with deliberate misuse such as `strlen( array() )` (or a function declared `: int` that returns a string) reports an error and exits nonzero, and an excluded copy of the same file does not, which is the signature of an excluded path. Delete the experiment; never leave deliberate errors in the repository.

## 8. Acceptance checks

| Check | Command or method | Passing proves | Does NOT prove |
|---|---|---|---|
| Effective config | `vendor/bin/phpstan diagnose` and `analyse -v` with the project's config | Version, loaded extensions, config, PHP | That code is correct |
| Coverage | Count files analyzed vs `rg --files -g '*.php'` of first-party | Analysis reaches the inventory | Absence of runtime bugs |
| Positive/negative control | Valid file passes, deliberate error fails (disposable copy) | Gate can fail | Rule completeness |
| Baseline audit | List entries by path/count; run with and without baseline | Baseline scope is bounded; new errors fail | That baselined errors are harmless |
| CI parity | Same command, same PHP, lockfile, exit code propagated | CI enforces the gate | Local developer experience |
| PHP matrix | Run against the lowest and highest supported PHP via `phpVersion` or CI jobs | Syntax/API compatibility at those versions | Runtime extension availability |

Record commands, versions, exit codes; list unexecuted checks. A zero exit means the analyzed files satisfy the configured rules at that level; it is not a security, correctness or performance verdict.

## 9. Sources

Research date: 2026-10-08. Sources: [PHPStan config reference](https://phpstan.org/config-reference) | [Rule levels](https://phpstan.org/user-guide/rule-levels) | [Ignoring errors](https://phpstan.org/user-guide/ignoring-errors) | [Baseline](https://phpstan.org/user-guide/baseline) | [Discovering symbols](https://phpstan.org/user-guide/discovering-symbols) | [Command line usage](https://phpstan.org/user-guide/command-line-usage) | [szepeviktor/phpstan-wordpress](https://github.com/szepeviktor/phpstan-wordpress) | [PHPStan 2.0 upgrading notes](https://github.com/phpstan/phpstan/blob/2.1.x/UPGRADING.md).
