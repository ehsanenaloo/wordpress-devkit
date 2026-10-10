---
name: wp-devkit-wpcli-and-ops
description: "Build, debug or review WP-CLI commands and WordPress operations runbooks. Use for serialized-safe search-replace and domain moves, multisite targeting, batch jobs, cron and cache maintenance, backups and recoverable procedures; not application code."
---

# Scoped commands and operational recovery

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Inputs and scope

Explicit environment (path, URL, alias, SSH host), WP-CLI/PHP/WordPress versions, command or runbook under review, selected tables/IDs/sites, write effects, whether the project bootstrap is trusted, backup and rollback requirements, multisite yes/no.

Inspect project evidence before asking. State material assumptions. Ask only what changes the decision or execution boundary. Follow existing command names, flags and runbook conventions.

## Boundaries with sibling skills

Plugin hooks, upgrade logic and storage design go to `wp-devkit-plugin-development`; migration/upgrade risk assessment of a whole site goes to `wp-devkit-migration-upgrade-review`; CI/release pipelines to `wp-devkit-ci-cd-and-release-engineering`; cache and query performance diagnosis to `wp-devkit-performance-review`. This skill owns the command, its targeting and safety, and the recovery procedure around it.

## Code Review Workflow

1. Read the command source, `wp-cli.yml`, aliases and scripts without loading WordPress: a command that loads WordPress runs the project's bootstrap, so "read-only" is not a property of the verb.
2. Confirm target identity: `--path`, `--url`, alias, DB prefix, network vs site scope, environment. Check the installed `wp help <command>` before assuming flags such as `--dry-run` exist; `--dry-run` is per command.
3. Classify each operation: inventory, diagnostic with effects (`cron event run`, `cache flush`, `eval`), reversible, irreversible. For irreversible ones require a verified backup, a dry run, scope and approval.
4. For code: argument validation before writes, stable keyed batching with a fixed upper bound, per-query and per-write error handling, truthful counts and non-zero exit on partial failure, site context restored on every path, dry run with zero side effects.
5. For runbooks: preconditions, exact commands, expected output, independent verification, rollback with a rehearsed restore, abort criteria, redacted logs.
6. Describe the plan and verification without running maintenance or mutating commands. Classify per the contract; use `insufficient evidence` when target, version or backup state cannot be established.

Read `references/wpcli-and-ops-workbook.md` for symptom triage, worked decisions, benign look-alikes and verification. Load topic references only when in scope:

- `references/command-authoring.md`: read for registering commands, synopsis, dry run, exit codes, batching and memory, `runcommand`, testing.
- `references/search-replace-and-migrations.md`: read for domain moves, serialized and JSON data, GUIDs, `--export`, backups, destructive DB commands.
- `references/multisite-and-batch-operations.md`: read for `--url`/`--network`, site iteration, `switch_to_blog`, long jobs, WP-Cron vs system cron, cache and transient maintenance, locks.
- `references/environment-safety-and-recovery.md`: read for config precedence and aliases, bootstrap risk, `--skip-plugins`, operation classes, backups and restore rehearsal, CI, runbook template.

## Implementation workflow

1. Define the operation, target, blast radius and rollback before writing anything. State the plan and checks first.
2. Build the command: namespaced, documented synopsis, validate all input, plan then confirm then mutate, `--dry-run` that writes nothing, stable cursor, checkpoint after verified batches, truthful exit codes, machine-readable output option.
3. Test: empty set, one item, exact batch multiple, mid-run failure, interruption and resume, dry-run side-effect assertions, multisite context restore.
4. Execution against any real environment (including maintenance mode, backups, flushes) is a separate, explicitly authorized task. Report unavailable checks as unexecuted.

## Search Patterns for Quick Detection

Run only relevant groups from the first-party root; narrow `.`. The commands read files and never run WP-CLI or load WordPress. Hits are leads, not findings; no hit proves nothing (scripts, CI files and multiline calls hide matches). Exit 0 match, 1 none, 2 error.

```sh
# Commands, config, aliases
rg -n -g '*.{php,yml,yaml}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'WP_CLI::add_command|WP_CLI_Command|@when|before_invoke|^require:|^path:|^url:|^@[a-z]' .
# Destructive or executable operations
rg -n -g '*.{php,sh,ps1,yml,yaml,md}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'wp\s+(db\s+(reset|drop|import|clean)|site\s+(delete|empty)|eval(-file)?|search-replace|post\s+delete)|--force|--yes' .
# Preview and target selection
rg -n -g '*.{php,sh,ps1,yml,yaml,md}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e '--dry-run|--url|--path|--network|--all-tables|--all-tables-with-prefix|--skip-columns|--skip-plugins|--ssh' .
# Paging, progress, exit behavior
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'make_progress_bar|WP_CLI::(error|warning|success|halt|confirm|runcommand)|last_error|OFFSET|offset|checkpoint|batch' .
# Multisite context and user policy
rg -n -g '*.{php,sh,ps1,yml,yaml,md}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'switch_to_blog|restore_current_blog|get_sites|site\s+list|is_super_admin|--user' .
# Cache and scheduled maintenance
rg -n -g '*.{php,sh,ps1,yml,yaml,md}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'wp\s+(cache|transient|cron|rewrite)|wp_cache_flush|DISABLE_WP_CRON|wp_schedule_event|flock' .
```

Read the match context and the enclosing script before reporting.

## Task-selected resources

- `references/operations-cache-prime-fixture.php`: an optional disposable WP-CLI command example; its limits are in the workbook. Load only in an inspected disposable environment.

## Acceptance checks

In a disposable site with the same WP-CLI major version: malformed arguments fail before writes; `--dry-run` leaves rows, options and cache keys unchanged; empty data exits 0; an injected database or write failure exits non-zero with counts; interrupt-and-resume processes the expected set; multisite run restores the original blog ID and reports per-site failures; the backup restores on a scratch database; remaining-occurrence and sample-URL checks pass after a replace. Tools: Behat (WP-CLI tests), PHPUnit for extracted logic, shellcheck for wrapper scripts, `wp --info` recorded in the log. A pass proves the tested scope and versions; it does not prove production data volume, concurrent writers, other WP-CLI versions or backend caches.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: `file:line`, actor, trigger, reachable path, impact, confidence, severity (per contract), minimal fix, regression. Candidates and missing evidence separate. Implementation or runbook: target, plan, commands with expected output, verification, rollback, executed vs unexecuted checks and exit statuses.
