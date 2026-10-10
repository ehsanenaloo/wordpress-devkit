# WordPress.org releases, host deployment and rollback

Contents: WordPress.org plugin release mechanics; automating with a tag workflow; readme and directory rules; pre-publish gates; propagation and verification; rollback reality; non-directory distribution; host deployments; data and migration rollback; release record; false positives.

Researched 2026-10-08. Sources: [Using Subversion](https://developer.wordpress.org/plugins/wordpress-org/how-to-use-subversion/), [How your readme.txt works](https://developer.wordpress.org/plugins/wordpress-org/how-your-readme-txt-works/), [10up WordPress plugin deploy action](https://github.com/10up/action-wordpress-plugin-deploy), [Plugin Check action](https://github.com/WordPress/plugin-check-action), WordPress core `wp-includes/update.php` (version comparison), [WP-CLI dist-archive](https://developer.wordpress.org/cli/commands/dist-archive/). The SVN handbook does not describe a rollback procedure; the rollback section below is derived from core behavior and marked as such.

## WordPress.org SVN mechanics

- Repository layout: `/trunk` (development state, main plugin file directly inside, not in a subfolder), `/tags/<version>` (release snapshots; names look like versions), `/assets` (banners, icons, screenshots; keep them out of trunk), `/branches` (not used by WordPress.org).
- Release = update trunk including `readme.txt` `Stable tag`, `svn cp trunk tags/<version>`, commit with a message. The directory reads `Stable tag` from `trunk/readme.txt`, then serves the matching `/tags/<stable>/` folder; once a tag folder exists its readme is what displays, so the readme in the tag must carry the correct Stable tag too. `Stable tag: trunk` works but is discouraged and prohibited for new plugins.
- Everything committed is distributed, including `vendor/`, build output and stray files. Do not upload zip files, do not commit every small change (SVN is a release system), and keep commit messages meaningful. Treat published tags as immutable; a fix is a new version. (The SVN handbook recommends tagging so rollbacks are possible but states no no-edit rule; immutability here is release practice.)
- Each commit rebuilds the zip files for all versions; the handbook says updates can take up to about 6 hours to appear. Plan verification and communication around that delay.
- Credentials: SVN username is case-sensitive; use the SVN-specific password if a commit fails with "Access forbidden". Store them as environment secrets with required reviewers (`SVN_USERNAME`, `SVN_PASSWORD`).

## Tag-triggered deployment

```yaml
name: release-wporg
on:
  push:
    tags: ['[0-9]*.[0-9]*.[0-9]*']       # bare versions match the SVN tag
permissions:
  contents: read
concurrency:
  group: wporg-release
  cancel-in-progress: false
jobs:
  deploy:
    runs-on: ubuntu-24.04
    environment: wordpress-org            # required reviewers + tag rule
    steps:
      - uses: actions/checkout@<sha> # v7.0.1
        with: { persist-credentials: false }
      # build once, verify (see packaging reference), then:
      - name: Deploy dry run
        uses: 10up/action-wordpress-plugin-deploy@<sha> # 2.3.0
        with:
          dry-run: true
          generate-zip: true
        env:
          SVN_USERNAME: ${{ secrets.SVN_USERNAME }}
          SVN_PASSWORD: ${{ secrets.SVN_PASSWORD }}
          SLUG: my-plugin
```

Facts from the action's README: it commits the contents of the Git tag to the directory using the same tag name; it excludes files per `.distignore` (preferred) or `.gitattributes` `export-ignore`; it moves `.wordpress-org/` into the SVN `assets` directory; `BUILD_DIR` deploys a prepared directory and ignores `.distignore`; `VERSION` defaults to the tag name (do not set it except for tests); `dry-run: true` skips the final SVN commit; `generate-zip: true` outputs `zip-path`. Keep the dry run as a separate, always-run job and the real commit as a gated job in the protected environment; review the dry run's file list first. Check the action's latest release and pin by SHA; it was last released in January 2025, so confirm it still fits the current directory rules.

## Directory-readiness gates (before the SVN commit)

1. Version consistency check (packaging reference): header `Version`, `Stable tag`, tag, changelog.
2. `readme.txt` validity: 1 to 5 `Tags`; `Contributors` are WordPress.org usernames; `Tested up to` is a number only and only the major version matters (minor versions are ignored); `Requires PHP` numbers only; license GPLv2-compatible; short description about 150 characters, no markup; `Requires at least` lives in the main plugin file header since WordPress 5.8. A readme larger than 10k may result in errors (readme handbook): keep recent notes in `readme.txt` and move old history to `changelog.txt`.
3. Plugin Check: `wordpress/plugin-check-action` with `build-dir` set to the built tree; inputs include `checks`, `exclude-checks`, `ignore-codes`, `categories`, `exclude-directories`, `ignore-warnings`. Narrow ignores with a reason; do not blanket-ignore categories to turn it green.
4. Smoke install of the exact zip (packaging reference). `Tested up to` must be a version your matrix actually ran.
5. Changelog and, if the release changes data, upgrade notice text.
6. Guideline conformance for the directory (no obfuscated code, no tracking without opt-in, no embedded licensing nags beyond the guidelines): a human review item, not automatable.

## Verification after publishing

After the propagation window: fetch the public plugin info, compare the live version to the tag, install from the directory on a disposable site (`wp plugin install my-plugin`), run the smoke checks, and confirm an upgrade from the previous version works through the normal updater (`wp plugin update my-plugin`). Check the plugin page for the intended readme, banner and screenshots.

## Rollback reality (derived from core behavior)

- WordPress offers a plugin update only when the version served by the directory is higher than the installed version: `wp-includes/update.php` uses `version_compare( $update->new_version, $plugin_data['Version'], '>' )`. Pointing `Stable tag` back to an older tag therefore does not downgrade sites that already installed the bad version; it only changes what new installs receive.
- The practical fix is a new, higher version (for example 1.4.2 after a bad 1.4.1) containing the last known-good code plus the fix, released through the same pipeline. Keep the previous known-good tag so the diff is mechanical.
- A bad release also needs: stop further spread (point `Stable tag` at the last good tag only if the bad one cannot be fixed quickly, accepting the propagation delay), a statement of impact, and a data repair plan if the bad version wrote data.
- Plan the rollback before the release: which tag is known-good, who can commit, what data the bad version may have changed and how it is repaired.

## Distribution outside WordPress.org

- GitHub release assets: attach the built zip, its SHA-256 and the attestation; never the auto-generated source zip. The release should be created by the same verified artifact.
- Self-hosted update servers or commercial updaters: sign or checksum packages, serve over HTTPS, version monotonically, and keep the update metadata endpoint in the release checklist. A compromised update endpoint is a remote code execution path to every site, so credentials for it get the strictest environment protection.
- Composer packages (Packagist, private repositories) use tags; mark which tags are installable on production.

## Host deployments (sites and agencies)

- Build the release artifact in CI; the host receives artifacts, not a `git pull` plus `composer install`.
- Atomic switch: upload to a new release directory, link shared state (uploads, `wp-config.php`), run checks, switch a `current` symlink, keep the last N releases for instant rollback.
- Pre-deploy: confirm a fresh database backup exists and is restorable; enable maintenance mode only if the release has a breaking data step.
- Post-deploy WP-CLI sequence as needed (each only when relevant): `wp core update-db` (multisite: `--network`), plugin upgrade routines, `wp cache flush`, `wp rewrite flush`, `wp cron event run --due-now` if schedules changed. Smoke test: health URL, a logged-in admin page, one write path, the REST root, error log tail.
- Database changes follow expand/contract: ship a backward-compatible additive migration first, switch code, remove old structures in a later release. Then code rollback does not need a data rollback. A migration that drops or rewrites data needs a tested restore, not a revert script.
- Feature flags (options, constants, environment variables) allow disabling a risky path without redeploying.
- Multisite: migrations run per site; a partial failure leaves mixed versions, so migrations must be idempotent and resumable (`wp site list --field=url`, loop with `--url`).

## Release record

Each release logs: version, commit SHA, tag, artifact name and SHA-256, attestation reference, workflow run URL, approver, environment, start/end time, verification results, and the rollback target. Without this, "which build is live" is guesswork.

## Looks wrong but is fine

- A WordPress.org workflow that deploys from a tag with `dry-run` in a separate verification job.
- `Tested up to` set to a major version only.
- Stable tag in trunk readme equal to a tag that already exists, with trunk code identical to it.
- Keeping `.wordpress-org/` in the repo to feed SVN assets.
