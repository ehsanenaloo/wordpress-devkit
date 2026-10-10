---
name: wp-devkit-block-development
description: "Build, debug or review Gutenberg blocks: block.json registration, invalid-content errors and deprecations, dynamic render.php, InnerBlocks, Interactivity API, Block Bindings, iframe editor. Not for theme.json/templates (theme skill) or generic plugin code."
---

# Block state, storage and rendering

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations, builds that rewrite files, or untrusted runtime execution. Implementation applies only when the request authorizes changes.

## Inputs

Block name, oldest and newest supported WordPress, `block.json`, build command, emitted `build/` assets, one saved-content fixture per historical form, and the failing action (insert, save, reopen, frontend, second instance). Inspect project evidence before asking; ask only what changes the decision.

## Boundaries

- Theme templates, `theme.json`, patterns files: hand off to `wp-devkit-theme-development`.
- Admin screens, settings pages, REST routes, plugin lifecycle: `wp-devkit-plugin-development`, `wp-devkit-rest-api-development`, `wp-devkit-admin-ui-development`.
- Escaping or authorization questions beyond the block renderer: `wp-devkit-security-review`.
- Editor/visual polish decisions: `wp-devkit-ui-design`.

## Code Review Workflow

1. Follow metadata from source to build output to server and client registration (`references/metadata-registration-and-build.md`). Check asset field types, `file:` paths, `*.asset.php`, and the apiVersion against the supported range.
2. Trace each attribute from control to stored form (comment JSON or markup `source`) to render. Decide static vs dynamic from freshness and storage needs.
3. Compare each historical fixture with the current `save` and attribute definitions (`references/saved-content-and-deprecations.md`). Check nested blocks.
4. For dynamic output, trace attributes and context to the escaped sink (`references/dynamic-rendering-and-security.md`); confirm wrapper attributes and empty states.
5. Check editor behavior under the iframe, data loading, effects and errors (`references/editor-and-iframe-compat.md`).
6. For interactive blocks, check state vs context, server initialization and event handling (`references/interactivity-api.md`). For bindings or PHP-only blocks, read `references/bindings-and-php-only-blocks.md`.
7. Report the failing boundary with the old/new content checks needed. Do not rebuild assets or rewrite saved content during review.

Read `references/block-development-workbook.md` for the decision table, symptom table, false positives, severity guidance and acceptance checks.

## Implementation workflow

State the expected behavior and the smallest affected boundary. Prefer metadata and supports over bespoke code. If saved markup changes, add a frozen deprecation and a fixture before editing `save`. Implement, then run the acceptance checks in the workbook against the lowest and highest supported WordPress. Report any unavailable check as unexecuted. Publishing or deploying needs its own scope.

## Search Patterns for Quick Detection

Read-only leads from the first-party root; narrow `.` where possible. Matches are candidates, not findings; no match proves nothing. Exit 0 = match, 1 = none, 2 = error (record separately).

```sh
# registration and metadata
rg -n -g '*.{php,json,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage}/**' -e 'apiVersion|register_block_type|registerBlockType|viewScriptModule|blocks-manifest|autoRegister' .
# wrappers, inner blocks, renderers
rg -n -g '*.{php,json,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage}/**' -e 'useBlockProps|InnerBlocks|useInnerBlocksProps|render_callback|get_block_wrapper_attributes|save\s*[:(]' .
# deprecations, transforms, attribute sources
rg -n -g '*.{json,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage}/**' -e 'deprecated|isEligible|migrate|transforms|"source"|"selector"' .
# editor data and global access
rg -n -g '*.{js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage}/**' -e 'useSelect|useDispatch|apiFetch|\bdocument\.|\bwindow\.|useEffect' .
# interactivity and bindings
rg -n -g '*.{php,html,json,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage}/**' -e 'data-wp-|@wordpress/interactivity|wp_interactivity_|withSyncEvent|asDangerousHTML|register_block_bindings_source|metadata.bindings' .
# output context
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage}/**' -e 'echo\s+\$|esc_(html|attr|url)|wp_kses|dangerouslySetInnerHTML' .
```

How to read the leads: a `document.`/`window.` hit in editor code matters only inside `edit`/effects; an `echo $` hit matters only if the value is attacker-influenced and unescaped for its context (`$content` from core is not); `data-wp-html` matters only with a non-literal source.

## Output Format

Lead with the result and reviewed scope. Confirmed concern: `file:line`, actor, trigger, reachable path, impact, confidence, minimal fix, regression check. List candidates and missing evidence separately; use "not established" when the fixture, build output or version is unavailable. Implementation: changed boundaries, deprecations added, commands with exit codes, fixtures, unexecuted checks, residual risk. A passing build or editor test does not prove old-content safety, frontend rendering or cross-version support.
