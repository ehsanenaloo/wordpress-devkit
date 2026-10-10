# Authoring WP-CLI commands

Contents: registration; synopsis and docblock; trust model; argument validation; dry run; output and exit codes; batching and memory; progress; running other commands; distribution; testing; failure symptoms; sources.

Verified against the WP-CLI commands cookbook and internal API pages on 2026-10-08. Latest WP-CLI release seen: v2.12.0 (2025-05-07). Always check `wp --version` and `wp help <command>` on the target; flags differ across versions.

## Registration

```php
if ( defined( 'WP_CLI' ) && WP_CLI ) {
	WP_CLI::add_command( 'acme sync', 'Acme_Sync_Command' );   // class with __invoke, or subcommand methods
}
```

- Load command files only when `WP_CLI` is defined so web requests never include them.
- A class with `__invoke()` registers one command; otherwise each public method is a subcommand. Use `@subcommand` when a method name is reserved (`list`) and `@alias` for aliases.
- Third argument: `shortdesc`, `synopsis`, `when`, `longdesc`, `before_invoke` (for example require multisite or check a precondition once).
- `@when before_wp_load` has no effect for commands loaded from a plugin or theme (verified); default is `after_wp_load`. Commands that must run without WordPress belong in a standalone package.
- Namespace commands (`acme ...`) to avoid collisions with core and other packages.

## Synopsis and docblock

The docblock is the contract: first line is the short description; `## OPTIONS` and `## EXAMPLES` follow Markdown Extra. Syntax: `<name>` required positional, `[<name>]` optional, `<name>...` repeating, `--flag=<value>` associative, `[--dry-run]` boolean flag, defaults and allowed values in a `---` YAML block. WP-CLI validates the call against the synopsis before invoking you; unknown arguments, missing required values and invalid `options` enums fail with a usage error and a non-zero exit.

```php
/**
 * Re-sync stale records.
 *
 * ## OPTIONS
 *
 * [--batch-size=<number>]
 * : Records per batch.
 * ---
 * default: 100
 * ---
 *
 * [--dry-run]
 * : Report what would change; write nothing.
 *
 * ## EXAMPLES
 *
 *     wp acme sync --batch-size=200 --dry-run
 */
public function __invoke( $args, $assoc_args ) { /* ... */ }
```

`$args` holds positionals; `$assoc_args` holds values, flags (`true`) and `--no-flag` (`false`). Use `WP_CLI\Utils\get_flag_value( $assoc_args, 'dry-run', false )` for flags. Do not rely on synopsis defaults to enforce ranges; validate numbers yourself.

## Trust model

The operator already has shell access to the server, so the CLI trust boundary is the operating system. Browser nonces are not required. Add WordPress-user policy only when the command promises it: run with `--user=<id|login|email>` and check `current_user_can()` for commands that act "as" a user (audit attribution, capability-gated content operations). Never accept SQL fragments or PHP code as arguments; never `eval` input. Redact secrets from output and logs.

## Validate before you write

Order: parse and validate all arguments; resolve target (site, IDs); compute the plan; print the plan; confirm when destructive (`WP_CLI::confirm( $msg, $assoc_args )` honors `--yes`); then mutate. Reject nonsensical ranges early:

```php
$raw = (string) ( $assoc_args['batch-size'] ?? '100' );
if ( ! ctype_digit( $raw ) || (int) $raw < 1 || (int) $raw > 1000 ) {
	WP_CLI::error( 'Batch size must be an integer from 1 to 1000.' );
}
```

## Dry run

`--dry-run` is not a global flag; each command defines it. A dry run must have zero side effects: no writes, no cache fills, no progress/state options, no emails, no remote calls with effects. Print counts and identifiers of what would change. Test it by asserting row counts, options and cache keys before and after.

## Output and exit codes (verified)

- `WP_CLI::log()` for progress to STDOUT, `WP_CLI::warning()` continues, `WP_CLI::error( $message, $exit = true )` writes to STDERR and exits with code 1 (an integer `$exit` is documented as accepted), `WP_CLI::halt( $code )` stops with a specific code, `WP_CLI::success()` for the final state.
- Make exit codes truthful: any failed write, failed query (check `$wpdb->last_error` / `false === $result`), failed cache write or partial processing must end with `WP_CLI::error()` (non-zero), never a "success" line. A job that processed 90 of 100 items and swallowed ten failures must exit non-zero with counts: processed, skipped, failed.
- An empty result set after a database error is a failure, not "nothing to do".
- Machine output: support `--format=table|json|csv|ids|count` via `WP_CLI\Utils\format_items( $format, $items, $fields )`; print only data to STDOUT and messages to STDERR (`--quiet` suppresses logs) so pipelines (`| jq`, `xargs`) work.

## Batching, ordering and memory

