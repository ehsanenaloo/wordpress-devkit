# Stack signals and ownership

Contents: [How to read signals](#how-to-read-signals) - [Project shape signals](#project-shape-signals) - [wp-content layout](#wp-content-layout) - [Drop-ins](#drop-ins) - [mu-plugins and platform layers](#mu-plugins-and-platform-layers) - [Multisite](#multisite) - [Environment and configuration constants](#environment-and-configuration-constants) - [Version sources](#version-sources) - [Ownership map](#ownership-map) - [Sources](#sources)

A signal suggests a shape; two independent signals support it; runtime evidence confirms it. Record which kind you have.

## How to read signals

Classify each directory you were given as one of: first-party source, vendored dependency, generated artifact, third-party code that was copied in, or deployment/infra. Edits belong in first-party source only. Never infer "active" from "present": a plugin directory, a theme, a drop-in file, a Docker service or a CI workflow can be present and unused. Never infer "working" from "configured".

## Project shape signals

| Shape | Signals | Notes |
| --- | --- | --- |
| Single plugin | Header comment `Plugin Name:` in a root PHP file; `readme.txt`; `uninstall.php`; activation hooks | Check `Requires at least`, `Requires PHP`, `Requires Plugins` (WordPress 6.5+), `Update URI` (5.8+), `Network: true` |
| Theme: block | `theme.json`, `templates/index.html`, `parts/`, `patterns/`, `styles/` | `wp_is_block_theme()` (since 5.9) wraps `wp_get_theme()->is_block_theme()`, which the reference's user note ties to a block template `index.html` (the reference itself does not name the path; confirm in `WP_Theme::is_block_theme()`); `theme.json` `version` and `$schema` tell the schema level |
| Theme: classic | `style.css` header, `functions.php`, `header.php`, `index.php` | `Template:` header means a child theme: find the parent |
| Theme: hybrid | Both `theme.json`/block templates and PHP templates | Verify which templates are actually resolved on the site |
| Block library | `block.json` files (`apiVersion`, `render`, `viewScriptModule`), `@wordpress/scripts` in `package.json`, `src/` and `build/` | Built output may be committed or generated in CI: find where it is produced |
| WooCommerce extension or store | `woocommerce/` template overrides, gateway classes, `FeaturesUtil`, `Requires Plugins: woocommerce`, `WC tested up to` | HPOS declaration and active storage mode are separate facts |
| Headless | `faustwp`, WPGraphQL plugin, `next.config.*`, `astro.config.*`, `NEXT_PUBLIC_*` URLs pointing at WordPress, revalidation or preview code, CORS filters | Two deployables: WordPress backend and the frontend |
| Builder-driven | Elementor, WPBakery (`vc_*`), Divi (`et_pb_*`), Beaver, Bricks, Breakdance data in post meta or shortcodes | Content ownership is the builder's; do not plan a rebuild from this signal |
| ACF-heavy | `acf-json/`, `acf_add_local_field_group`, `get_field` | Content model lives in JSON or the database; check sync state |
| Composer-managed | root `composer.json` with `roots/wordpress`, `johnpbloch/wordpress`, `wpackagist-*`; `web/wp`, `web/app`, `config/application.php`, `.env` | Core and plugins are dependencies; `vendor/` and `web/app/plugins` are not hand-edited |
| Monorepo | several `composer.json`/`package.json`, `packages/`, workspaces | Pick the boundary the request names |
| Local-environment config | `.wp-env.json`, `docker-compose*.yml`, `.ddev/config.yaml`, `.lando.yml`, Playground `blueprint.json` | Describes dev/test, not production |

## wp-content layout

Standard layout: `wp-content/plugins/`, `themes/`, `mu-plugins/`, `uploads/`, `languages/`, `upgrade/`, plus drop-in files at the root of `wp-content`. The directory can be relocated with `WP_CONTENT_DIR`, `WP_PLUGIN_DIR`, `WPMU_PLUGIN_DIR` or a Bedrock-style `web/app` layout, so locate the real path from configuration before concluding a plugin is missing. `uploads/` is user data: never treat it as source or modify it. A `.maintenance` file at the site root is how WordPress signals maintenance mode during an update and can be left behind by an interrupted update (hosting guides agree; not a primary WordPress page). A non-empty `upgrade/` directory may be leftover update staging (check the host's update behavior); report both and do not delete them. Backup or `.zip` copies of plugins, `old-*` directories and `*.bak` files are risks to flag (exposure, stale code), not code to edit.

## Drop-ins

Drop-ins are PHP files WordPress loads from `wp-content` for special purposes. Their presence changes behavior globally and is often invisible in the admin plugin list except under "Drop-ins".

| File | Effect | Condition |
| --- | --- | --- |
| `advanced-cache.php` | Page cache hook point | Used when `WP_CACHE` is true |
| `object-cache.php` | External object cache (Redis, Memcached); transients move out of the options table | Loaded automatically; `wp_using_ext_object_cache()` reports it |
| `db.php` | Replaces the database class (read replicas, HyperDB, query logging) | Loaded automatically |
| `sunrise.php` | Multisite domain mapping before site resolution | Needs `SUNRISE` constant |
| `maintenance.php`, `db-error.php`, `php-error.php`, `fatal-error-handler.php` | Custom maintenance, error and fatal-error pages or handlers | Used on the respective event |
| `install.php` | Replaces the installer | Used during install |
| `blog-deleted.php`, `blog-inactive.php`, `blog-suspended.php` | Multisite messages | Multisite only |

Record each drop-in found, who owns it (plugin-generated or hand-written), and whether the code that expects it (a cache plugin) is present.

## mu-plugins and platform layers

Must-use plugins load automatically, cannot be deactivated in the UI and load in alphabetical order; only top-level PHP files load (a loader file is needed for subdirectories). They often hold hosting integration, security hardening, feature flags or the whole site's custom code. Inventory every file. Hosting layers commonly leave recognizable files (examples only: verify per host in its documentation): WP Engine `wpengine-common`, Kinsta `kinsta-mu-plugins`, Pantheon `pantheon.yml` and a `pantheon-mu-plugin`, WordPress VIP `client-mu-plugins`, `vip-config/`, `plugins/` conventions. Their presence says where behavior such as caching, CDN purge, login protection, cron or email may be implemented outside the repository.

## Multisite

Multisite is active when `wp-config.php` defines `MULTISITE` as true (with `SUBDOMAIN_INSTALL`, `DOMAIN_CURRENT_SITE`, `PATH_CURRENT_SITE`, `SITE_ID_CURRENT_SITE`, `BLOG_ID_CURRENT_SITE`) and `.htaccess`/server rules are in place. `WP_ALLOW_MULTISITE` alone only enables the Network Setup screen under Tools; it does not create or activate a network. Do not classify a project as multisite from `WP_ALLOW_MULTISITE`, `is_multisite()` calls in a library, or `switch_to_blog` code in a plugin that supports both. Consequences once confirmed: per-site options and tables (`wp_2_posts`), network-activated plugins, `sunrise.php` and domain mapping, per-site themes and locales, uploads under `sites/ID`, super-admin capabilities.

## Environment and configuration constants

Record names and presence, not secret values. Useful, non-secret flags: `WP_ENVIRONMENT_TYPE` (`local`, `development`, `staging`, `production`; invalid values are treated as production; read with `wp_get_environment_type()`), `WP_DEBUG`, `WP_DEBUG_LOG`, `WP_DEBUG_DISPLAY`, `SCRIPT_DEBUG`, `WP_CACHE`, `DISABLE_WP_CRON`, `ALTERNATE_WP_CRON`, `DISALLOW_FILE_EDIT`, `DISALLOW_FILE_MODS`, `AUTOMATIC_UPDATER_DISABLED`, `WP_AUTO_UPDATE_CORE`, `WP_MEMORY_LIMIT`, `WP_HOME`/`WP_SITEURL`, `FORCE_SSL_ADMIN`, `EMPTY_TRASH_DAYS`, `WP_POST_REVISIONS`, table prefix. Never record `DB_PASSWORD`, `*_KEY`, `*_SALT`, API tokens or `.env` values. `WP_DEBUG` true with display on in a production-typed environment is a candidate to hand to security and operations.

## Version sources

Trust order is in [safe-inventory.md](safe-inventory.md). Where to read each without executing code: WordPress core `$wp_version`, `$required_php_version` and `$required_mysql_version` in `wp-includes/version.php` (parse as text); plugin and theme headers in the main file or `style.css`; `composer.lock` (`packages[].version`, `platform` and `php` constraints); `package-lock.json`/`pnpm-lock.yaml`/`yarn.lock`; `.nvmrc`, `.node-version`, `.tool-versions`, `.php-version`, `engines` in `package.json`; `readme.txt` `Tested up to` and `Stable tag` (declared compatibility, not installed); Dockerfile `FROM` and compose image tags; `.wp-env.json` `core`; CI matrix versions.

## Ownership map

Fill this table for the task; leave "unknown" where evidence is missing.

| Area | Owner (code or service) | Evidence | Unknown |
| --- | --- | --- | --- |
| Bootstrap and config | wp-config.php, mu-plugin loader, Bedrock `application.php` | file paths | production values |
| Content model | CPTs, taxonomies, ACF JSON, block patterns | registrations | database state |
| Rendering | theme templates, block render callbacks, builder | files | which templates resolve |
| API and integrations | REST routes, GraphQL, webhooks, third-party services | registrations | credentials, live endpoints |
| Build and assets | package scripts, bundler, committed `build/` | package.json | where CI builds |
| Tests and static analysis | PHPUnit, PHPStan, PHPCS, Playwright | config files | last run result |
| Delivery | CI, deploy scripts, host Git, rsync, SFTP | workflows | production process |
| Hosting layer | drop-ins, mu-plugins, platform config | files | platform settings |
| Data and backups | database, uploads, object cache, CDN | docs | backup restore proof |

## Sources

Reviewed 2026-10-08.

- [Drop-ins list (_get_dropins)](https://developer.wordpress.org/reference/functions/_get_dropins/)
- [Create a network (WP_ALLOW_MULTISITE)](https://developer.wordpress.org/advanced-administration/multisite/create-network/)
- [wp_get_environment_type](https://developer.wordpress.org/reference/functions/wp_get_environment_type/)
- [wp_is_block_theme](https://developer.wordpress.org/reference/functions/wp_is_block_theme/)
- [Plugin header requirements](https://developer.wordpress.org/plugins/plugin-basics/header-requirements/)
- Host layer examples are heuristics; confirm in the host's documentation.
