# Environment doctor

Contents: [When to use](#when-to-use) - [Running it](#running-it) - [Modes and what each executes](#modes-and-what-each-executes) - [Reading the output](#reading-the-output) - [Evidence reports and comparison](#evidence-reports-and-comparison) - [Limits](#limits) - [Troubleshooting](#troubleshooting) - [Manual fallback](#manual-fallback) - [Sources](#sources)

Select this reference for `/wp-devkit:doctor`, environment discovery, or a request for versions, Docker state, active plugins, HPOS and object-cache inventory. Apply the engineering contract first.

## When to use

Use the doctor to get a repeatable, redacted snapshot of the local toolchain and, if explicitly authorized, of one named container's WordPress runtime. Do not use it as a security scan, compatibility certification or health check. A detected executable or file is not evidence of a working project.

## Running it

Run the self-contained `scripts/doctor.py` relative to this skill directory with Python 3.10 or later. Manual installations include the script and its report renderer (`scripts/evidence_report.py`). In the DevKit repository the equivalent entrypoint is `python scripts/doctor.py`.

```sh
# Filesystem and tool discovery only (default)
python scripts/doctor.py /path/to/project --output /path/to/evidence

# Trusted runtime inventory inside one named container
python scripts/doctor.py /path/to/project --container owned-wordpress --trusted-runtime --output /path/to/evidence
# Non-standard WordPress root inside the container
python scripts/doctor.py /path/to/project --container owned-wordpress --trusted-runtime --wordpress-root /var/www/site --output /path/to/evidence
```

Write the output directory outside the reviewed source tree. The report names the target by its absolute local path (it includes your user name and folder layout); add `--redact-paths` before sharing a report to record only the directory name. The command prints the path of `report.html`; `report.json` is the machine-readable twin.

## Modes and what each executes

| Mode | Runs | Does not run |
| --- | --- | --- |
| Default | Reads which top-level files exist (`composer.json`, `package.json`, `wp-config.php`, `wp-content`, `web/wp`, `theme.json`, `block.json`, compose files); runs `--version` for `php`, `node`, `npm`, `python`, `docker` found on PATH | Project scripts, WordPress, WP-CLI (found but deliberately not executed because `wp-cli.yml` can load PHP), secrets and configuration values |
| `--container NAME` | Adds `docker inspect` of that container's running state | Anything inside the container |
| `--container NAME --trusted-runtime` | Adds `docker exec NAME php -r <collector> <root>`: loads `wp-load.php` (WordPress and active plugin bootstrap), then reads WordPress, PHP and WooCommerce versions, multisite flag, external object cache flag, HPOS flag, current site's stylesheet and theme version, and every plugin with version, active and network-active flags | Writes, cache flushes, database checks, installs, attack probes; WP-Cron spawning is disabled via `DISABLE_WP_CRON` |

Authorization rule: trusted runtime executes the site's own bootstrap, which can have side effects (plugin load hooks, license pings, cache warmups). Use it only for a container the owner named and trusts, preferably a staging or disposable copy. The doctor refuses `--trusted-runtime` without `--container`, and validates container name and root path format.

## Reading the output

Each check has `id`, `status` (`passed`, `failed`, `unavailable`, `skipped`), `message` and `evidence`.

| Check id | Meaning |
| --- | --- |
| `filesystem` | Layout signals found at the top level (a list of names); not an exhaustive scan |
| `tool:php`, `tool:node`, `tool:npm`, `tool:python`, `tool:docker` | `passed` with the parsed version, `unavailable` if not on PATH, if its version probe exited with an error (for example a broken shim) or its output was not recognized, `failed` only if the probe timed out (15 s; the tool and any process it started are stopped) |
| `tool:wp` | Always `skipped` when found: execution omitted by design |
| `docker:container` | `passed` if the named container is running; otherwise `unavailable` |
| `wordpress:runtime` | `passed` with the runtime inventory; `failed` if the collector or validation failed (diagnostics withheld to protect secrets); `skipped` when no runtime mode was requested |

Exit codes: `0` when no check failed (unavailable and skipped are visible but not failures); `1` when at least one probe timed out or the runtime collector failed; `2` for invalid arguments or output-path problems. A `failed` check says the probe could not finish, not that the project is broken. The report ends with a `limits` list stating that the output is not a vulnerability scan or compatibility certification.

Runtime evidence example (values are illustrative):

```json
{
  "wordpress": "6.9",
  "php": "8.3.6",
  "multisite": false,
  "external_object_cache": true,
  "woocommerce": "10.8.0",
  "hpos": true,
  "theme": { "stylesheet": "twentytwentyfive", "version": "1.2" },
  "plugins": [
    { "file": "woocommerce/woocommerce.php", "version": "10.8.0", "active": true, "network_active": false }
  ]
}
```

Interpretation notes: theme `version` can be an empty string because themes need not declare a version; `hpos` is `null` when WooCommerce is not loaded, otherwise whether custom order tables are the authoritative store; `external_object_cache` true means a persistent cache drop-in is in use, so transients are not in the options table; plugin activation is for the current site only (check `network_active` and per-site state on multisite); must-use plugins and drop-ins are not listed. Container reports include the WordPress root in the target identity, so reports for different roots are never compared as the same target.

## Evidence reports and comparison

`scripts/evidence_report.py` renders any report of schema version 1 to escaped standalone HTML and JSON, and compares two reports for the same target:

```sh
python scripts/evidence_report.py current.json --output evidence/ --previous previous.json
```

Rules enforced: required `target` and `generated_at` (timezone-aware ISO time), unique non-empty ids, check statuses from the set above, finding fields `classification` (`confirmed` or `candidate`), `severity` (`CRITICAL`, `WARNING`, `INFO`), `remediation` (`open`, `fixed`, `unverified`, `accepted`), `location` and `evidence`. Comparison lists added, changed and absent items; an absent finding is reported as "resolution unverified", never as fixed. Use `candidate` classification for unconfirmed observations.

## Limits

- Filesystem mode never discovers active plugins, HPOS state or cache state; it sees only top-level files and tool versions.
- Runtime mode reads the current site (on multisite run per site or use network-level evidence separately).
- No credentials, environment values, database contents or arbitrary process diagnostics are collected, and none are shown on failure.
- Tool version output is parsed with an allow-list pattern; unrecognized output is "unavailable".
- A run shows the machine and container at one time. Re-run when the target changes.

## Troubleshooting

- `tool:python` failed on Windows: the PATH may contain the Microsoft Store `python` alias stub, which exits nonzero; the doctor then exits 1 although the project is fine. Disable the alias or note the failed probe as environmental. Only `python` is probed, so a host with only `python3` reports it unavailable.
- `wordpress:runtime` failed: the collector requires the WordPress root path to contain `wp-load.php`, a working database connection and PHP CLI in the container; output validation rejects unexpected shapes. Check the root with `--wordpress-root` and run the manual fallback below on a disposable copy to see the actual error.
- Container "unavailable": the name is wrong or the container is stopped; list running containers yourself and pass the exact name.
- Large plugin sets: the validator caps plugins at 2000 entries.

## Manual fallback

When the doctor cannot run, collect the same facts without bootstrapping production: parse `wp-includes/version.php`, plugin headers and lockfiles (see `safe-inventory.md`), ask the owner for the Site Health info export, and mark everything as owner-stated or checkout-only. State plainly that activation, HPOS authority and object-cache state are unverified.

## Sources

Reviewed 2026-10-08.

- [wp_using_ext_object_cache](https://developer.wordpress.org/reference/functions/wp_using_ext_object_cache/)
- [wp plugin list](https://developer.wordpress.org/cli/commands/plugin/list/)
- [WooCommerce HPOS](https://developer.woocommerce.com/docs/features/high-performance-order-storage/)
- [WP-CLI configuration (require loads PHP files)](https://make.wordpress.org/cli/handbook/references/config/)
- Behavior of `scripts/doctor.py` and `scripts/evidence_report.py` read directly from source in this review; exit codes follow `main()` (exit 1 on any failed check, argparse exit 2 on invalid input).
