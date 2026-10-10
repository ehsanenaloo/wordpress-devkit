# Interactivity API

Contents: wiring, state vs context, server rendering, actions and events, client navigation, security, failure table, sources. Requires WordPress 6.5+.

## Wiring

```json
{ "supports": { "interactivity": true }, "viewScriptModule": "file:./view.js", "render": "file:./render.php" }
```

```php
<?php
wp_interactivity_state( 'acme/counter', array( 'step' => 1 ) );
$context = array( 'count' => (int) ( $attributes['start'] ?? 0 ) );
?>
<div <?php echo get_block_wrapper_attributes(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
     data-wp-interactive="acme/counter"
     <?php echo wp_interactivity_data_wp_context( $context ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped by core. ?>>
    <button type="button" data-wp-on--click="actions.increment">+</button>
    <output data-wp-text="context.count"><?php echo (int) $context['count']; ?></output>
</div>
```

```js
import { store, getContext } from '@wordpress/interactivity';

store( 'acme/counter', {
    state: {
        get doubled() {
            return getContext().count * 2;
        },
    },
    actions: {
        increment() {
            getContext().count += 1;
        },
    },
} );
```

Directives processed on the server for blocks happen automatically; classic templates must pass markup through `wp_interactivity_process_directives()` once, at the outermost template.

## State vs context (most common bug source)

- State (`wp_interactivity_state`, `store().state`) is global to the namespace: every instance shares it. Per-instance data (open/closed, count, selected id) belongs in `data-wp-context`. Symptom of misuse: "first instance works, second changes both".
- Context is inherited and merged by nesting; deeper wins. Read with `getContext()`.
- Derived values are getters on `state`; they cannot be assigned. Do not duplicate them as stored properties.
- `getServerState()`/`getServerContext()` return snapshots of the server data; the server context is updated on client navigation and, per the API reference, cannot be used directly in directives but can be read in callbacks. Mutating a snapshot does not change the live store.
- Config (`wp_interactivity_config`, `getConfig()`) is non-reactive: URLs, nonces, flags, translated strings. Reactive UI data does not belong there.

## Server rendering and hydration

- Initialize everything the first paint needs on the server. A getter defined only in JS leaves the server HTML in the wrong state until hydration (flash and layout shift). Give a PHP value, or a closure that reads `wp_interactivity_get_context()`.
- Do not re-declare in JS state the server already provided.
- Strings produced in JS actions are not translated; pass translated strings through state/config.
- `data-wp-each` templates: set `data-wp-each-key` for object lists; `data-wp-each-child` is added by the server.

## Actions and events

- Event directives run async by default. Handlers that call `event.preventDefault()`, `stopPropagation()` or read `event.currentTarget` must be wrapped in `withSyncEvent()` (required since WordPress 6.8; without it a deprecation warning appears).
- Async actions must be generators (`function* load() { const r = yield fetch(...); }`). With `async/await`, scope is lost across the await and `getContext()` can return the wrong context. Use `withScope()` for callbacks created outside the runtime (timers, third-party listeners). Use `splitTask()` inside generators to break up long tasks.
- Always handle a failed request: set an error flag in context and expose it with `aria-live` text; do not leave a spinner.
- Negation `!` works on state/context/getters, not on functions; define a getter for computed negation.

## Client navigation

Router regions (`data-wp-router-region`, `supports.interactivity.clientNavigation`) swap content without a reload. The Interactivity API reference page does not document these (the block-supports page documents the `clientNavigation` sub-property only as a compatibility flag); check the installed `@wordpress/interactivity-router` docs before using, and test that listeners and `data-wp-init` cleanups survive repeated navigation.

## Security

- `data-wp-html` only accepts values wrapped in `asDangerousHTML()`; it does not sanitize and nested directives are not processed. Feed it only trusted, server-sanitized `state`, never `context` or request data.
- `wp_interactivity_data_wp_context()` and `wp_interactivity_state()` serialize and escape values; hand-built `data-wp-context='{...}'` with interpolated strings is an injection candidate (attribute and JSON breakout).
- Nonces in config authorize requests only together with a capability check on the endpoint.

## Failure table

| Symptom | Evidence | Fix |
| --- | --- | --- |
| Nothing reacts | `data-wp-interactive` missing/namespace typo; module not enqueued (view source); `supports.interactivity` absent | Fix namespace; ensure build emitted module; confirm `viewScriptModule` |
| Second instance shares state | Value lives in `state` | Move to `data-wp-context` |
| `Cannot read properties of undefined` in action after `await` | async/await with `getContext()` | Use generator |
| Deprecation warning on click handler | `preventDefault` without wrapper | `withSyncEvent` |
| Flash of wrong content | Client-only getter | Initialize in PHP |
| Works on first load, breaks after navigation | Listeners attached outside runtime | Use directives/`data-wp-init` with cleanup |

## Sources (checked 2026-10-08)

- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/api-reference/
- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/core-concepts/undestanding-global-state-local-context-and-derived-state/
- https://developer.wordpress.org/block-editor/reference-guides/interactivity-api/core-concepts/server-side-rendering/
- https://developer.wordpress.org/block-editor/reference-guides/block-api/block-supports/
- Core source read (trunk): `wp-includes/interactivity-api/interactivity-api.php` (`wp_interactivity_*` functions since 6.5; `wp_interactivity_get_context` 6.6; `wp_interactivity_get_element` 6.7)

Facts to verify in the API reference: `withSyncEvent` required since 6.8, generators for async actions, `withScope`, `splitTask`, `data-wp-each-key`, `asDangerousHTML`, the `!` operator limits, minimum WordPress 6.5.
