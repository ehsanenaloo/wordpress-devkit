# Editor behavior, data and the iframe editor

Contents: iframe timeline, fixes, data access, effects, controls, tests, sources.

## Iframe editor timeline (verified 2026-10-08)

- apiVersion 3 (WordPress 6.3+) means the block must work inside an iframe with its own `document` and `window`; editor scripts still run in the parent page.
- WordPress 6.9: console warning for blocks registered with apiVersion 2 or lower; published `block.json` schema only allows 3.
- WordPress 7.0: the iframe decision looks at blocks present in the post content; one v1/v2 block makes the editor fall back to non-iframe mode.
- Gutenberg 23.6 and WordPress 7.1: the post editor always uses the iframe, regardless of apiVersion. Treat an apiVersion 2 block that touches globals as a release-blocking defect on 7.1 targets, and as a compatibility warning below.

## Typical breakages and fixes

| Symptom in iframe | Cause | Fix |
| --- | --- | --- |
| Listener never fires / `document.querySelector` returns null | Global `document`/`window` refer to the parent | `useRefEffect( ( el ) => { const win = el.ownerDocument.defaultView; ... return cleanup; }, [] )` |
| Editor styles missing | Styles enqueued only for the admin page | Declare in `block.json` `editorStyle`/`style`, or `add_editor_style`/`enqueue_block_assets` |
| Third-party library (jQuery plugin, slider) fails | Library bound to parent globals | Pass the iframe element/ownerDocument; patch or request upstream support |
| Viewport units/media queries differ from frontend | Previously evaluated against admin window | Verify; the iframe makes them match the frontend |

Prefer `useRefEffect` over `useEffect` plus `ref.current`, because it re-runs when the ref changes.

## Editor data

- Read with `useSelect( ( select ) => select( coreStore ).getEntityRecord(...), [ deps ] )`; list the real dependencies. Prefer `useEntityRecords`/`useEntityProp` over hand-written `apiFetch` for entities.
- `useSelect` mapping functions must be pure; never dispatch inside them. Writes belong in event handlers or intentional effects with guarded conditions; an effect that calls `setAttributes` on every render loops and dirties the post.
- Handle all of: loading (`hasFinishedResolution`), error, empty, and permission denial (`canUser`). A control that assumes data crashes the whole block ("This block has encountered an error and cannot be previewed").
- Block `context` values are consumed with `usesContext`; check the actual ancestor provides them (`providesContext` maps context key to attribute name).

## Controls

- Put persistent options in `InspectorControls`, formatting in `BlockControls`; wrapper from `useBlockProps()` (mandatory in apiVersion 2+), nested content from `useInnerBlocksProps( blockProps, { allowedBlocks, template, templateLock } )`.
- Localize every visible string with `__()` and the block text domain; set `textdomain` in `block.json` and load JS translations (`wp_set_script_translations` or automatic via metadata).
- Use `supports` (color, spacing, typography, align) instead of bespoke controls when it expresses the need; supports output also reaches the frontend wrapper via `get_block_wrapper_attributes`.

## Tests

- Unit: `parse`/`serialize` with `@wordpress/blocks` for fixtures.
- E2E: Playwright (`wp-scripts test-e2e`) with the iframe on: insert, edit, save, reload, assert no console errors and no "invalid content". Run once against the lowest supported WordPress and once against current.
- Passing editor tests do not prove frontend behavior; check the rendered page separately.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-api-versions/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-api-versions/block-migration-for-iframe-editor-compatibility/
- https://make.wordpress.org/core/2026/02/24/iframed-editor-changes-in-wordpress-7-0/ (fetched 2026-10-08: the 7.0 check uses blocks inserted in the post; the iframe is not enforced in 7.0)
- https://make.wordpress.org/core/2025/11/12/preparing-the-post-editor-for-full-iframe-integration/ (search result only, not fetched)

The 7.1 / Gutenberg 23.6 statement comes from the handbook migration page as served on 2026-10-08; secondary sources disagree on dates, so confirm against the current handbook.
