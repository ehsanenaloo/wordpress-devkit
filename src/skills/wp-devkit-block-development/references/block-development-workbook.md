# Block development workbook

Apply [the engineering contract](engineering-contract.md) before classifying anything. Contents: evidence to collect, decision table, symptom table, false positives, acceptance checks, report templates, sources.

## Evidence to collect

Block name(s) and namespace, oldest and newest supported WordPress (and Gutenberg plugin if used), `block.json`, build command and lockfile, emitted `build/` tree including `*.asset.php` and `blocks-manifest.php`, one saved-content fixture per historical form, and the exact failing action (insert, save, reopen, frontend view, second instance).

Keep an expected/observed pair for the journey. Locate the owning boundary (metadata, `save`, PHP renderer, store, directive) before proposing a change. A grep hit is a lead, not an observation.

## Decision table

| Decision | Rule |
| --- | --- |
| Static vs dynamic | Static when output depends only on attributes and must survive plugin removal; dynamic when it depends on live data, user, time or other posts. Dynamic containers still serialize children. |
| Needs deprecation | Yes if the serialized form of already-saved content stops validating or must be migrated. No for PHP-only changes to a dynamic leaf block. |
| Attribute source | Comment JSON for structured/non-visible values; `source` + `selector` for values that live in markup. |
| Registration | Manifest (6.8+) for many blocks; `register_block_type` per folder otherwise; never register one name two ways. |
| apiVersion | 3 for any new or touched block; test with the iframe. Do not raise it without running the editor. |
| Script module | Required for Interactivity API view code (`viewScriptModule`); classic `viewScript` cannot import modules. |
| State location | Per-instance in context, shared data in state, static in config. |

## Symptom table

| Symptom | Evidence | Likely owner | Reference |
| --- | --- | --- | --- |
| Not in inserter | registry check, console, build tree | metadata/registration | [metadata-registration-and-build.md](metadata-registration-and-build.md) |
| Invalid content after update | console expected vs actual | `save`/deprecations | [saved-content-and-deprecations.md](saved-content-and-deprecations.md) |
| Children lost on frontend | `post_content` raw, `save` | container serialization | [saved-content-and-deprecations.md](saved-content-and-deprecations.md) |
| Wrong output / XSS candidate | `render.php` data flow | renderer | [dynamic-rendering-and-security.md](dynamic-rendering-and-security.md) |
| Works in classic, broken in editor | globals, styles | iframe compat | [editor-and-iframe-compat.md](editor-and-iframe-compat.md) |
| Second instance broken | state vs context | interactivity | [interactivity-api.md](interactivity-api.md) |
| Bound value empty | source registration, REST exposure | bindings | [bindings-and-php-only-blocks.md](bindings-and-php-only-blocks.md) |

## Looks wrong but is fine

- `save: () => null` for a dynamic leaf.
- `echo $content` in a renderer when `$content` is core's rendered inner blocks.
- Missing optional metadata (`example`, `keywords`, `description`).
- `apiVersion` 2 in an older, working block on a pre-7.1 target (compatibility INFO, not a defect, unless it touches globals).
- Attributes stored in comment JSON that include markup, when output is escaped for its context.
- A variation or transform that duplicates attributes of the parent block.
- Hashed filenames or `build/` directory committed intentionally for distribution.

Insufficient evidence outcome: when the fixture, build output or runtime version needed to reproduce is missing, report "not established" with the exact artifact needed; do not infer a defect from source alone.

## Severity guidance

CRITICAL: attacker-reachable script injection through a rendered attribute or binding, or content loss on update for already-published posts. WARNING: validation failure on supported old content, broken second instance, unescaped output of non-attacker data, missing capability check in a binding source. INFO: apiVersion lag with no failing behavior, stylistic metadata gaps.

## Acceptance checks (implementation)

1. `npx wp-scripts build` (or the project build) exits 0 and the build tree contains the expected `*.asset.php`/manifest.
2. `npx wp-scripts lint-js` and `lint-style`, plus `phpcs`/`phpstan` for PHP, as the project configures them.
3. Fixture test: every historical form parses with `isValid` true and serializes to the expected markup.
4. Playwright: insert, edit, save, reload, view frontend; no console errors; two instances for interactive blocks; keyboard operation.
5. Run once on the lowest and once on the highest supported WordPress.

A passing result does not prove: behavior with other plugins' block filters, caching layers, KSES for lower-privileged authors, multisite, or untested historical forms.

## Report formats

Review finding: `file:line` | actor | trigger | reachable path | impact | confidence | minimal fix | regression check. Keep candidates separate.

Change report: affected boundaries, deprecation added (yes/no and why), commands with exit codes, fixtures added, unexecuted checks, residual risk.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-metadata/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-deprecation/
- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-context/
