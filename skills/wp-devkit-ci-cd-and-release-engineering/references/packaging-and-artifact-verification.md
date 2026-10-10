# Packaging, versioning and artifact verification

Contents: the artifact is the unit of release; deterministic build; include/exclude policy; version consistency; inspecting the archive; smoke install and upgrade tests; provenance and checksums; dependency collisions; themes and blocks; false positives.

Researched 2026-10-08. Sources: [Composer CLI](https://getcomposer.org/doc/03-cli.md), [wp dist-archive](https://developer.wordpress.org/cli/commands/dist-archive/), [actions/upload-artifact README](https://github.com/actions/upload-artifact), [artifact attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds) (docs use `actions/attest`; `actions/attest-build-provenance` was at v4.2.2 on the research date), [10up deploy action README](https://github.com/10up/action-wordpress-plugin-deploy), [plugin readme rules](https://developer.wordpress.org/plugins/wordpress-org/how-your-readme-txt-works/).

## The artifact is the unit of release

Build once from a clean checkout of the tagged commit, inspect it, record its digest, and promote those exact bytes everywhere (GitHub release, WordPress.org, host deploy). Rebuilding per destination produces different artifacts that were never tested. The repository tree is not the artifact: `git` ignores built assets, development dependencies may be installed, and `.gitattributes`/`.distignore` filters change contents.

## Deterministic build

- Install from lockfiles only: `composer install --no-dev --optimize-autoloader --no-interaction` (use `--classmap-authoritative` only if nothing is autoloaded dynamically; it implies optimization), `npm ci`. Never `composer update` or `npm install` in a release job. `composer validate --strict` and `composer audit --locked --no-dev` are cheap pre-checks.
- Pin runtime versions (PHP, Node via `.nvmrc`/`engines`) and print them in the log.
- No network fetch of unpinned scripts (`curl | sh`). If a binary is downloaded (for example a tool), verify its checksum.
- Set build timestamps from the commit (`SOURCE_DATE_EPOCH`) if reproducibility is a goal; sorting the zip entries and fixing mtimes makes the digest stable (`wp dist-archive` output is not documented as reproducible, so verify).
- Compiled assets (`build/`, `dist/`) are generated in CI and appear in the artifact even if git-ignored. A checked-out source tree without them is not releasable.

## Include and exclude policy

- Keep a single list of exclusions: `.distignore` (used by `wp dist-archive` and by the 10up deploy action) or `.gitattributes` `export-ignore` (used by `git archive`). `.distignore` cannot negate patterns the way `.gitignore` can. Alternatively build into a clean directory (`BUILD_DIR` for the 10up action) and ship everything in it.
- Exclude: `.git*`, `.github`, tests and fixtures, `node_modules`, `src/` that is compiled elsewhere, lock and tool config as policy dictates, local env files, IDE files, docs not needed at runtime, source maps if policy says so.
- Include: main plugin file, `readme.txt`, `LICENSE`/license headers, `languages/` or JSON translations, compiled assets, production `vendor/` with its autoloader, `uninstall.php`, `index.php` guards if used.
- The zip's top-level folder must equal the plugin slug (no version suffix) and contain the main file at `slug/slug.php`. A GitHub-generated "Source code" zip fails this and includes development files; attach a built zip to the release instead.

```sh
wp dist-archive . "dist/my-plugin.zip" --plugin-dirname=my-plugin --force   # honors .distignore
```

## Version consistency (single source, checked)

For a plugin, these must agree for a release `X.Y.Z`: plugin header `Version`, any version constant, `readme.txt` `Stable tag` (in trunk and the tag), the git tag (`vX.Y.Z` or `X.Y.Z` per project convention), the changelog heading, and `package.json`/`composer.json` version if present. A check:

```sh
set -eu
tag="${GITHUB_REF_NAME#v}"
header=$(sed -n 's/^[[:space:]]*\*\{0,1\}[[:space:]]*Version:[[:space:]]*//p' my-plugin.php | head -n1 | tr -d '\r')
stable=$(sed -n 's/^Stable tag:[[:space:]]*//Ip' readme.txt | head -n1 | tr -d '\r')
const=$(sed -n "s/.*define( *'MY_PLUGIN_VERSION', *'\([^']*\)'.*/\1/p" my-plugin.php | head -n1)
for v in "$header" "$stable" "$const"; do
  [ "$v" = "$tag" ] || { echo "Version mismatch: tag=$tag header=$header stable=$stable const=$const" >&2; exit 1; }
done
```

Notes: `Requires at least` is read from the main plugin file header since WordPress 5.8, so keep it there; `Tested up to` and `Requires PHP` belong to the support policy and must match what CI proves. `Stable tag: trunk` is discouraged and prohibited for new plugins.

## Inspect the archive

```sh
unzip -Z1 dist/my-plugin.zip | sort > dist/manifest.txt
test "$(cut -d/ -f1 dist/manifest.txt | sort -u)" = "my-plugin"
unzip -Z1 dist/my-plugin.zip | grep -E '(^|/)(\.git|\.github|node_modules|tests?|\.env[^/]*|phpunit\.xml(\.dist)?)(/|$)' && { echo "forbidden path in archive" >&2; exit 1; } || true
unzip -Z1 dist/my-plugin.zip | grep -q '^my-plugin/my-plugin.php$'
unzip -Z1 dist/my-plugin.zip | grep -q '^my-plugin/vendor/autoload.php$'      # if vendor is required at runtime
unzip -p dist/my-plugin.zip my-plugin/my-plugin.php | php -l
```

Adjust the deny list to the project's policy. A secret scan (`gitleaks`/`trufflehog`-class tools, or the project's tool) over the extracted tree catches credentials left in config. Compare `manifest.txt` with the previous release's manifest and review additions and removals; unexpected new top-level paths are the usual signal of a packaging regression.

