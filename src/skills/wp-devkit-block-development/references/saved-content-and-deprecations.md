# Saved content, validation and deprecations

Contents: how validation works, attribute storage, deprecation recipe, migrate with inner blocks, fixtures, rename/transform, sources.

## How validation works

On load the editor parses each comment-delimited block, regenerates markup with the current `save()` from the parsed attributes, and compares it with the stored HTML. A mismatch marks the block invalid ("This block contains unexpected or invalid content"). Causes, in order of likelihood:

1. `save()` markup changed (wrapper element, class, attribute order, whitespace-significant text) without a deprecation.
2. An attribute's `source`/`selector`/`type` changed so parsing yields a different value.
3. `save()` depends on outside data (store selectors, `Date`, random ids). `save()` must be pure.
4. Hand-edited or filter-modified HTML (`blocks.getSaveContent.extraProps`; KSES stripping attributes for users without `unfiltered_html` is a plausible cause that this review did not confirm against a primary source, so treat it as a candidate).

Diagnose with the console message that prints expected vs actual markup. Do not use "Attempt Block Recovery" on production content to silence the warning; recovery rewrites saved content.

## Attribute storage

- Attributes with no `source` live in the block comment JSON; attributes with `source` (`html`, `text`, `attribute`, `query`) are read back from markup using `selector`.
- `type` must match what the control writes. A `RangeControl` returning a string into `"type": "number"` validates in editor state, then fails after save and reload. Convert in `onChange`.
- Changing `default` does not alter stored content, but changes what a saved block with no attribute renders and can invalidate static output, because defaults are omitted from the comment JSON.
- Do not store derived or secret values in attributes; they are public in `post_content`.

## Deprecation recipe

Add a deprecation when previously saved content no longer validates or must be migrated:

```js
// deprecated.js: keep a frozen copy of the old definition. Do not import live helpers.
const v1 = {
    attributes: { text: { type: 'string', source: 'html', selector: 'p' } },
    supports: { className: false },
    save( { attributes } ) {
        return <p>{ attributes.text }</p>;
    },
    migrate( { text } ) {
        return { content: text };
    },
};
export default [ v1 ]; // newest first
```

Rules confirmed in the handbook:

- Each entry must carry its own `attributes`, `supports` and `save`; nothing is inherited from the current definition.
- Entries are tried in array order (newest first); the first whose `save()` validates the stored content wins and its `migrate` runs. Deprecations do not chain, so a change that affects every older form needs the migration in each relevant entry.
- `isEligible( attributes, innerBlocks, { blockNode, block } )` forces migration for content that is still valid; it is not consulted when every earlier `save()` was invalid for that content.
- `migrate` may return `[ attributes, innerBlocks ]` to restructure children (use `createBlock`).
- Helpers imported into an old `save()` can change later and silently break it; snapshot them in the file.

## Dynamic blocks and null save

`save: () => null` is correct for a dynamic leaf block. For a dynamic container whose children must persist, `save` returns `<InnerBlocks.Content />` (inside `useBlockProps.save()` wrapper if the renderer expects one). Changing from `null` to a wrapper, or the reverse, invalidates existing content for static output but not for a pure-PHP leaf; decide per block and add a deprecation when stored markup changes. A dynamic block with `save: () => null` that previously stored nothing is not invalidated by moving rendering to PHP.

## Fixtures and regression

Keep one fixture per supported historical form, as raw `post_content`:

```
<!-- wp:acme/notice {"message":"Hi"} -->
<p class="wp-block-acme-notice">Hi</p>
<!-- /wp:acme/notice -->
```

Regression check (Playwright with the WordPress e2e utils, or a Jest/Vitest test with `@wordpress/blocks` `parse`/`serialize`): load each fixture, assert `isValid === true` for every block in `parse()` output, assert migrated attributes, assert `serialize(parse(x))` equals the current expected markup, and assert no console warnings. Include a fixture with nested children.

## Renames, transforms, variations

- Rename = new block + `transforms.to`/`from` on both sides; the old name must keep registering (even hidden with `supports.inserter: false`) or stored posts lose the block.
- A variation is a preset of attributes/inner blocks of the same block, not a migration. A transform changes representation and must preserve content.

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-deprecation/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-edit-save/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-registration/
- Gutenberg `packages/blocks/src/api/serializer.tsx`: `getCommentAttributes()` omits attributes that equal their `default`, attributes with a `source`, and `role: local` attributes.

Facts to verify in the deprecation page: newest-first order, first valid entry wins, no chaining, `isEligible` not called when all earlier saves were invalid, `migrate` may return a tuple, each entry carries its own `attributes`/`supports`/`save`.
