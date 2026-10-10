# Baselines, ignores and CI gates

Researched 2026-10-08 against PHPStan 2.3.x. Contents: 1 Choosing a suppression | 2 Inline ignores | 3 Config ignores | 4 Baseline | 5 Adoption plan | 6 CI wiring | 7 Upgrading PHPStan | 8 Review checks

## 1. Choosing a suppression

Order of preference: fix the code; fix the PHPDoc or stub; narrow the type in code; an inline ignore with an identifier and reason; a config ignore for a path and identifier; a baseline for a bounded legacy set. Anything that silences a class of errors globally is the last resort. Never disable a check, loosen `reportUnmatchedIgnoredErrors`, or regenerate a baseline solely to make CI green (contract item 8); if an exception is unavoidable, scope it narrowly and write why.

## 2. Inline ignores

`@phpstan-ignore <identifier>[, <identifier>] (reason)` in any PHP comment. On its own line it applies to the next line; trailing a line it applies to that line. Identifiers appear in the table output and in `--error-format=json`/`prettyJson`. Example:

```php
// @phpstan-ignore argument.type (third-party filter passes int here; remove when upstream fixes the docblock)
acme_process( $value );
```

`@phpstan-ignore-line` and `@phpstan-ignore-next-line` silence every error on the line, accept no identifier and no comment: avoid them. `reportIgnoresWithoutComments: true` (PHPStan 2.1.41+) requires the parenthesized comment and bans those two forms. Unmatched inline ignores are reported when `reportUnmatchedIgnoredErrors` is on (the default), which keeps ignores from outliving the error. Searching for `@phpstan-ignore` should return a list a reviewer can read in minutes.

## 3. Config ignores

```neon
parameters:
    ignoreErrors:
        -
            identifier: missingType.iterableValue
            path: src/Legacy/*
        -
            message: '#^Method Acme\\Legacy\\Importer::run\(\) has no return type specified\.$#'
            path: src/Legacy/Importer.php
            count: 1
        -
            rawMessage: 'Call to an undefined method Foo::bar().'   # exact text, no regex (2.1.24+)
            identifier: method.notFound
            path: src/Compat/foo.php
```

Forms: a bare string (a regex applied project-wide: avoid); `message`/`messages` (regex) with `path`/`paths` (fnmatch, relative to the config) and `count`; `rawMessage` (exact text, PHPStan 2.1.24+, plural form 2.1.40+; cannot be combined with `message`); `identifier`/`identifiers` (alone or combined with `message`, both must match). Per-entry `reportUnmatched: false` overrides the global setting for one entry only. Paths in `ignoreErrors` must be valid paths or fnmatch patterns (an optional-path suffix `(?)` is not supported there). Prefer `identifier` plus `path` plus `count`; they stay stable across message rewording and show intent.

Red flags: an entry without `path`; a regex such as `#Call to an undefined#`; `count` omitted for an entry that matches a handful of known errors; `reportUnmatchedIgnoredErrors: false` globally; entries for first-party new code.

## 4. Baseline

`vendor/bin/phpstan analyse -c phpstan.neon.dist --generate-baseline phpstan-baseline.neon` records current errors as `ignoreErrors` entries with an escaped message pattern, a `count` and a `path`; include the file via `includes:`. A name ending in `.php` produces a PHP-format baseline that parses faster for very large baselines. Behavior to rely on: the baseline suppresses only what it recorded; errors beyond a recorded count, in new files, or with new messages still fail; if a count goes down PHPStan reports the stale entry so it can be removed. Without `--allow-empty-baseline`, generation refuses to write an empty baseline (exit code 1 means no errors to baseline, 0 means a non-empty baseline was written). Limits: no line numbers, no comments, grows quietly, and a message-and-count match can hide a new error identical to an old one in the same file.

