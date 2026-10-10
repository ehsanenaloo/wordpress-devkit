# Search-replace, database moves and migrations

Contents: what `search-replace` does; scoping flags; GUIDs; serialized data and JSON; multisite; a safe procedure; domain-move recipes; things it will not fix; export/import; verification; failure symptoms; sources.

Never run a write operation from a review. Everything below is for a separately authorized execution on a verified target.

## What `wp search-replace` does (verified against the command page)

It replaces strings across database tables, handling PHP-serialized data correctly (it unserializes, replaces, recomputes lengths and reserializes) instead of a raw SQL `REPLACE`, which corrupts serialized string lengths. Key flags:

| Flag | Meaning |
|---|---|
| `--dry-run` | Full run and report, nothing saved. Default off. |
| `--network` | Multisite: all tables registered to `$wpdb`. Without it only the current site's tables. |
| `--all-tables-with-prefix` | Also unregistered tables that match the prefix. |
| `--all-tables` | Every table regardless of prefix; overrides the two above. |
| `<table>...`, `--skip-tables`, wildcards | Explicit table scope. |
| `--skip-columns=guid`, `--include-columns=` | Column scope (`table.column` allowed). |
| `--export[=<file>]` | Write transformed SQL instead of updating the database; leaves the source untouched. |
| `--precise` | Force PHP processing for all columns instead of fast SQL; slower, safer for complex serialized data. |
| `--recurse-objects` (default true) | Replace inside objects; `--no-recurse-objects` to disable. |
| `--regex`, `--regex-flags`, `--regex-delimiter`, `--regex-limit` | Regex mode, about 15-20 times slower. |
| `--report`, `--report-changed-only`, `--format=table|count`, `--log[=<file>]`, `--verbose` | Reporting; `--log` slows the run significantly. |

Tables without a primary key are skipped (check with `wp db query 'DESCRIBE <table>'`). Primary key values are not changed.

## GUIDs

Leave `guid` alone for ordinary domain moves: GUIDs are permanent identifiers (feed readers treat a changed GUID as a new item) and need not match the live URL. The command's own examples use `--skip-columns=guid`. Replace GUIDs only for an exceptional, explicitly documented policy.

## Serialized data, JSON and other encodings

- Serialized PHP (options, widgets, page-builder meta): handled by the command.
- JSON stored as text (block attributes, Elementor, some page builders) with escaped slashes (`https:\/\/old.example`): the plain search string `https://old.example` does not match in older releases. Current `search-replace-command` source also builds JSON-encoded forms of the search and replace strings (`json_encode_strip_quotes` in `Search_Replace_Command.php`); on an older WP-CLI run a second pass with the escaped form, or use `--regex` carefully. Verify with a count before/after.
- URL-encoded and base64 content is not decoded; those occurrences need a separate, reviewed pass or application-level regeneration.
- Do not use search-replace on a replacement that changes string length inside values you cannot unserialize (the replacer warns "Skipping an inconvertible serialized object ... replacements might not be complete" for some failures, and by default only `stdClass` objects are instantiated; check the output for warnings).
- `siteurl`/`home` are options and are included; for a staging move also review constants `WP_HOME`, `WP_SITEURL` and `wp-config.php`, which the database replace never touches.

## Multisite

Domain moves on a network change `wp_blogs` and `wp_site` rows plus per-site option tables. Use `--network` with explicit `--url` for the main site, review `DOMAIN_CURRENT_SITE`, `PATH_CURRENT_SITE` and `COOKIE_DOMAIN`, and check `wp site list` afterward. `--all-tables-with-prefix` can include tables of every site; narrow to explicit tables or per-site runs when only one site moves.

## Safe procedure

