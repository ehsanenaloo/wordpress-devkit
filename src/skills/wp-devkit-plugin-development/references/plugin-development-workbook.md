# Plugin lifecycle and integration workbook

Contents: establish the behavior; decision checkpoints; symptom triage; worked decisions; looks wrong but is fine; severity guidance; verification; sources.

Apply [the engineering contract](engineering-contract.md) before classifying a concern. Topic depth lives in the four references linked from `SKILL.md`; this file routes symptoms to them and fixes the verdict rules.

## Establish the behavior

Record: entry file and loading mode, channel, declared vs tested WordPress/PHP versions, multisite status, failing request, expected vs observed result, and existing tests. Keep one expected/observed example per affected journey. Locate the owning callback, stored record or file before editing. A search hit is a lead, not a runtime result.

## Decision checkpoints

| Decision | What changes the answer |
|---|---|
| Loading mode | Must-use plugins and drop-ins have no activation/deactivation hooks; network activation runs the hook once with `$network_wide`. |
| Lifecycle stage | Install/activation, versioned upgrade, deactivation and uninstall are separate. Updates never rerun activation. |
| Hook contract | Timing, priority, `accepted_args`, return on every branch, removal identity. Classes are not inherently better than functions. |
| Registration | Post types, taxonomies, blocks on `init`; flush rewrite rules only on a registration change. |
| Storage | Option vs meta vs table vs transient by access pattern; autoload by read frequency and size (see storage reference). |
| Jobs | Idempotent, schedule-once, time-boxed, cleared on deactivation; queue for retries. |
| Packaging | Shipped artifact (not repository) is what is tested; channel rules apply only to that channel. |

## Symptom triage

| Symptom | Evidence to gather | Action after confirmation |
|---|---|---|
| Plugin activates, feature missing | Registration timing, dependency load order, `did_action` | Move registration to the hook that supplies the context; do not re-initialize every request. |
| Upgrade leaves old state | Stored version marker, which steps completed | Add a versioned idempotent step; advance the marker after verified success (see lifecycle reference). |
| Filter blanks content or breaks other plugins | Return value per branch, later callbacks | Return the (modified) input on every path. |
| `remove_action` has no effect | Registered callback identity, priority, timing | Remove with the same instance/priority after registration. |
| Duplicate scheduled work | `wp cron event list`, `as_get_scheduled_actions` | Check before scheduling, clear on deactivation, make the job idempotent. |
| Site slow on every page | Autoload total, largest autoloaded rows, `plugins_loaded` work | Set `autoload` false for large options; defer work to the needing request. |
| 6.7+ notice about translation loading | Backtrace of `_load_textdomain_just_in_time` | Defer translated strings to `init` or later. |
| ZIP fails on a clean site | Archive listing, autoload paths, case sensitivity | Package runtime dependencies; fix case; do not require user-side builds. |
| Multisite: new site lacks tables | Network activation path | Provision on `wp_initialize_site` and/or in the versioned upgrade. |

If the evidence does not support the cause, keep the hypothesis open and inspect the next boundary. Do not add a fallback that changes the promised behavior.

## Worked decisions

Independently written teaching illustrations, not executed tests. Integrate with the project's existing contracts and verified target versions.

### 1. Filter modifies a local value but returns nothing

Problem: `add_filter( 'body_class', static function ( $classes ) { $classes[] = 'acme'; } );` returns `null`. Fix: add `return $classes;` on every branch. Verify the rendered body classes with the condition true and false, and that a second probe callback still receives the array.

### 2. Table created only in the activation hook

Context: version 1.2 adds `acme_events`. Sites updating from 1.1 never activate again, so the table is missing and queries fail. Confirm: `wp db query "SHOW TABLES LIKE '%acme_events'"`, installed marker is `1.1`. Fix: run `dbDelta()` from the versioned upgrade routine (idempotent, locked) and keep activation calling the same function. Regression: install 1.1, update to 1.2, assert table and marker; run again, assert no change.

### 3. Rewrite flush on every request

`add_action( 'init', function () { acme_register_types(); flush_rewrite_rules(); } );` regenerates and rewrites the `rewrite_rules` option on every hit (a hard flush may also attempt to update the server rewrite file). Confirm with a query count or a counter on `update_option( 'rewrite_rules' )`. Fix: flush on activation/deactivation and on a version bump that changed registration. Regression: two requests produce zero `rewrite_rules` writes; new and old permalinks and pagination resolve.

### 4. Removal with a new instance

`remove_action( 'init', array( new Acme_Loader(), 'boot' ) )` removes nothing: a different object. Fix: keep the instance or expose an accessor and remove with the same priority after registration. Regression: assert `has_action` is `false` after removal and the callback no longer fires.

### 5. Uninstall deletes user content unconditionally

`uninstall.php` deleting all posts of the plugin's type on delete destroys data after a troubleshooting deactivate-and-delete. Fix: retention by default; opt-in setting to purge. Regression: delete plugin with the setting off (data remains) and on (data and options gone; other plugins' data untouched).

## Looks wrong but is fine

- Small procedural plugin with a unique prefix: no namespace, container or activation callback is required.
- Closure callbacks on hooks nobody needs to unhook.
- No `uninstall.php` when the plugin stores nothing persistent.
- Option written with `autoload` false and read lazily.
- `is_admin()` used to choose admin-only UI assets (not for authorization).
- Missing `Requires Plugins` when the optional integration is guarded at runtime.

## Severity guidance (apply the contract)

- CRITICAL: reachable fatal on activation/update of supported versions, irreversible data deletion on a default path, schema migration that corrupts data, or a security issue with a traced path.
- WARNING: duplicate jobs, per-request rewrite flushes, large autoloaded options, unsupported-version syntax inside the declared range, removal that cannot work.
- INFO: structure, naming, optional hardening.
- Candidate / insufficient evidence: any item whose version range, loading mode or reachable path is unproven. State what would settle it.

## Verify the outcome

- Fresh install, update from the oldest supported marker, and repeat setup all reach the intended schema; repeat setup duplicates nothing (`wp cron event list`, option count).
- Deactivation preserves user content; uninstall follows the declared policy.
- Clean ZIP install loads the feature; `wp plugin check` triaged; PHPCS/PHPStan clean at the configured level.
- Record runner, versions, fixture, result and exit status. A pass proves only the exercised path, versions and data volume; it does not prove other PHP/WordPress versions, multisite, persistent object cache or concurrent upgrades unless those were part of the matrix.

## Delivery evidence

State the practical result, the changed owner and the remaining limits. Separate confirmed findings, candidates, executed and unexecuted checks. Do not claim compatibility, performance or security beyond the recorded environment.

## Sources

Research date: 2026-10-08.

- Plugin basics: https://developer.wordpress.org/plugins/plugin-basics/
- Header requirements: https://developer.wordpress.org/plugins/plugin-basics/header-requirements/
- Uninstall methods: https://developer.wordpress.org/plugins/plugin-basics/uninstall-methods/
- Hooks: https://developer.wordpress.org/plugins/hooks/
- Directory guidelines: https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/
