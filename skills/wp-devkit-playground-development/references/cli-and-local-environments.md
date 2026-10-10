# Playground CLI and local environments

Contents: commands, flags, persistence, mounts and trust, CI use, limits, sources. Package: `@wp-playground/cli` (Node 20.18 or newer per the docs checked 2026-10-08). Use the installed `--help` output as the final authority; flags change between releases and the legacy `wp-now` package is superseded.

## Commands

| Command | Use |
| --- | --- |
| `start` | Auto-detects project type, persists the site per working directory, opens a browser |
| `server` | Manual control; suited to CI and custom setups |
| `run-blueprint` | Run a Blueprint without a web server |
| `build-snapshot` | Build a ZIP snapshot of a site from a Blueprint |

```sh
npx @wp-playground/cli@<pinned> --help
npx @wp-playground/cli@<pinned> server --auto-mount --blueprint=./blueprint.json --php=8.3 --wp=6.9 --port=9400
```

Pin the package version in repeatable work (`@latest` is for exploration).

## Flags worth knowing (server unless noted)

`--php` (8.0 to 8.5 and 7.4; default 8.3), `--wp` (default latest), `--port` (default 9400), `--blueprint` (path, zip, directory or http(s) URL), `--auto-mount[=path]`, `--mount=host:vfs`, `--mount-before-install=host:vfs`, `--mount-dir "<host>" "<vfs>"` (Windows-friendly), `--login`, `--wordpress-install-mode` (`download-and-install`, `install-from-existing-files`, `install-from-existing-files-if-needed`, `do-not-attempt-installing`), `--skip-sqlite-setup`, `--verbosity=quiet|normal|debug`, `--debug`, `--phpmyadmin`, `--xdebug`, `--workers`. `start` only: `--reset`, `--skip-browser`, `--no-auto-mount`, `--path`. The docs list no `--skip-wordpress-setup` flag.

## Trust-sensitive flags

- `--blueprint-may-read-adjacent-files`: consent for bundled resources to read files beside the Blueprint. Grant only for a Blueprint you have reviewed.
- `--follow-symlinks`: exposes files outside the mounted directories. Avoid on shared or untrusted trees.
- Mounts are read-write views of host directories. A plugin under test can modify them; mount a copy when testing destructive behavior. On Windows, prefer `--mount-dir` quoting and check for path separators in Blueprint `vfs` paths (they are POSIX paths inside Playground).

## Persistence

- `start`: site files and database persist under `~/.wordpress-playground/sites/<path-hash>/`, keyed by the working directory. `--reset` deletes it. The store is keyed by a hash of the project path (default: the working directory; `--path` selects another project), so a different path means a different site.
- `server`: files and SQLite DB live in a temp directory; auto-mounting a plugin or theme loses the DB on stop. Mounting `wp-content` keeps the database at `wp-content/database/`. Reset is manual deletion.
- Consequence: a repro that passes on a reused `start` site may fail on a fresh one. Verify on a fresh instance (`--reset`, new temp dir).

## Using it in CI (pattern)

```sh
npx @wp-playground/cli@<pinned> server --blueprint=./ci/blueprint.json --port=9400 &
npx wait-on http://127.0.0.1:9400 && npx playwright test
```

Capture exit codes for both. The runtime is PHP.wasm with SQLite: a green run does not prove MySQL/MariaDB, object cache, real cron, filesystem permissions, hosting limits or Apache/nginx rewrite behavior. Keep a real-environment job (wp-env, Docker) for those.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/playground/developers/local-development/wp-playground-cli/

Confirmed 2026-10-08: Node.js 20.18+, the four commands, `server` defaults (port 9400, PHP 8.3 with choices 7.4 to 8.5, `download-and-install`, verbosity `normal`), the `start` flags (`--reset`, `--skip-browser`, `--no-auto-mount`, `--path`), persistence locations for `start` and `server`, `@wp-now/wp-now` deprecated in favor of `start`, and `--follow-symlinks` flagged as a security risk. Not documented on the page and therefore unverified: the CI `wait-on` snippet and `run-blueprint` flags (the snippet is a generic pattern); the "SQLite not MySQL" caveat is inferred from the `runSql` note and the `--skip-sqlite-setup` flag.
