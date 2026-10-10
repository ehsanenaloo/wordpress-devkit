# Test layers and setup

Contents: [Layer choice](#layer-choice) - [Setup options](#setup-options) - [Plugin bootstrap](#plugin-bootstrap) - [PHPUnit versions](#phpunit-versions) - [Base classes and isolation](#base-classes-and-isolation) - [Writing a regression that proves the bug](#writing-a-regression-that-proves-the-bug) - [Multisite and environments](#multisite-and-environments) - [Sources](#sources)

## Layer choice

Choose the cheapest layer that still contains the failing boundary.

| Layer | Use for | Cannot prove |
| --- | --- | --- |
| Pure unit (no WordPress, or WP functions stubbed with Brain Monkey / WP_Mock / hand fakes) | Parsers, calculators, validators, formatters, state machines | Hook dispatch, capability mapping, SQL, escaping in real output, caching |
| WordPress integration (`WP_UnitTestCase`, real database) | Hooks and filters, capabilities and roles, post/term/user/option storage, REST dispatch, AJAX handlers, cron registration, settings, shortcodes, block render callbacks, uninstall | Browser behavior, JavaScript, CSS, HTTP auth transport, real payment gateway |
| HTTP/REST over the wire (curl or Playwright `request`) | Cookie and Application Password authentication, nonce header handling, redirects, headers, caching layers | Internal logic detail |
| Browser (Playwright) | Complete journeys, editor interaction, accessibility flows, JavaScript state, responsive layout | Fine-grained edge cases (too slow to enumerate) |
| Manual / exploratory | Visual quality, assistive technology judgment, third-party sandboxes | Repeatability; record as manual evidence |

Rule: one assertion at the layer where the behavior is decided, plus at most a thin smoke test above it. A mock returning `true` for `current_user_can()` cannot test authorization; a unit test of a pure function should not boot WordPress.

## Setup options

| Option | Fits | Notes |
| --- | --- | --- |
| `wp scaffold plugin-tests <plugin>` | A plugin repo without tests | Generates `phpunit.xml.dist`, `bin/install-wp-tests.sh`, `tests/bootstrap.php`, `tests/test-sample.php`, `.phpcs.xml.dist` and a CI config (`--ci=github|gitlab|bitbucket|circle`). `tests/bootstrap.php` reads the `WP_TESTS_DIR` environment variable. |
| `bin/install-wp-tests.sh <db> <user> <pass> <host> <wp-version>` | CI and local runs against a fresh database | Check the script before running: it prepares a test database and a WordPress copy; use a dedicated database and credentials, never the site database. |
| `@wordpress/env` (`wp-env`) | Docker-based, repo-local WordPress with plugins mapped | `.wp-env.json` fields `core`, `plugins`, `themes`, `mappings`, `config`, `port` (8888), `testsPort` (8889). `wp-env run cli --env-cwd=wp-content/plugins/my-plugin vendor/bin/phpunit`. Requires Docker by default. The docs list the `wp-env run` containers `mysql`, `wordpress`, `cli`, `composer` and `phpmyadmin` and do not mention a `tests-cli` container; confirm with `wp-env run --help` for your version. The experimental Playground runtime does not support `wp-env run`. |
| WordPress Playground / Blueprints | Quick disposable runtime for demos and some browser tests | Not a substitute for MySQL-backed integration tests; never execute untrusted Blueprint PHP. |
| Docker Compose in the project | Existing stacks | Pin image digests for reproducibility. |

Use a separate database. The WordPress test suite resets and reinstalls its database; pointing it at real data destroys data. `WP_TESTS_SKIP_INSTALL=1` (checked as `'1' !== getenv( 'WP_TESTS_SKIP_INSTALL' )` in the library bootstrap) speeds repeated small runs but should not be used for full or CI runs.

## Plugin bootstrap

```php
<?php
// tests/bootstrap.php
$tests_dir = getenv( 'WP_TESTS_DIR' );
if ( ! $tests_dir ) {
	$tests_dir = rtrim( sys_get_temp_dir(), '/\\' ) . '/wordpress-tests-lib';
}
if ( ! file_exists( $tests_dir . '/includes/functions.php' ) ) {
	fwrite( STDERR, "WordPress test library not found in {$tests_dir}\n" );
	exit( 1 );
}

// Polyfills path is required when the library is not installed through Composer.
if ( ! defined( 'WP_TESTS_PHPUNIT_POLYFILLS_PATH' ) && is_dir( dirname( __DIR__ ) . '/vendor/yoast/phpunit-polyfills' ) ) {
	define( 'WP_TESTS_PHPUNIT_POLYFILLS_PATH', dirname( __DIR__ ) . '/vendor/yoast/phpunit-polyfills' );
}

require_once $tests_dir . '/includes/functions.php';

tests_add_filter(
	'muplugins_loaded',
	static function () {
		require dirname( __DIR__ ) . '/my-plugin.php';
	}
);

require $tests_dir . '/includes/bootstrap.php';
```

Load dependencies (WooCommerce) the same way in `muplugins_loaded` before your plugin, in the order production loads them. Plugin activation hooks do not run when a file is only required; call the install routine explicitly in a test when lifecycle is under test.

## PHPUnit versions

WordPress core's test suite selects PHPUnit by PHP version through the PHPUnit Polyfills (WordPress 5.9+). At the time of review, WordPress 7.0 and 7.1 on PHP 7.4 to 8.5 use PHPUnit 9; 6.9 uses 9 on 7.3 to 8.5. Plugins that load the core test library are therefore constrained to the version that library supports, whatever the project would like. Pure-unit suites that do not load the library may use a newer PHPUnit (10 to 12) with their own `phpunit.xml`. Read the installed library bootstrap and the compatibility table before choosing a version.

## Base classes and isolation

- Extend `WP_UnitTestCase`. Use the snake_case fixtures: `set_up_before_class()`, `set_up()`, `tear_down()`, `tear_down_after_class()`; call `parent::set_up()` first and `parent::tear_down()` last.
- Each test runs in a database transaction that is rolled back; the harness also converts `CREATE`/`DROP TABLE` into temporary-table statements. Statements that cause an implicit commit (other DDL, `TRUNCATE`) and anything outside MySQL (files, transients in an external cache, uploads, scheduled events held elsewhere) are not rolled back; clean them in `tear_down()`.
- The harness resets common globals (`$_GET`, `$_POST`, `$_REQUEST`), flushes the cache, restores hooks and sets the current user to 0 after each test. It does not reset your own static properties, singletons, `$_SERVER` changes, constants, filters added with a different mechanism, or class-level caches: reset them yourself.
- Factories: `self::factory()->user->create( array( 'role' => 'editor' ) )` returns the id; `create_and_get()` returns the object; `create_many()` keeps values unique. `set_up_before_class()` is static and takes no arguments; for class-level fixtures define `public static function wpSetUpBeforeClass( $factory )` (and `wpTearDownAfterClass()`), which the harness calls when the method exists, and create data through the `$factory` argument.
- Use `@expectedDeprecated` / `@expectedIncorrectUsage` (or `setExpectedDeprecated()` / `setExpectedIncorrectUsage()`) when a notice is intended; otherwise the harness fails the test on `_deprecated_*` and `_doing_it_wrong` calls, which is the point.
- Assertions: `assertSame` over `assertEquals`; `assertWPError()` / `assertNotWPError()`; `assertEqualSets()` for order-free arrays; pass a message when a test has several assertions.
- Do not rely on test order or `@depends`. Every test builds what it needs.
- Time: WordPress has no clock abstraction. Inject time into your own code or filter `pre_option_*`, `current_time` and `wp_date`-based values; avoid `sleep()`.
- Random: seed or inject; do not assert on `wp_rand`/`shuffle` results.
- Run tests with errors visible: `error_reporting( E_ALL )`; treat PHP deprecations from your own code as failures on supported PHP versions (8.2 dynamic properties, 8.4 implicit nullable types).

## Writing a regression that proves the bug

1. Reproduce the bug at the chosen layer with the smallest fixture.
2. Assert the user-visible or persisted outcome, not an internal call.
3. Run it on the unfixed code and record that it fails for the stated reason (an `Error` from a missing function is not the same failure). If the fix already shipped, revert it temporarily in a scratch checkout, or write a mutation (change the guard) and confirm the test fails.
4. Add the control: the same operation succeeding for the allowed actor or valid input.
5. Fix; rerun; keep the test.

```php
<?php
class Test_Settings_Save extends WP_UnitTestCase {
	public function set_up() {
		parent::set_up();
		update_option( 'myplugin_api_url', 'https://example.test' );
	}

	public function test_subscriber_cannot_change_api_url() {
		wp_set_current_user( self::factory()->user->create( array( 'role' => 'subscriber' ) ) );
		$_POST = array( 'api_url' => 'https://evil.test', '_wpnonce' => wp_create_nonce( 'myplugin_save' ) );

		$result = myplugin_handle_save(); // Adapt: the handler under test.

		$this->assertWPError( $result );
		$this->assertSame( 'https://example.test', get_option( 'myplugin_api_url' ), 'Protected value changed despite error.' );
	}

	public function test_administrator_can_change_api_url() {
		wp_set_current_user( self::factory()->user->create( array( 'role' => 'administrator' ) ) );
		$_POST = array( 'api_url' => 'https://ok.test', '_wpnonce' => wp_create_nonce( 'myplugin_save' ) );

		$this->assertNotWPError( myplugin_handle_save() );
		$this->assertSame( 'https://ok.test', get_option( 'myplugin_api_url' ) );
	}
}
```

The nonce is only CSRF protection; the capability check is what the test must prove. Handlers that call `exit`/`wp_die` need the AJAX base class or a `wp_die_handler` filter (see recipes).

## Multisite and environments

- Run the multisite configuration separately (core uses `phpunit -c tests/phpunit/multisite.xml`; plugin setups maintain a second PHPUnit config that defines the `WP_TESTS_MULTISITE` constant, which the current library bootstrap checks; it also honors the `WP_MULTISITE=1` environment variable; confirm in the installed library's `includes/bootstrap.php`). Skip single-site-only tests with `skipWithMultisite()` and multisite-only with `skipWithoutMultisite()`, or by group, and keep the skip list visible in the report.
- Cover per-site vs network options (`get_option` vs `get_site_option`), `switch_to_blog()` restore in `finally`, `is_plugin_active_for_network`, and uninstall across sites.
- Test the declared PHP and WordPress minimum and latest, plus WooCommerce storage modes where relevant.
- Persistent object cache: run integration tests once with the default non-persistent cache and, for cache-sensitive code, once with a real Redis or Memcached drop-in available; transients then live in the cache and are not rolled back.

## Sources

Reviewed 2026-10-08.

- [WordPress core PHPUnit handbook](https://make.wordpress.org/core/handbook/testing/automated-testing/phpunit/)
- [Writing PHPUnit tests (core)](https://make.wordpress.org/core/handbook/testing/automated-testing/writing-phpunit-tests/)
- [PHPUnit compatibility and WordPress versions](https://make.wordpress.org/core/handbook/references/phpunit-compatibility-and-wordpress-versions/)
- [wp scaffold plugin-tests](https://developer.wordpress.org/cli/commands/scaffold/plugin-tests/)
- [@wordpress/env](https://developer.wordpress.org/block-editor/reference-guides/packages/packages-env/)
- Confirmed 2026-10-08 against current trunk: `skipWithMultisite()`, `skipWithoutMultisite()`, `setExpectedDeprecated()`, `setExpectedIncorrectUsage()`, `assertWPError()`, `assertNotWPError()`, `assertEqualSets()`, `assertSameIgnoreEOL()`, `start_transaction()`, `_create_temporary_tables()`; PHPUnit table: WordPress 6.9 uses PHPUnit 9 on PHP 7.3-8.5 (8 on 7.2), 7.0 and 7.1 use 9 on 7.4-8.5.
- Core test case source (method names for transactions, temporary tables, skip helpers): [abstract-testcase.php](https://github.com/WordPress/wordpress-develop/blob/trunk/tests/phpunit/includes/abstract-testcase.php)
