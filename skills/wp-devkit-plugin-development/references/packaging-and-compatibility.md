# Packaging, directory readiness and compatibility

Contents: channels; directory rules that affect code; Plugin Check; readme and versions; dependencies, prefixing and bundling; PHP and WordPress version gates; release ZIP verification; assets and i18n; failure symptoms; sources.

## Channels

Decide the channel before applying rules. WordPress.org directory, private ZIP/update server, Composer package (`type: wordpress-plugin`) and must-use deployment have different requirements. Do not force directory rules on a private plugin, and do not ship a private update mechanism inside a directory plugin.

## Directory rules that change code (verified summary of the 18 guidelines)

- GPL-compatible licensing for all bundled code and assets; verify each library.
- Human-readable code. Minified or built assets need source access and documented build steps (readme or repository link).
- No trialware, no locked features; external services are allowed only when they provide real functionality and are disclosed in the readme with terms/privacy links.
- No contact with external servers without explicit opt-in consent; document collected data.
- No remote executable code, no updates from other servers, no third-party CDN assets other than fonts (keep JS/CSS local), no iframes to external admin pages.
- Use libraries bundled with WordPress (jQuery, PHPMailer, SimplePie...) rather than shipping copies.
- Admin notices: limited, dismissible, no dashboard ads; credit links optional and off by default.
- Increment the version on every release; trunk readme must match the stable tag. Submit a complete working plugin.
- Prefixing is a code-quality convention enforced in review (the guidelines page does not state it as a numbered rule): prefix functions, classes, constants, options, hooks, handles and global variables, or use a unique namespace.

## Plugin Check

The Plugin Check plugin (WordPress 6.3+, PHP 7.4+) runs most directory-submission checks and also flags i18n, accessibility, performance and security concerns.

```sh
wp plugin check my-plugin            # static checks (default)
wp plugin check /path/to/plugin      # a path
```

Runtime checks need the plugin's `cli.php` loaded via `--require` before WordPress loads (see its readme). Passing the "Plugin repo" category is typically required for approval but does not guarantee it and does not replace manual review. A result is a lead list: triage each item (for example a "direct database query" warning on a prepared custom-table query is expected and is annotated with a narrow `phpcs:ignore` plus reason, not blanket-disabled).

## Readme and version consistency

- `Stable tag`, plugin header `Version`, and any `ACME_VERSION` constant must agree at release. Verify with one script in CI.
- `Requires at least`, `Tested up to`, `Requires PHP` must reflect what CI actually tested, not aspirations. Update `Tested up to` only after running the suite on that core release.
- Document external services, data collected, and the uninstall data policy.
- Keep the changelog entry for the release.

## Dependencies, prefixing and bundling

- Composer with `--no-dev --optimize-autoloader` for the shipped `vendor/`. Dev tooling (PHPUnit, PHPCS, PHPStan) never ships.
- Two plugins bundling different versions of the same library collide on class names. Isolate runtime dependencies with a namespace-prefixing tool (php-scoper or Strauss are the established options; evaluate with your CI) or avoid the dependency. Verify after prefixing that autoload maps, string class references and reflection still resolve.
- Guard classes loaded from the plugin only when optional (`class_exists`) and never to hide a broken required dependency: a missing required dependency should produce a clear admin notice and graceful deactivation of the feature, not a fatal.
- Autoloading: PSR-4 via Composer, or a small `spl_autoload_register` for dependency-free plugins. File names must match the autoloader's expectations on case-sensitive filesystems (Linux). A plugin that works on Windows/macOS and fatals on Linux is a case mismatch.
- A direct-access guard (`defined( 'ABSPATH' ) || exit;`) belongs at the top of files that execute code on load. It is not a security boundary and is not needed in files that only declare symbols.

## PHP and WordPress version gates

