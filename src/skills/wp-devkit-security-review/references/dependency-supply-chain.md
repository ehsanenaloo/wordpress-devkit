# Dependency and supply-chain review

Researched 2026-10-08. Contents: 1 Inventory | 2 Scan runbook | 3 Triage | 4 Build and CI chain | 5 WordPress packages | 6 Checks

## 1. Inventory

Collect from lockfiles and the real build path, not from `composer.json`/`package.json` ranges: `composer.lock`, `package-lock.json`/`pnpm-lock.yaml`/`yarn.lock`, vendored copies (`vendor/` committed, bundled libraries inside the plugin, minified JS with a version banner), Docker base images, GitHub Actions and their pinned refs, and WordPress plugins/themes the project requires. For each: name, exact resolved version, source/registry, integrity hash present, license, maintainer activity, whether install scripts run (`scripts` in Composer, `preinstall/postinstall` in npm).

## 2. Scan runbook (review mode, read-only)

Discover which lockfiles and scripts exist, then run only audit commands:

```sh
composer audit --locked --format=json            # advisories for the lock, regardless of vendor/
composer audit --locked --no-dev --format=json   # runtime-only view
npm audit --omit=dev --json                      # production deps; add --package-lock-only to ignore node_modules
npm audit signatures                             # registry signatures and provenance (needs installed tree)
```

- Record tool version, exit code, date, scope and (for Composer) the advisory source. Composer returns nonzero when advisories or policy matches (abandoned packages with `--abandoned=fail`) are found; the Composer docs list only `0` (no issues) and `1` (policy matches or missing packages) for `audit`; other versions may differ, so read `composer audit --help` for the installed one. `npm audit` exits nonzero at or above `--audit-level`; the flag does not filter the report.
- Never run `npm audit fix`, `composer update`, or regenerate a lockfile during review; audit tooling may touch caches or the network but that does not authorize dependency changes.
- Unsupported flag, no network, or no lockfile means the scan is unexecuted, not clean. Say so.
- Validate the gate on a throwaway project with a known-vulnerable fixture, never by adding a vulnerable package to the real lock.
- `composer audit` and `npm audit` do not cover WordPress.org plugins/themes or bundled third-party copies; use the vendor advisory (Patchstack, Wordfence Intelligence, WPScan databases, the plugin's changelog) and match the exact version.

## 3. Triage

Classify each hit as: reachable vulnerability (affected version, vulnerable function called with attacker input), affected dependency with unknown reachability, affected but dev-only/build-only, false match (name/version mismatch, advisory withdrawn), or unavailable scan. Confirm against the primary advisory (GitHub Security Advisory, FriendsOfPHP, vendor bulletin): affected range, fixed version, preconditions. Severity follows reachability and exposure, not the advisory's CVSS alone. A dev-only dependency in a published plugin zip is INFO unless the zip ships it.

Also review: abandoned or unmaintained packages, single-maintainer risk for critical dependencies, typosquatting (similar names, new packages with install scripts), dependency confusion for private package names, license conflicts with GPL distribution (WordPress.org requires GPL-compatible code), and bundled libraries that duplicate WordPress core (jQuery, PHPMailer) and can drift behind core's patched copy.

## 4. Build and CI chain

- Pin GitHub Actions to a full commit SHA (tags are mutable); minimize `permissions:` on `GITHUB_TOKEN`; no secrets to workflows triggered by forks (`pull_request_target` with checkout of PR code is a classic exposure); separate build and release credentials.
- `curl | bash` installers, downloaded binaries without checksum verification, `composer install` without `--no-scripts` in untrusted contexts, `npm ci` vs `npm install` (the former honors the lock), and caching that restores from untrusted branches.
- Release provenance: the zip published to WordPress.org or a customer should be built in CI from a tagged commit, with a recorded digest; compare against `git archive` and `.distignore`/`.gitattributes` so dev files, `.env`, `.git`, backups and tests do not ship.
- Build artifacts: minified bundles checked in must be reproducible from source; source maps may reveal source and secrets in comments.
- Lockfile integrity: lockfile changes in a PR deserve review (resolved URLs pointing at unexpected hosts).

## 5. WordPress packages

Inventory with `wp core version`, `wp plugin list --format=json`, `wp theme list --format=json` against a staging copy. Check the update state and vendor advisories for exact versions; abandoned plugins closed on WordPress.org are a finding by themselves only if exposed to attacker input. Must-use plugins and drop-ins (`object-cache.php`, `advanced-cache.php`, `db.php`) execute early and with full privileges: review their provenance.

## 6. Checks

| Check | Passing proves | Does not prove |
|---|---|---|
| `composer audit --locked`, `npm audit --omit=dev` clean | No known advisory for audited locks on that date | Reachability, WordPress plugin advisories, unknown flaws |
| `npm audit signatures` ok | Registry signatures match | Package safety |
| Actions pinned and permissions minimal | Smaller blast radius | Absence of compromised pinned commit |
| Release zip digest matches CI build | Artifact came from the pipeline | That the source was safe |

Sources: [Composer audit](https://getcomposer.org/doc/03-cli.md#audit) | [npm audit](https://docs.npmjs.com/cli/v11/commands/npm-audit) | [GitHub Actions security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions) | [OWASP Top 10:2025 A03 Software Supply Chain Failures](https://top10.owasp.org/2025).