Governance: generate once, review the diff, commit alone, label it as debt with an owner and a target to shrink; CI never generates or refreshes it; a pull request that grows the baseline needs explicit approval; track entries per directory. Regenerating after a PHPStan or extension upgrade is legitimate only if the diff shows the same errors under new messages, never new real defects. Baselining a level raise is acceptable as an adoption tool when new code is held to the new level through a stricter config for changed or new paths.

## 5. Adoption plan

1. Establish coverage: all first-party paths in `paths`, stubs loaded, no excludes of failing files, level 0 to 3 green.
2. Raise the level step by step on the whole tree (not a subset), triaging each class of error: discovery first, then real defects, then PHPDoc.
3. At the target level, baseline the remaining reviewed legacy errors; set a ratchet (the baseline count may only fall).
4. Hold new code to the target or a higher level through a second config (`phpstan-new.neon` targeting new directories) if the legacy debt is large.
5. Add `phpstan-deprecation-rules` before WordPress or PHP upgrades.

## 6. CI wiring

Requirements: install from the lockfile (`composer install --no-interaction --prefer-dist`), pin the PHP version (matrix for min and max supported), run the same config as local (`-c phpstan.neon.dist` explicitly), propagate the exit code, no `continue-on-error`, no `|| true`, no baseline generation, runs on pull requests and on the default branch, and a required status check in branch protection.

```yaml
- name: PHPStan
  run: vendor/bin/phpstan analyse -c phpstan.neon.dist --no-progress --memory-limit=1G --error-format=github
```

`--error-format=github` annotates the diff in GitHub Actions (other built-in formats: `table`, `raw`, `checkstyle`, `json`, `prettyJson`, `junit`, `gitlab`, `teamcity`); `--no-progress` keeps logs clean; the table format also detects some CI environments automatically. Cache `tmpDir` between runs keyed on `composer.lock` and the config. Pin third-party actions to full commit SHAs and give the job read-only token permissions. Do not run PHPStan on untrusted pull requests with secrets available; analysis loads `bootstrapFiles` and Composer autoloaders, which execute code.

Prove the gate: in a disposable branch add a deliberate error to a first-party file and confirm the job fails; keep this as a documented procedure or a CI self-test fixture outside the shipped code. A zero exit must never be reported without the command and PHP/PHPStan versions.

## 7. Upgrading PHPStan

Treat as a change set: read the release notes and UPGRADING.md; major 2.0 removed options (`checkMissingIterableValueType`, `checkGenericClassInNonGenericObjectType`, `checkAlwaysTrue*`), renamed `excludes_analyse` to `excludePaths`, requires identifiers on custom rule errors, and reports always-true conditions by default. Extensions must be compatible (szepeviktor/phpstan-wordpress 2.x needs PHPStan 2). Minor releases can add checks and change inference (for example 2.2.15 added `Error` to the default unchecked exception classes); result-cache formats can change (2.2.13). Upgrade in its own pull request, review new errors as real findings, and avoid rebaselining them blindly.

## 8. Review checks

1. Inventory of suppressions: count by form, identifiers and paths present, comments present, none on new code.
2. Baseline: one file, bounded, committed, not regenerated in CI, new errors still reported (test by adding one).
3. CI: command parity, exit code propagation, required check, pinned versions.
4. Regression: deliberate error fails the gate; fixing a baselined error reduces its `count` and PHPStan asks to remove the stale entry.
5. A green gate with a large baseline proves little about legacy code; report the baseline size and the share of files covered by it.

Sources: [Ignoring errors](https://phpstan.org/user-guide/ignoring-errors) | [Baseline](https://phpstan.org/user-guide/baseline) | [Command line usage](https://phpstan.org/user-guide/command-line-usage) | [Output format](https://phpstan.org/user-guide/output-format) | [Config reference](https://phpstan.org/config-reference) | [PHPStan releases](https://github.com/phpstan/phpstan/releases) | [UPGRADING (2.x)](https://github.com/phpstan/phpstan/blob/2.1.x/UPGRADING.md) | [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions). | [Output format (no sarif listed)](https://phpstan.org/user-guide/output-format)
