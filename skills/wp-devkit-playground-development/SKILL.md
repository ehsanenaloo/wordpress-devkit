---
name: wp-devkit-playground-development
description: "Build, debug or review WordPress Playground Blueprints, @wp-playground/cli setups, query/embed links and shareable plugin or theme reproductions. Use for boot failures, resource/mount problems and untrusted-Blueprint review. Not a substitute for real MySQL or host testing."
---

# Portable reproductions and trusted Blueprints

Read `references/engineering-contract.md` first. Review requests stay read-only: read Blueprints and configs, never boot them, execute their PHP/SQL/WP-CLI steps, or fetch their resources. Implementation or runtime verification applies only when the request authorizes it, in a disposable environment.

## Inputs

What must be reproduced or demonstrated, the artifact under test and its identity, Blueprint schema generation, resolved WordPress and PHP versions, CLI package version, Node version, mounts, and whether booting is authorized. Inspect project files first; ask only what changes the decision.

## Boundaries

- Test strategy and CI design for the plugin itself: `wp-devkit-test-strategy` and `wp-devkit-ci-cd-and-release-engineering`; this skill covers the Playground layer.
- Security review of the plugin under test: `wp-devkit-security-review`.
- Real database, cache, cron or host behavior: use wp-env/Docker, not Playground.

## Code Review Workflow

1. List every step and resource; read all `runPHP`, `runPHPWithOptions`, `runSql`, `wp-cli`, `writeFile(s)`, archive imports and URLs before anything runs (`references/blueprint-authoring.md`, trust review). Do not execute them.
2. Validate against the schema used by the installed generation; parsing JSON is not validation.
3. Check step order, resource types, pinning and CORS-reachable URLs; record resolved versions of aliases.
4. For CLI work, read the installed `--help`, then check flags, mounts and persistence mode (`references/cli-and-local-environments.md`). For links and embeds, check query parameters, bundle layout, origins (`references/embedding-and-query-api.md`).
5. Confirm the reproduction has a seed, a named trigger and an expected/observed pair; otherwise it is a setup, not a reproduction.
6. Describe the fresh-instance, missing-resource and second-run checks. Report runtime behavior as unexecuted unless it was run.

Read `references/playground-development-workbook.md` for the decision table, symptoms, false positives, severity and acceptance checks.
Optional disposable setup material: `references/playground-isolation-fixture.json` (not a defect reproduction; limits in the workbook).

## Implementation workflow

State the reproduction target and the smallest Blueprint that exposes it. Prefer pinned `git:directory`/`bundled` resources, install before activate, seed only what the trigger needs, and keep secrets out. Validate, then boot in a disposable instance with the pinned CLI, perform the trigger, repeat on a fresh instance, and record versions and exit codes. Do not claim production compatibility from a Playground run.

## Search Patterns for Quick Detection

Read-only leads; they do not run anything. Matches are candidates; no match proves nothing. Exit 0 = match, 1 = none, 2 = error.

```sh
# Blueprint identity and versions
rg -n -g '*.json' -g '!**/{vendor,node_modules,build,dist}/**' -e 'blueprint-schema|preferredVersions|landingPage|"steps"|"features"' .
# external resources
rg -n -g '*.json' -g '!**/{vendor,node_modules,build,dist}/**' -e '"resource"|"url"|git:directory|wordpress.org/(plugins|themes)|importWxr|importWordPressFiles' .
# executable steps
rg -n -g '*.json' -g '!**/{vendor,node_modules,build,dist}/**' -e 'runPHP|runPHPWithOptions|runSql|wp-cli|writeFile|defineWpConfigConsts' .
# CLI and CI ownership
rg -n -g '*.{json,js,ts,yml,yaml,sh,ps1,md}' -g '!**/{vendor,node_modules,build,dist}/**' -e '@wp-playground|wp-now|run-blueprint|build-snapshot|follow-symlinks|blueprint-may-read-adjacent-files|--mount' .
# embeds and links
rg -n -g '*.{html,js,jsx,ts,tsx,md}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'playground\.wordpress\.net|blueprint-url|startPlaygroundWeb|postMessage|event\.origin|<iframe' .
# secrets and live data in shareable artifacts
rg -n -i -g '*.{json,md}' -g '!**/{vendor,node_modules,build,dist}/**' -e 'password|secret|api[_-]?key|token|BEGIN (RSA|PRIVATE)' .
```

Reading the leads: `runPHP` is a candidate only when its code or source is attacker-controlled or unreviewed; `login` in a disposable fixture is intended; `latest` is acceptable in an exploratory demo; a secrets hit needs the value inspected and redacted in the report.

## Output Format

Lead with the result and reviewed scope (files read, nothing executed). Confirmed concern: `file:line`, actor, trigger, reachable path, impact, confidence, minimal fix, regression check. Keep candidates and "not established" items separate. Implementation: Blueprint/command, resolved versions, CLI and Node versions, exit codes, fresh-instance result, what remains unexecuted. A successful Playground boot does not prove MySQL, hosting, cache or production behavior.
