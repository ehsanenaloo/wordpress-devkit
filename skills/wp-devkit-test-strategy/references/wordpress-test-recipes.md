# WordPress test recipes

Contents: [REST permission and schema](#rest-permission-and-schema) - [AJAX and admin-post handlers](#ajax-and-admin-post-handlers) - [External HTTP](#external-http) - [Cron and scheduled work](#cron-and-scheduled-work) - [Mail](#mail) - [Rendering and escaping](#rendering-and-escaping) - [Activation, upgrade and uninstall](#activation-upgrade-and-uninstall) - [Blocks](#blocks) - [Idempotency and concurrency](#idempotency-and-concurrency) - [Scenario matrix](#scenario-matrix) - [Sources](#sources)

All examples assume `WP_UnitTestCase` from the WordPress test library and are sketches to adapt; run them in a disposable environment. Names such as `myplugin_*` are placeholders.

## REST permission and schema

Dispatching through the server tests route logic, permission callbacks and schema. It does not test cookie, nonce-header or Application Password transport; cover that once at the HTTP layer.

```php
<?php
class Test_Rest_Orders_Route extends WP_UnitTestCase {
	private $route = '/myplugin/v1/exports';

	public function set_up() {
		parent::set_up();
		$GLOBALS['wp_rest_server'] = null;
		rest_get_server(); // Builds the server and fires rest_api_init.
	}

	public function tear_down() {
		$GLOBALS['wp_rest_server'] = null;
		parent::tear_down();
	}

	public function test_anonymous_request_is_rejected_without_side_effects() {
		wp_set_current_user( 0 );
		$response = rest_do_request( new WP_REST_Request( 'POST', $this->route ) );

		$this->assertSame( 401, $response->get_status() );
		$this->assertSame( 0, (int) get_option( 'myplugin_export_count', 0 ) );
	}

	public function test_logged_in_user_without_capability_gets_403() {
		wp_set_current_user( self::factory()->user->create( array( 'role' => 'subscriber' ) ) );
		$response = rest_do_request( new WP_REST_Request( 'POST', $this->route ) );

		$this->assertSame( 403, $response->get_status() );
	}

	public function test_authorized_user_succeeds_and_input_is_validated() {
		wp_set_current_user( self::factory()->user->create( array( 'role' => 'administrator' ) ) );

		$bad = new WP_REST_Request( 'POST', $this->route );
		$bad->set_param( 'limit', -5 );
		$this->assertSame( 400, rest_do_request( $bad )->get_status() );

		$good = new WP_REST_Request( 'POST', $this->route );
		$good->set_param( 'limit', 10 );
		$this->assertSame( 200, rest_do_request( $good )->get_status() );
	}

	public function test_object_level_authorization() {
		$owner = self::factory()->user->create( array( 'role' => 'author' ) );
		$other = self::factory()->user->create( array( 'role' => 'author' ) );
		$post  = self::factory()->post->create( array( 'post_author' => $owner ) );

		wp_set_current_user( $other );
		$request = new WP_REST_Request( 'GET', '/wp/v2/posts/' . $post );
		$request->set_param( 'context', 'edit' );
		$this->assertContains( rest_do_request( $request )->get_status(), array( 401, 403 ) );
	}
}
```

Status codes: a logged-out request denied by a permission callback returns 401 and a logged-in user without the capability returns 403 (core's `rest_authorization_required_code()`). A permission callback returning `true` for a write route, or `__return_true` on a route that returns private data, is the thing to test; a public read-only route is a deliberate design and needs only a test that it exposes no private fields (`context=edit`, user emails, meta). Verify the schema with `OPTIONS` requests or `rest_get_server()->get_routes()` when a response contract matters.

## AJAX and admin-post handlers

Handlers that call `wp_die()` or `exit` need the AJAX test base class, which converts the die into exceptions.

```php
<?php
class Test_Ajax_Save_Note extends WP_Ajax_UnitTestCase {
	public function test_non_privileged_user_cannot_save() {
		wp_set_current_user( self::factory()->user->create( array( 'role' => 'subscriber' ) ) );
		$_POST['_ajax_nonce'] = wp_create_nonce( 'myplugin_save_note' );
		$_POST['note']        = 'hello';

		try {
			$this->_handleAjax( 'myplugin_save_note' );
		} catch ( WPAjaxDieContinueException $e ) {
			unset( $e ); // Handler finished through wp_die(); response is captured.
		}

		$response = json_decode( $this->_last_response, true );
		$this->assertFalse( $response['success'] );
		$this->assertSame( '', (string) get_option( 'myplugin_note', '' ), 'Capability check must run before the write.' );
	}
}
```

Notes: a bad or missing nonce typically ends in `WPAjaxDieStopException` (`-1` or `0`); assert the persisted value, not just the message. `admin_post_*` handlers normally redirect and exit; test the handler function directly with `wp_redirect` filtered to throw, or cover the full flow in the browser layer. `wp_ajax_nopriv_*` handlers are deliberate public endpoints: test abuse bounds and validation instead of demanding authentication.

## External HTTP

Block real network traffic in every test and make each expected call explicit.

```php
<?php
class Test_Remote_Sync extends WP_UnitTestCase {
	private $requests = array();

	public function set_up() {
		parent::set_up();
		$this->requests = array();
		add_filter( 'pre_http_request', array( $this, 'fake_http' ), 10, 3 );
	}

	public function tear_down() {
		remove_filter( 'pre_http_request', array( $this, 'fake_http' ), 10 );
		parent::tear_down();
	}

	public function fake_http( $preempt, $args, $url ) {
		$this->requests[] = array( 'url' => $url, 'args' => $args );
		if ( false !== strpos( $url, 'api.example.test/v1/items' ) ) {
			return array(
				'headers'  => array(),
				'body'     => wp_json_encode( array( 'items' => array() ) ),
				'response' => array( 'code' => 200, 'message' => 'OK' ),
				'cookies'  => array(),
				'filename' => null,
			);
		}
		return new WP_Error( 'unexpected_http', 'Unexpected request to ' . $url );
	}

	public function test_sync_sends_auth_header_and_handles_timeout_error() {
		myplugin_sync();
		$this->assertCount( 1, $this->requests );
		$this->assertArrayHasKey( 'Authorization', $this->requests[0]['args']['headers'] );
	}
}
```

`pre_http_request` short-circuits any non-false return. Add cases for `WP_Error`, 429/5xx, malformed JSON and a slow response; assert retry/backoff, no duplicate side effect and no secret in logs. A real sandbox call belongs in a separate, clearly marked integration job.

## Cron and scheduled work

Scheduling and execution are separate tests. Assert `wp_next_scheduled( 'myplugin_hook', $args )` after activation or save, and `wp_clear_scheduled_hook()` on deactivation. Run the job by calling `do_action( 'myplugin_hook', $args )` (WP-Cron's spawn mechanism is not part of the unit under test). Cases: the job running twice (idempotent), the job overlapping (lock), a failure midway (resume and not duplicate), a large batch (bounded memory and time, cursor advances). For Action Scheduler jobs see [woocommerce-and-data-tests.md](woocommerce-and-data-tests.md).

## Mail

The core test library replaces the mailer. `tests_retrieve_phpmailer_instance()` returns the mock mailer used by `wp_mail()`; read the sent message from it and reset in `set_up()`. Assert recipient, subject, no header injection from user-supplied names (`"\r\nBcc:"`), and that the failing mailer does not lose the underlying record. The helper is defined in the library's `includes/mock-mailer.php` (added in 4.4.0 per Trac changeset 36594; secondary search snippets, file not read directly) and returns `MockPHPMailer|false`; check it exists in the installed library version.

## Rendering and escaping

Render with the real API and assert hostile input is neutralized and the output is what a user gets.

```php
<?php
class Test_Shortcode_Output extends WP_UnitTestCase {
	public function test_attributes_are_escaped() {
		$html = do_shortcode( '[myplugin_badge label="<script>alert(1)</script>" url="javascript:alert(1)"]' );

		$this->assertStringNotContainsString( '<script>', $html );
		$this->assertStringNotContainsString( 'javascript:', $html );
		$this->assertStringContainsString( '&lt;script&gt;', $html );
	}
}
```

Use `render_block()`, `do_blocks()` or the template function for blocks and templates, and compare normalized HTML (`assertSameIgnoreEOL`, or parse with `WP_HTML_Tag_Processor` for attribute assertions) instead of whole-string snapshots that break on whitespace.

## Activation, upgrade and uninstall

- Fresh install: call the installer, assert tables, options and capabilities exist with expected defaults.
- Upgrade: seed the previous version's data shape, set the stored version option, run the upgrade routine, assert the new invariant; run it twice to prove idempotence; interrupt after write and before the version bump and rerun.
- Uninstall: create data, run `uninstall.php` in the test with `WP_UNINSTALL_PLUGIN` defined, assert removal or retention exactly as documented.
- `dbDelta()` DDL causes implicit commits and temporary-table rewriting changes schema behavior; run schema tests in their own class and assert with `SHOW COLUMNS`/`SHOW INDEX`.

## Blocks

Keep saved-content fixtures for every released version of a block. For PHP: `parse_blocks()` then `render_block()` must not emit warnings and must produce the documented markup. For JavaScript: parse the fixture with `@wordpress/blocks` in a Jest/`wp-scripts test-unit-js` test and assert the block is valid (no invalid-content recovery) or that the deprecation migrates attributes. Cover nested blocks, empty attributes, and escaped hostile attribute values.

## Idempotency and concurrency

Sequential calls do not prove atomicity. For a "last item in stock" or "single use coupon" invariant, run two PHP processes or two Playwright contexts against the same row with a barrier and assert one succeeds. For webhook replays send the same payload twice and assert one effect. Mark these tests as slow and run them in the integration job.

## Scenario matrix

| Surface | Positive control | Negative and failure controls |
| --- | --- | --- |
| Settings save | Authorized valid input persists | Low capability, bad nonce, invalid shape leaves old value, unchanged screens load no assets |
| REST write | Authorized actor, valid params | 401 and 403 split, other user's object, invalid param, no side effect on denial |
| Public submission | Valid anonymous request accepted | Oversized, malformed, repeated, honeypot/rate bound; absence of a nonce alone is not a defect |
| Uninstall/upgrade | Data preserved or removed as documented | Re-run, partial run, multisite |
| Cache | Cold and warm agree | Invalidation on write, user-specific data does not leak across users |
| Cron job | Runs and finishes | Double run, failure midway, large batch |
| Block | Saved fixtures render | Old versions, hostile attributes |
| i18n | Strings load in a non-English locale | RTL, plural forms |

## Sources

Reviewed 2026-10-08.

- [Writing PHPUnit tests (core)](https://make.wordpress.org/core/handbook/testing/automated-testing/writing-phpunit-tests/)
- [pre_http_request](https://developer.wordpress.org/reference/hooks/pre_http_request/)
- [WP_Ajax_UnitTestCase source](https://github.com/WordPress/wordpress-develop/blob/trunk/tests/phpunit/includes/testcase-ajax.php)
- [REST API handbook: authentication and permission callbacks](https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-custom-endpoints/)
