# Playground development workbook

Apply [the engineering contract](engineering-contract.md) first. Contents: evidence, decision table, symptom table, looks-fine cases, severity, acceptance checks, reproduction template, optional fixture, sources.

## Evidence to collect

The behavior to reproduce (defect, demo, onboarding), the artifact under test (plugin/theme zip, repo ref, WordPress.org slug) and its identity (version, commit or digest), the Blueprint file or link and its schema generation, resolved WordPress and PHP versions, CLI package and version, Node version, mounts, and whether the runtime may be booted at all (authorization).

## Decision table

| Decision | Rule |
| --- | --- |
| Browser, CLI or real environment | Browser: shareable links and demos. CLI: local mounts, CI, debugging (`--xdebug`). Real MySQL/host stack (wp-env, Docker): anything involving database engine, cache, cron, permissions or server config. |
| Resource kind | `git:directory` with pinned ref for source; `bundled` for self-contained bundles; `url` only for stable, CORS-enabled direct downloads. |
| Version policy | Exploratory demo: aliases acceptable. Compatibility claim or regression fixture: pin and record resolved versions. |
| Shared vs local | Anything needing adjacent files or mounts is local-only; say so, or bundle the resources. |
| Executable steps | Treat `runPHP`, `runSql`, `wp-cli`, `writeFile` and imported archives as code; review before boot. |

## Symptom table

| Symptom | Evidence | Next |
| --- | --- | --- |
| Blueprint will not boot | schema validation, `--verbosity=debug`, first failing step | [blueprint-authoring.md](blueprint-authoring.md) |
| Plugin install fails | resource type, HTTP status/content type, CORS, networking flag | [blueprint-authoring.md](blueprint-authoring.md) |
| CLI flag unknown | `--help` of the installed version | [cli-and-local-environments.md](cli-and-local-environments.md) |
| State differs between runs | `start` persistence vs `server` temp dir, aliases | [cli-and-local-environments.md](cli-and-local-environments.md) |
| Embed shows wrong state or blocked | landing page, query params, origin handling | [embedding-and-query-api.md](embedding-and-query-api.md) |
| Passes in Playground, fails in production | SQLite vs MySQL, cache, cron, hosting | use a real-environment check |

## Looks wrong but is fine

- An exploratory Blueprint using `latest` (it is not a compatibility fixture, which is a different claim).
- `login` step in a disposable demo (not a credential leak; a real password literal would be).
- `runPHP` that only seeds options or content in a reviewed Blueprint.
- A core-only Playground boot used as a deliberate separate demo.
- Mounting a directory read-write in a throwaway checkout.
- An `iframe` embed without a `message` listener.

Insufficient evidence outcome: when the artifact, resolved versions or authorization to boot are missing, report the reproduction as "not established" with the exact input needed. Never claim a reproduction from source reading.

## Severity

CRITICAL: a Blueprint or bundle that exfiltrates data or runs hostile code when opened, or credentials/production exports committed in a shared artifact. WARNING: unpinned artifacts in a claimed reproducible fixture, missing prerequisites that make the reproduction fail, `--follow-symlinks` or adjacent-file consent on untrusted input, unvalidated message origins. INFO: moving aliases in a demo, absent landing page.

## Acceptance checks

1. Schema-validate the Blueprint against `https://playground.wordpress.net/blueprint-schema.json` (for example with `npx ajv-cli` or an editor with `$schema`) and report the result separately from boot.
2. Boot on a fresh instance (new temp dir or `start --reset`) in a disposable environment; record CLI version, Node version, resolved WP/PHP, command and exit status.
3. Perform the named trigger action and record observed vs expected; add the assertion to a Playwright test when it will be kept.
4. Fail-path: break one resource URL and confirm a clear failure; run once with `networking` disabled if the artifact must work offline.
5. Repeat the run on a second fresh instance to catch ordering and persistence dependence.
6. For compatibility claims: repeat on a real MySQL/MariaDB stack.

A pass does not prove production compatibility, performance, security of the plugin under test, or behavior with a different resolved version.

## Reproduction template

```text
Artifact: <name, version/commit, digest>   Runtime: WP <resolved>, PHP <resolved>, CLI <version>, Node <version>
Launch: <Blueprint file / link / command>   Seed: <content and options>
Trigger: <named user action>   Expected: <...>   Observed: <...>
Persists after reset: <yes/no>   Unexecuted: <list>
```

## Optional fixture

[playground-isolation-fixture.json](playground-isolation-fixture.json) sets a site title and logs in on a disposable instance. It is setup material, not a defect reproduction or runtime test; its `preferredVersions` lines are examples to replace and record.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/playground/blueprints/
- https://developer.wordpress.org/playground/developers/local-development/wp-playground-cli/
