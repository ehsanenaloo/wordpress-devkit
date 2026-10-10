# Configuration, levels and symbol discovery

Research date: 2026-10-08. Check the latest releases of PHPStan, szepeviktor/phpstan-wordpress and the stub packages online (official source) and record the versions you used.

Contents: 1 Install and layout | 2 Config precedence and keys | 3 Levels | 4 Symbol discovery | 5 WordPress extension and stubs | 6 WooCommerce, WP-CLI and other stubs | 7 PHP version | 8 Cache and performance | 9 Strictness packages | 10 Review checks

## 1. Install and layout

```sh
composer require --dev phpstan/phpstan szepeviktor/phpstan-wordpress phpstan/extension-installer
```

Committed: `composer.json`, `composer.lock`, `phpstan.neon.dist` (and a baseline if used). Ignored by Git: `phpstan.neon` (local override) and `tmpDir`. Pin the PHPStan version through the lockfile; upgrades are deliberate commits that re-run the suite. szepeviktor/phpstan-wordpress 2.x requires PHPStan 2.0+ and PHP 7.4+; check its README online for the supported PHP range and the minimum `php-stubs/wordpress-stubs` version. With `phpstan/extension-installer` the extension loads automatically; without it include `vendor/szepeviktor/phpstan-wordpress/extension.neon` once. Do both and you load it twice.

## 2. Config precedence and keys

Which config runs: `-c/--configuration` file; else `phpstan.neon`, then `phpstan.neon.dist`, then `phpstan.dist.neon` in the current directory; else no config (then `--level` and paths are mandatory on the command line). Relative paths in a config resolve from that config file's directory. Paths given on the command line replace `parameters.paths`; they do not merge.

Keys that decide coverage:

| Key | Meaning | Review note |
|---|---|---|
| `level` | Rule level 0 to 10 (`max` alias) | Set a numeric value; the config requires a level unless the command passes `--level` |
| `paths` | Files/directories analyzed | Must cover every shipped first-party PHP file |
| `excludePaths` | fnmatch patterns; sub-key `analyse` excludes from analysis only; `analyseAndScan` excludes from analysis and discovery; a plain list means `analyseAndScan` | Each entry needs a reason; optional paths can be marked `(?)` in `excludePaths` |
| `scanFiles` / `scanDirectories` | Make symbols known without analyzing them | For vendored or generated code |
| `bootstrapFiles` | PHP files executed before analysis (constants, aliases, custom autoloader, stubs) | Executed by the PHP runtime: keep side-effect free; never point at the project's WordPress bootstrap |
| `tmpDir` | Result cache location (default `sys_get_temp_dir()/phpstan`) | Set per project (e.g. `.cache/phpstan`), not committed |
| `treatPhpDocTypesAsCertain` | Default true: PHPDoc types are as certain as native types | Set false for code that receives untrusted input typed only in docs |
| `phpVersion` | Target PHP as an integer such as `80300`, or a `min`/`max` range (2.0+); inferred from `composer.json` when unset | Align with supported PHP, not just CI PHP |
| `ignoreErrors`, `reportUnmatchedIgnoredErrors` | Suppression and its hygiene | See the baseline reference |
| `reportIgnoresWithoutComments` | Requires a parenthesized comment on every `@phpstan-ignore` (PHPStan 2.1.41+) | Good policy knob |

Config files use NEON: tabs/spaces are significant, lists need consistent indentation; validate with `phpstan analyse` or `phpstan diagnose` rather than by eye. PHPStan 2.0 removed several options (`checkMissingIterableValueType`, `checkGenericClassInNonGenericObjectType`, the `checkAlwaysTrue*` family; `excludes_analyse` became `excludePaths`); a config still carrying them was written for 1.x. To keep ignoring the old classes of errors use the identifiers `missingType.iterableValue` and `missingType.generics` in `ignoreErrors`, or better add the types.

## 3. Levels

Levels are cumulative: 0 basics (unknown classes/functions, wrong argument counts); 1 possibly undefined variables, magic members; 2 unknown methods on all expressions and PHPDoc validation; 3 return and property types; 4 dead code (always-false checks); 5 argument types; 6 missing type hints; 7 partially wrong union types; 8 nullable method calls and property access; 9 strict explicit `mixed`; 10 strict implicit `mixed` as well (new in 2.0); `max` aliases the highest level and moves on upgrades. Practical guidance: start at 5 on legacy WordPress code (arguments checked, noise manageable), move to 6 when signatures are typed, aim for 8 on new code; levels 9 and 10 suit typed domain code and are noisy at WordPress boundaries (options, meta, request data are `mixed`). Choose by useful signal and policy; record the reason. Prefer a numeric level so a PHPStan upgrade cannot change the bar unannounced.

## 4. Symbol discovery

PHPStan finds symbols in analyzed paths and Composer-autoloaded dependencies. Everything else must be made discoverable:
- Source code that defines symbols but should not be analyzed: `scanFiles` / `scanDirectories`.
- Constants, class aliases or a custom autoloader: `bootstrapFiles` or `--autoload-file`.
- WordPress core, plugins and themes are not in your Composer tree; supply stubs (next section) instead of pointing PHPStan at a live WordPress install, whose files include conditional definitions and executable side effects.

