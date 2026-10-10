# Blueprint authoring and review

Contents: structure, versions, resources, steps, ordering, trust review, a worked repro, failure table, sources.

## Structure

A Blueprint is JSON that configures an instance. Validate against `https://playground.wordpress.net/blueprint-schema.json`. JSON that parses is not a valid Blueprint; validate and then boot in a disposable instance.

Top-level (v1) properties: `$schema`, `landingPage`, `preferredVersions` (`php`, `wp`), `features` (`networking`, default true), `extraLibraries` (`wp-cli`), `steps`, and the shorthands `plugins`, `login`, `siteOptions`, `constants` that expand before `steps`.

Versions: `preferredVersions.php` accepts a supported PHP minor version, `latest` and `next` (web only); no patch versions. Look up the supported PHP range online. `preferredVersions.wp` accepts recent majors plus `latest`, `beta`, `nightly`/`trunk`. The Blueprint data-format page and the Query API page can disagree on how many recent majors are listed. Pick versions from the page that matches the surface you use, and confirm by booting. Aliases (`latest`, `beta`, `nightly`) move: record the resolved WordPress and PHP versions in the report. A Blueprints "v2" generation exists (the published schema declares it and the client source in `wordpress-playground` has a `BlueprintsV2Handler` and a `blueprints-runner` query parameter); its stability is not guaranteed, so do not author v2 unless the user asks and the target runner supports it.

## Resources

| Resource | Fields | Notes |
| --- | --- | --- |
| `wordpress.org/plugins` / `themes` | `slug`, optional `version` | Pin `version` for repeatability |
| `url` | `url` | Server needs CORS headers; must return the file itself (no HTML/login/redirect page); must be a real ZIP for installs; short-lived CI or tunnel URLs expire |
| `git:directory` | `url`, `path` (subdirectory), `ref` (default HEAD), `refType` (`branch`, `tag`, `commit`) | Preferred over `url` for GitHub source; pin `ref` to a commit for repeatability; the resources page says `refType` is required when `ref` is a branch or tag name |
| `bundled` | `path` | Relative to the Blueprint bundle (zip or directory with `blueprint.json` at the root or one top-level folder) |
| `literal` | `name`, `contents` | Inline files |
| `vfs` | `path` | File already in the Playground filesystem |

## Steps (checked list)

`activatePlugin`, `activateTheme`, `cp`, `defineSiteUrl`, `defineWpConfigConsts`, `enableMultisite`, `importThemeStarterContent`, `importWordPressFiles`, `importWxr`, `installPlugin` (`pluginData`, `ifAlreadyInstalled`, `options`), `installTheme` (`themeData`), `login`, `mkdir`, `mv`, `resetData`, `rm`, `rmdir`, `runPHP`, `runPHPWithOptions`, `runSql`, `setSiteLanguage`, `setSiteOptions`, `unzip`, `updateUserMeta`, `wp-cli`, `writeFile`, `writeFiles`. Deprecated: `pluginZipFile` and `themeZipFile` (use `pluginData` and `themeData`); the `importer` option of `importWxr`.

Ordering rules: install before activate; `activatePlugin` and `activateTheme` do nothing useful if the artifact is absent; `runPHP` needs `require '/wordpress/wp-load.php';` before WordPress functions; `runSql` assumes the SQLite integration plugin (Playground runtime), so SQL tested here does not prove MySQL behavior; installs from wordpress.org need `features.networking` true (the data-format page: disabling networking makes WordPress HTTP functions fail); `setSiteLanguage` downloads translations, so assume it needs networking too.

## Trust review (read-only)

Before booting any third-party Blueprint, read every `runPHP`, `runPHPWithOptions`, `runSql`, `wp-cli`, `writeFile(s)` and every external resource URL. Flag: exfiltration (`wp_remote_post` to unknown hosts), credential or token literals, `importWordPressFiles` of unknown archives, `defineWpConfigConsts` that disable security, URLs that are not pinned or are on short-lived hosts. Do not execute during review; execute only in a disposable environment with the user's authorization. Redact secrets in any shared Blueprint.

## Minimal reproduction example

```json
{
  "$schema": "https://playground.wordpress.net/blueprint-schema.json",
  "landingPage": "/wp-admin/admin.php?page=acme-import",
  "preferredVersions": { "php": "8.3", "wp": "6.9" },
  "steps": [
    { "step": "installPlugin",
      "pluginData": { "resource": "bundled", "path": "/acme-import.zip" },
      "options": { "activate": true } },
    { "step": "importWxr",
      "file": { "resource": "bundled", "path": "/fixtures/sample.xml" } },
    { "step": "login" }
  ]
}
```

(`options.activate` is the documented placement: the data-format page says `activate` belongs inside `options`, not inside `pluginData` or on the step itself.) The bundle is a zip with `blueprint.json` at its root. The trigger is the landing page action; the report states expected and observed behavior.

## Failure table

| Symptom | Check | Fix |
| --- | --- | --- |
| Boots, steps fail at one index | CLI debug log (`--verbosity=debug`), first failing step | Reorder or fix prerequisite; do not swallow errors |
| Install step downloads tiny file | `url` resource returned HTML | Fix hosting, use `git:directory` or `bundled` |
| Works locally, fails on shared link | adjacent-file reads, `file:` paths | Bundle resources into a zip |
| Different result next week | moving aliases/unpinned URLs | Pin versions, refs, digests |
| `runSql` fails | MySQL-only syntax | Use `runPHP` + `$wpdb` or WP-CLI steps |

## Sources

Research date: 2026-10-08.

- https://developer.wordpress.org/playground/blueprints/steps/
- https://developer.wordpress.org/playground/blueprints/data-format/
- https://developer.wordpress.org/playground/blueprints/resources/
- https://developer.wordpress.org/playground/blueprints/bundles/
- https://playground.wordpress.net/blueprint-schema.json
- https://make.wordpress.org/playground/