## Smoke install, upgrade and uninstall (disposable site)

1. Fresh WordPress (wp-env or a container): `wp plugin install ./dist/my-plugin.zip --activate`, load a front-end and admin page, check `wp plugin list`, PHP error log empty.
2. Upgrade: install the previous released zip, create representative data, then `wp plugin install ./dist/my-plugin.zip --force`; run the plugin's upgrade routine; verify data and settings.
3. Minimum environment: repeat step 1 on the declared minimum PHP/WP cell.
4. Deactivate and uninstall: `wp plugin deactivate my-plugin && wp plugin uninstall my-plugin`; confirm options, tables, transients and scheduled hooks are removed as designed (`wp option list --search='my_plugin*'`, `wp cron event list`).
5. Multisite: network activate and per-site activate.

These are the checks that a green unit-test run does not provide.

## Provenance and checksums

- Record SHA-256 of the archive (`sha256sum`), publish it with the release, and upload the artifact with `if-no-files-found: error`. The `upload-artifact` output `artifact-digest` ties a job's artifact to a digest.
- Attest the built archive in the build job: permissions `id-token: write`, `attestations: write`, `contents: read`; the documented action is `actions/attest` (the older `actions/attest-build-provenance` wrapper also exists). Consumers verify with `gh attestation verify dist/my-plugin.zip -R owner/repo`. Attestations prove which workflow built the bytes, not that the code is safe; availability: attestations work on every plan for public repositories, while private and internal repositories require GitHub Enterprise Cloud (GitHub Enterprise Cloud docs, found by search; the how-to page itself is silent), so confirm it for the target.
- Optional: generate an SBOM (`cyclonedx/cyclonedx-php-composer`, command `CycloneDX:make-sbom`; `npm sbom --sbom-format=cyclonedx|spdx`) and attach it. It supports audits; it does not fix vulnerabilities.
- Promotion jobs download the artifact, verify digest/attestation, then publish. They never rebuild.

## Dependency collisions (WordPress-specific)

Every plugin shares one PHP process. Two plugins shipping different versions of the same Composer library collide (first loaded wins). For libraries that are not widely shared, prefix namespaces at build time with Strauss (`brianhenryie/strauss`, a Mozart fork), PHP-Scoper (`humbug/php-scoper`) or Mozart, and test the prefixed build (autoload map, reflection and string-class usage break easily; Strauss rewrites only classes it scanned). Do not ship `require-dev` packages. Do not auto-update bundled libraries without a changelog review.

## Themes, blocks and mixed repositories

- Themes: zip root is the theme directory with `style.css` header (`Version`, `Requires at least`, `Requires PHP`, `Text Domain`); compiled CSS/JS must be inside; child-theme parents are not bundled.
- Blocks: `block.json` `version`/`apiVersion`, built `build/` output and `viewScriptModule` assets must be in the archive; run `npm run build` in CI, not on the host.
- Monorepos with several plugins: one artifact per plugin, versioned independently.

## Looks wrong but is fine

- Source maps or `composer.json` present in the archive when policy allows them.
- A build directory listed in `.gitignore` but included by the packaging step.
- Different tag formats (`v1.2.3` vs `1.2.3`) as long as the check normalizes them and the WordPress.org tag is the bare version.
- Re-running packaging in a dry run that publishes nothing.