- Select with a stable cursor: `WHERE ID > %d AND ID <= %d ORDER BY ID ASC LIMIT %d`, with the upper bound captured at start. Do not use `OFFSET` over data that changes during the run (rows shift and are skipped). A cursor is not a snapshot: rows inserted below the cursor or updated mid-run are not revisited; state the policy (rerun, reconcile).
- Long runs leak memory: `$wpdb->queries` grows with `SAVEQUERIES`; the runtime object cache grows. Call `wp_cache_flush_runtime()` (6.0+, runtime cache only) every batch on persistent-cache sites, or `wp_cache_flush()` only when the whole cache may be dropped (it affects production, see operations notes). Use `no_found_rows => true`, `fields => 'ids'`, and `update_post_meta_cache => false` where possible.
- Make each batch independently retryable; record a checkpoint option only after the batch is verified; expose `--resume-from=<id>` or read the checkpoint, and document that a checkpoint is not a lock (two workers must not run concurrently: use `flock` on a lock file or a named option lock).
- Multisite loops: see [multisite-and-batch-operations.md](multisite-and-batch-operations.md).

## Progress

`$bar = WP_CLI\Utils\make_progress_bar( 'Syncing', $total ); $bar->tick(); $bar->finish();` `make_progress_bar()` returns a no-op object when STDOUT is piped (`Shell::isPiped()` in WP-CLI `utils.php`), so do not parse or depend on bars. For long jobs also log periodic structured lines (timestamp, cursor, counts) to a file for observability.

## Running other commands

`WP_CLI::runcommand( $command, $options )`: `launch` (default true: new process, fresh state), `exit_error` (default true), `return` (`'all'`, `'stdout'`, `'stderr'`, `'return_code'`), `parse` (`'json'`), `command_args`. Use `'return' => 'all', 'exit_error' => false` to inspect failures. `WP_CLI::launch_self()` re-runs the current WP-CLI with the runtime arguments. Pass `--url`/`--path` explicitly when targeting other sites.

## Distribution

Bundle in a plugin (conditional load) or ship as a package (`composer.json` with `"type": "wp-cli-package"` and an `autoload` entry; installed with `wp package install`). Commands bundled in a plugin are not available with `--skip-plugins`; mention that in runbooks.

## Testing

- Behat (the WP-CLI framework `wp-cli/wp-cli-tests`) for end-to-end: scaffold with `wp scaffold package-tests <dir>` (provided by the `wp-cli/scaffold-package-command` package; core `wp scaffold` has `plugin-tests` and `theme-tests`). Assert STDOUT, STDERR and return codes, including failure paths.
- PHPUnit for the logic extracted from the command class (batcher, planner) with `WP_UnitTestCase`.
- Fixtures: a disposable site seeded with known IDs; test empty set, one item, exact multiple of the batch size, mid-run failure, interruption and rerun, and dry run side-effect assertions.

## Failure symptoms

| Symptom | Evidence | Fix |
|---|---|---|
| Exit 0 though items failed | Errors logged as warnings or ignored | `WP_CLI::error` or non-zero halt with counts |
| Dry run changes state | Cache/option writes on the dry-run path | Gate all writes on the flag; test side effects |
| Rows skipped | `OFFSET` pagination over changing data | Keyed cursor with fixed upper bound |
| Memory growth | Query log / object cache | Flush runtime cache per batch, `SAVEQUERIES` off |
| Command missing in production | Plugin skipped via `--skip-plugins` or load guard | Check invocation and `WP_CLI` guard |
| Usage error before code runs | Synopsis mismatch | Fix docblock |

## Sources (checked 2026-10-08)

- Commands cookbook: https://make.wordpress.org/cli/handbook/guides/commands-cookbook/
- Internal API: https://make.wordpress.org/cli/handbook/references/internal-api/ , `WP_CLI::runcommand`, `WP_CLI::error` pages under the same path.
- `wp_cache_flush_runtime`: https://developer.wordpress.org/reference/functions/wp_cache_flush_runtime/
- WP-CLI releases: https://github.com/wp-cli/wp-cli/releases

Confirmed in WP-CLI main source (2026-10-08): `WP_CLI::halt( $return_code )` exits with that integer (`php/class-wp-cli.php`); `WP_CLI::confirm( $question, $assoc_args )` skips the prompt when `yes` is set and calls a bare `exit` (status 0) when the answer is not `y`, so a declined prompt is not a failure exit; `make_progress_bar()` is a no-op when piped (`php/utils.php`); `wp scaffold package-tests` exists in https://github.com/wp-cli/scaffold-package-command. Sources: https://github.com/wp-cli/wp-cli/blob/main/php/class-wp-cli.php, https://github.com/wp-cli/wp-cli/blob/main/php/utils.php. Behavior can differ by WP-CLI version: check `wp --version` and `wp help` on the target.
