# Embedding, query API and shareable links

Contents: query API, loading Blueprints, iframe/JS client, origin and message hygiene, sources.

## Query API (playground.wordpress.net)

`php` (a supported PHP minor version, `latest`, `next`; look up the supported range and the default online), `wp` (`latest`, `nightly`, `beta`, recent majors), `blueprint-url`, `plugin` and `theme` (WordPress.org slugs, repeatable), `url` (initial page), `login` (`yes`/`no`), `networking`, `multisite`, `mode` (`browser-full-screen` or `seamless`), `storage=temp`, `can-save=no`, `site-slug`, `language` (needs networking), `import-site`, `import-wxr`, `gutenberg-pr`, `gutenberg-branch`, `core-pr`, `lazy`, `page-title`. Installing a plugin or theme through these logs in as admin. Without `storage=temp` or `can-save=no`, the site may autosave in browser storage.

A Blueprint can also be passed in the URL fragment as JSON (optionally `encodeURIComponent`-encoded) or Base64, per the Using Blueprints and "How to load and run Blueprints" docs (via search result); browsers do not send fragments to servers, but anyone holding the link sees the Blueprint. Do not put secrets in a shared link or Blueprint.

## Remote Blueprint and bundle loading

`?blueprint-url=` must point at a file served with CORS headers that allow the Playground origin. ZIP bundles need `blueprint.json` at the root or inside exactly one top-level directory. A GitHub "blob" page URL is HTML, not the file; use the raw URL or `git:directory` resources. Test the link in a private window with no sign-ins.

## Embedding

```html
<iframe id="wp" style="width:100%;height:480px;border:1px solid #ccc"></iframe>
<script type="module">
  import { startPlaygroundWeb } from 'https://playground.wordpress.net/client/index.js';
  const client = await startPlaygroundWeb({
    iframe: document.getElementById('wp'),
    remoteUrl: 'https://playground.wordpress.net/remote.html',
    blueprint: { landingPage: '/wp-admin/', preferredVersions: { php: '8.3', wp: 'latest' } }, // optional: `blueprint` is in StartPlaygroundOptions in the client source; the docs page shows only iframe and remoteUrl
  });
  await client.isReady();
</script>
```

- The client README recommends importing the client from the same deployment as the runtime; an npm-installed client can drift from the hosted `remote.html`. If you use npm, pin client and remote versions together or self-host.
- Self-host the runtime if you need availability you control; that is a design judgment, not a documented requirement.
- Pass only data the page owns into the Blueprint. If the host page listens for `message` events, validate `event.origin` and the message shape; never `eval` or render message data as HTML.
- A docs page that embeds a generic site does not demonstrate the target defect; the landing page and seed must expose it.

## Sources

Research date: 2026-10-08.

- https://developer.wordpress.org/playground/developers/query-api/
- https://developer.wordpress.org/playground/blueprints/bundles/
- https://developer.wordpress.org/playground/developers/apis/javascript-api/ (`iframe`, `remoteUrl`, `isReady()`)
- https://github.com/WordPress/wordpress-playground/blob/trunk/packages/playground/client/README.md (same-origin import recommendation, npm drift warning)
- https://github.com/WordPress/wordpress-playground/blob/trunk/packages/playground/client/src/index.ts (`StartPlaygroundOptions.blueprint`)
- https://developer.wordpress.org/playground/blueprints/using-blueprints/ and .../tutorial/how-to-load-run/ (fragment Blueprints; search result only)
