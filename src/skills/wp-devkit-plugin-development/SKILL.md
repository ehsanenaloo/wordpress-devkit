---
name: wp-devkit-plugin-development
description: Build, debug or review WordPress plugin lifecycle, hooks, upgrade routines, storage, scheduled jobs and packaging. Use for activation/upgrade/uninstall failures, hook order or removal bugs, multisite setup and directory readiness; not REST routes, admin screens or WP-CLI.
---

# Plugin lifecycle and integration

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Inputs and scope

Plugin entry file, loading mode (regular, network-activated, must-use, drop-in), distribution channel (WordPress.org, private ZIP, Composer), declared and actually supported WordPress/PHP versions, multisite yes/no, failing request or symptom, existing tests.

Inspect project evidence before asking. State material assumptions. Ask only what changes the decision or the execution boundary. Follow existing architecture, naming and public contracts (hook names, option keys, table names, REST routes are public API).

## Boundaries with sibling skills

Hand off instead of absorbing: REST routes, schemas and permissions go to `wp-devkit-rest-api-development`; settings pages, list tables and admin assets go to `wp-devkit-admin-ui-development`; WP-CLI commands, search-replace and runbooks go to `wp-devkit-wpcli-and-ops`. Exploitable-input analysis beyond the lifecycle questions here belongs to `wp-devkit-security-review`. This skill owns the plugin skeleton those features hang on.

## Code Review Workflow

1. Identify the real entry file and loading mode. Trace bootstrap, dependency loading and hook registration to the first point where observed behavior departs from the expected lifecycle.
2. Classify each concern into one lifecycle stage: install/activation, versioned upgrade, runtime, deactivation, uninstall. Updates never rerun activation; must-use plugins and drop-ins have no activation hooks.
3. For each hook, confirm timing, priority, accepted-args count and (for filters) the return value on every branch. Confirm removal uses the registered callback identity.
4. For storage and jobs, check ownership of the schema or option, autoload and size, idempotence of repeat runs, multisite scope and uninstall policy.
5. For packaging, compare the declared headers, text domain, shipped files and dependencies against the real runtime. Do not build, install or activate during review.
6. Classify per the contract. Pattern hits stay candidates until the reachable path is traced; use `insufficient evidence` when the target version, loading mode or runtime cannot be established.

Read `references/plugin-development-workbook.md` for symptom triage, worked decisions, benign look-alikes and acceptance checks. Load topic references only when in scope:

- `references/lifecycle-and-upgrades.md`: read for headers, activation/deactivation/uninstall, versioned upgrades, dbDelta, dependencies, multisite provisioning.
- `references/hooks-and-callbacks.md`: read for hook order, priorities, removal, recursion, custom hooks, request-context detection, early-translation notices.
- `references/storage-jobs-and-multisite.md`: read for options and autoload, transients and object cache, custom tables, `$wpdb->prepare`, WP-Cron, Action Scheduler, privacy hooks, `switch_to_blog` cost.
- `references/packaging-and-compatibility.md`: read for directory rules, Plugin Check, readme, Composer and prefixing, PHP-version gates, release ZIP checks.

## Implementation workflow

1. Write the expected behavior and the smallest affected boundary; state the design and validation plan before editing.
2. Keep behavior in its current owner. Register at the hook that supplies the context the code needs. Add a class or layer only for a concrete responsibility or test seam.
3. Make every lifecycle step idempotent and safe to retry. Record version markers only after the step is verified.
4. Prove the original failure with a test or disposable-site reproduction first, then the fix. Run the acceptance checks below; report any check you could not run as unexecuted.
5. Publishing, tagging, deployment and live maintenance need their own task scope.

## Search Patterns for Quick Detection

Run only the groups that match the task from the first-party project root; narrow `.` where possible. These commands read files and never bootstrap WordPress. Hits are leads, not findings; no hit proves nothing (helpers, multiline code and generated files change the result). Exit 0 means a match, 1 none, 2 an error; record errors separately.

```sh
# Identity, headers, lifecycle
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'Plugin Name:|Requires (PHP|at least|Plugins):|Update URI:|Network:|register_(activation|deactivation|uninstall)_hook|WP_UNINSTALL_PLUGIN' .
# Hook contract and removal
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'add_(action|filter)\(|remove_(action|filter)\(|apply_filters|do_action' .
# Content registration and rewrites
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'register_(post_type|taxonomy)|add_rewrite_rule|flush_rewrite_rules' .
# Storage, schema, jobs
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'dbDelta|\$wpdb->|(add|update)_option\(|set_transient|wp_(schedule|next_scheduled|clear_scheduled)|as_(enqueue|schedule|unschedule)' .
# Assets, paths, translations
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'wp_enqueue_(script|style)|plugin_dir_(path|url)|/wp-content/plugins/|load_plugin_textdomain|Text Domain:|Domain Path:' .
```

Verify each hit: the callback is reachable, the stage is the one you assumed, and a core API or an existing guard does not already cover it.

## Acceptance checks

Run in a disposable site: `wp plugin activate <slug>` then `wp plugin deactivate <slug>` then activate again (no duplicate cron events, no fatal, no "unexpected output"); upgrade from the oldest supported stored version; `wp cron event list`; `wp option get <version-key>`; PHPUnit or integration tests for changed hooks; `wp plugin check <slug>` when targeting the directory; PHPCS with WordPress standards and PHPStan if configured. A pass shows the exercised paths work on that PHP/WordPress pair; it does not prove other versions, multisite, object-cache or high-concurrency behavior.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: `file:line`, actor, trigger, reachable path, impact, confidence, severity (per contract), minimal fix, regression check. List candidates and missing evidence separately. Implementation: changed boundaries, design decision, commands run with exit status, unexecuted checks, rollback note and residual risk.