Do not load `wp-load.php` or the project's bootstrap from `bootstrapFiles`: it executes the site (database connection, hooks) at analysis time, mutates state and makes results environment-dependent. A small bootstrap that defines the constants your plugin expects (`define( 'ACME_VERSION', '0' )`) is fine. PHPStan 2.1.12+ can silence its discovery tip with `tips: discoveringSymbols: false`; leave it on.

## 5. WordPress extension and stubs

`szepeviktor/phpstan-wordpress` loads `php-stubs/wordpress-stubs` as a bootstrap file, defines core constants, and adds: dynamic return-type extensions (`apply_filters`, `wp_parse_args`, `shortcode_atts`, `esc_sql`, `wp_slash`, `wp_parse_url` and others), a `HookCallbackRule` and `HookDocsRule` that validate hook callbacks and `@param` docblocks of `apply_filters()`/`do_action()` calls (the first `@param` type is treated as definitive, so keep it accurate), and a `WpConstantFetchRule`. It marks `wp_send_json` and `wp_nonce_ays` as early-terminating calls. The stubs describe the latest WordPress API, not your minimum supported version: PHPStan will not warn when code uses a function introduced after your `Requires at least`. Guard version-gated calls with `function_exists()` / `version_compare( $wp_version, ... )` and cover them with CI against the minimum core.

Stub quirks: WordPress defines some functions conditionally so plugins can override them; the extension documents removing a conflicting stub function with `sed` for the rare duplicate-definition error. Document and automate such a patch (Composer script) instead of ignoring the error.

## 6. WooCommerce, WP-CLI and other stubs

```neon
parameters:
    bootstrapFiles:
        - vendor/php-stubs/woocommerce-stubs/woocommerce-stubs.php
        # - vendor/php-stubs/woocommerce-stubs/woocommerce-packages-stubs.php   # only if you use packaged WooCommerce classes
        - vendor/php-stubs/wp-cli-stubs/wp-cli-stubs.php   # commands, i18n and tools stubs are separate files in the package: wp-cli-commands-stubs.php, wp-cli-i18n-stubs.php, wp-cli-tools-stubs.php
```

Add only what the code uses (`php-stubs/woocommerce-stubs`, `php-stubs/wp-cli-stubs`; community stub packages exist for ACF and others, verify maintenance). WooCommerce stubs track the latest WooCommerce, so the same version-gating caveat applies. Check each stub package's own README for the supported file names.

## 7. PHP version

Analysis follows the PHP version PHPStan infers or `phpVersion` sets, independent of the runner's PHP. For a library supporting 7.4 to 8.4, set a `min`/`max` range (PHPStan 2.0+) or run CI jobs per version. Language features beyond the min version are reported. PHPStan itself needs PHP 7.4+ to run.

## 8. Cache and performance

The result cache lives in `tmpDir`; on CI restore it between runs keyed by lockfile and config hash to speed up the job, and clear it (`phpstan clear-result-cache`) when behavior looks stale. Parallel processing is on by default; `--debug` disables parallelism and cache and stops on the first internal error, which makes it the tool for crashes. Memory: `--memory-limit=1G` (or higher) on large codebases; set it in the CI command, and in scripts not in `php.ini`. PHPStan 2.2.13 changed the result-cache serialization, so caches from older versions are invalid after an upgrade.

## 9. Strictness packages

Optional rule packages: `phpstan/phpstan-strict-rules` (opinionated), `phpstan/phpstan-deprecation-rules` (calls to deprecated APIs; valuable when preparing for a new WordPress or PHP), `phpstan/phpstan-phpunit`. Opt-in `bleedingEdge.neon` includes carry no compatibility guarantee between releases (per the PHPStan release notes): use it knowingly, pinned. Each package is a separate decision; add one at a time and baseline nothing new without review.

## 10. Review checks

1. Resolved config file named; paths cover the inventory; no excludes of failing first-party files.
2. Extension loaded once; stubs for WooCommerce/WP-CLI present if used; no `wp-load.php` bootstrap.
3. Numeric level with a reason; `phpVersion` matches the support policy; legacy options removed after the 2.0 upgrade.
4. `tmpDir` configured and not committed; cache handling in CI.
5. Positive and negative controls were run or listed as unexecuted. A clean run does not prove correct runtime behavior, and stubs of the latest WordPress do not prove compatibility with the minimum supported version.

Sources: [Config reference](https://phpstan.org/config-reference) | [Rule levels](https://phpstan.org/user-guide/rule-levels) | [Discovering symbols](https://phpstan.org/user-guide/discovering-symbols) | [Command line usage](https://phpstan.org/user-guide/command-line-usage) | [phpstan-wordpress README](https://github.com/szepeviktor/phpstan-wordpress) and its [extension.neon](https://github.com/szepeviktor/phpstan-wordpress/blob/2.x/extension.neon) | [WooCommerce stubs](https://github.com/php-stubs/woocommerce-stubs) | [PHPStan releases](https://github.com/phpstan/phpstan/releases) | [Packagist: wordpress-stubs](https://packagist.org/packages/php-stubs/wordpress-stubs). | [Packagist API (versions, PHP requirement)](https://packagist.org/packages/phpstan/phpstan) | [php-stubs/wp-cli-stubs](https://github.com/php-stubs/wp-cli-stubs) | [php-stubs/woocommerce-stubs](https://github.com/php-stubs/woocommerce-stubs) | [phpstan/extension-installer](https://github.com/phpstan/extension-installer)