- Do not use syntax or functions newer than the declared `Requires PHP`. Lint with `php -l` across the support range and run `PHPCompatibilityWP` through PHPCS (`--runtime-set testVersion 7.4-`).
- WordPress 7.0 raised the core minimum to PHP 7.4. A plugin may require more, but declare it.
- PHP 8.x deprecations that commonly bite plugins: dynamic properties on classes (deprecated in 8.2; use declared properties or `#[AllowDynamicProperties]` knowingly), passing `null` to non-nullable internal function parameters (8.1), implicit nullable parameter types (deprecated in 8.4: write `?Type $x = null`). Treat these as findings only when the declared support range includes the version that emits them.
- Guard use of newer core APIs by version or capability (`function_exists`, `has_action`, `$wpdb->has_cap( 'identifier_placeholders' )`) or raise `Requires at least`.
- Script loading: the `wp_enqueue_script` `$args` array (strategy `defer`/`async`, `in_footer`) needs 6.3; `fetchpriority` 6.9; `module_dependencies` 7.0. A bare boolean fourth `in_footer` still works.

## Release ZIP verification

Verify the artifact users get, not the repository:
1. Build with the release script; list the archive (`unzip -l`) and confirm presence of runtime `vendor/`, built assets, translations and absence of `tests/`, `node_modules/`, `.git*`, `composer.json` secrets, `.env`, source maps if undesired.
2. Install the ZIP on a clean disposable site; activate; run the primary journey; deactivate; delete (uninstall policy).
3. Run `wp plugin check` against the extracted directory.
4. Confirm the top-level folder name equals the slug and the main file path matches `Plugin Name` header file.
5. `wp dist-archive` (WP-CLI package) honors `.distignore`; whatever tool is used, the ignore list is part of the review.

## Assets and i18n

- Register assets with explicit dependencies and a version (file hash or plugin version) and enqueue them on the narrowest hook/screen. Generated `*.asset.php` (from `@wordpress/scripts`) supplies dependencies and version for built scripts.
- Use `wp_set_script_translations()` for JS strings; `wp i18n make-pot` to extract; text domain equals slug; complete sentences with placeholders and translator comments (`/* translators: %s: name */`); plurals through `_n()`.
- Test long German-like strings and RTL for layouts that embed text.

## Failure symptoms

| Symptom | Likely cause | Confirm |
|---|---|---|
| Fatal on Linux only | Class/file name case mismatch | `unzip -l`, `find`, error log |
| "Cannot redeclare" with another plugin | Unprefixed function/class or duplicated library | Stack trace; check prefixing/scoping |
| Feature missing in ZIP install | Build output or `vendor/` excluded by ignore file | Compare archive list to runtime requirements |
| Works on 8.1, warns on 8.3/8.4 | Newer deprecations | Run suite on the matrix |
| Directory rejection for "external code" | CDN scripts/styles or remote updater | Plugin Check, grep for URLs in enqueue calls |

## Sources (checked 2026-10-08)

- Detailed plugin guidelines: https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/
- Plugin Check (requires WordPress 6.3+, PHP 7.4+): https://wordpress.org/plugins/plugin-check/
- `wp dist-archive`: https://developer.wordpress.org/cli/commands/dist-archive/
- PHP 8.2 deprecations: https://www.php.net/manual/en/migration82.deprecated.php
- Header requirements: https://developer.wordpress.org/plugins/plugin-basics/header-requirements/
- `wp_enqueue_script` args: https://developer.wordpress.org/reference/functions/wp_enqueue_script/
- WordPress 7.0 field guide (PHP 7.4 minimum, script modules): https://make.wordpress.org/core/2026/05/14/wordpress-7-0-field-guide/

PHP deprecation versions (8.1 null to built-in non-nullable parameters, 8.2 dynamic properties, 8.4 implicit nullable parameters) were checked against the php.net migration guides; `wp dist-archive` (honors `.distignore`, options `--create-target-dir`, `--force`, `--plugin-dirname`, `--format`) against the WP-CLI command page. Not verified: php-scoper and Strauss behavior with the current release (check each tool's README; Strauss copies prefixed dependencies to `vendor-prefixed` by default).