1. Identify the target: `wp --path=/var/www/site --url=https://old.example option get home` plus `wp config get DB_NAME --path=...` and `DB_HOST` (never print `DB_PASSWORD`) and `wp db prefix`. Confirm production vs staging by a deliberate fact, not the directory name.
2. Back up and prove the backup: `wp db export /secure/backup-$(date +%F).sql --tables=...` (or the whole DB) and check the file is non-empty and importable on a scratch database. A backup copy on the same disk/host is not a recovery plan; record the restore command.
3. Dry run with the final scope: `wp search-replace 'old.example' 'new.example' --skip-columns=guid --all-tables-with-prefix --dry-run --report-changed-only`. Review per-table counts for surprises (log tables, session tables, `wp_options` cache rows).
4. Maintenance mode for production moves (`wp maintenance-mode activate` and deactivate afterward), or a read-only window, so writes do not race the replace.
5. Execute the same command without `--dry-run`, logging output to a file; capture the exit code.
6. Flush: `wp cache flush` (flushes the whole object cache, on multisite typically all sites; production impact), `wp rewrite flush`, clear page/CDN caches, regenerate builder CSS caches if applicable.
7. Verify independently: a counted grep over a database export (`wp db export - | grep -c 'old.example'`), `wp option get home siteurl`, a crawl or scripted check of sample URLs, mixed-content scan, admin login, media URLs, multisite domain mapping, and a restore rehearsal when data loss would be severe.

## Prefer `--export` for staged moves

`wp search-replace ... --export=transformed.sql` produces a transformed dump and leaves the source database unchanged, which turns the dangerous step into a reviewable artifact; import it into the target with `wp db import` (not creating the database; `-` reads STDIN; `--skip-optimization` keeps unique/foreign key checks on).

## Other database operations that are destructive

`wp db reset --yes` removes all tables; `wp db import` executes whatever SQL the file contains (DROP/CREATE included); `wp db clean`, `wp site empty`, `wp site delete` are irreversible without a backup. `wp eval`/`eval-file` run arbitrary PHP in the loaded site; they load project bootstrap and plugins (read-only-looking code can still write). Require explicit scope and a plan before use; never run a downloaded script that has not been read.

## What search-replace will not fix

Hard-coded URLs in theme/plugin files, `wp-config.php` constants, `.htaccess`/server rules, CDN origins, cookies and sessions, object/page caches, content in external services, and email links already sent.

## Failure symptoms

| Symptom | Evidence | Fix direction |
|---|---|---|
| Widgets/options broken after move | Raw SQL `REPLACE` on serialized data | Restore backup; redo with `wp search-replace` |
| Old URLs remain in block/builder content | Escaped-slash JSON | Second pass with escaped strings; verify counts |
| Wrong site changed | Missing `--url`/`--path`, `--all-tables` on shared prefix | Stop; restore; rerun with explicit targeting |
| Feed duplicates after move | GUIDs replaced | Restore GUIDs from backup if feasible |
| Very slow run | `--regex`, `--log`, huge tables | Limit tables/columns; run in window; consider `--export` |
| Login loops after domain change | Cookie domain/constants not updated | Fix `COOKIE_DOMAIN`, `WP_HOME`/`WP_SITEURL` |

## Sources

Research date: 2026-10-08.

- `wp search-replace`: https://developer.wordpress.org/cli/commands/search-replace/
- `wp db export`: https://developer.wordpress.org/cli/commands/db/export/
- `wp db import`: https://developer.wordpress.org/cli/commands/db/import/
- `wp db reset`: https://developer.wordpress.org/cli/commands/db/reset/
- `wp eval-file`: https://developer.wordpress.org/cli/commands/eval-file/
- `wp cache flush`: https://developer.wordpress.org/cli/commands/cache/flush/
- `wp maintenance-mode`: https://developer.wordpress.org/cli/commands/maintenance-mode/

Notes from https://github.com/wp-cli/search-replace-command (README and source): flags table, tables without a primary key skipped, JSON-encoded string handling, inconvertible-serialized-object warning. Check the report for corrupt serialized values, which may be altered partially instead of skipped; check `wp help` for `wp db clean` and `wp site empty`; the backup step is operational practice, not a documented requirement.
