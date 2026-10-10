# Runtime hardening and operational review

Researched 2026-10-08. Contents: 1 Scope and evidence | 2 WordPress configuration | 3 Server and filesystem | 4 Transport, headers and cookies | 5 Logging, backup and monitoring | 6 Staged testing bounds | 7 Checks

Source configuration is a hypothesis until the deployed response or environment confirms it. Docker localhost is not evidence of production TLS or hosting policy. Tool or host unavailable means unexecuted, not clean.

## 1. Scope and evidence

Record the environment: WordPress, PHP (version and SAPI), database (engine and version), web server, OS/container image digest, filesystem and object storage, cache layers, CDN/WAF, hosting provider. Compare with the supported versions in the project; a PHP minor past its security-support end is a finding by itself (DevKit was tested against WordPress 7.1 and PHP 8.3).

## 2. WordPress configuration

- `WP_DEBUG` off in production; `WP_DEBUG_DISPLAY` false; if `WP_DEBUG_LOG` is true the default log is `wp-content/debug.log`, which is web-readable on many hosts: set an explicit path outside the web root, or deny it, and verify with a request.
- `display_errors` off in PHP; `error_log` outside the web root.
- `wp-config.php` not readable by other users, not served as text; secrets and salts unique per environment; `DB_USER` limited to the application schema (no `FILE`, `SUPER`, `GRANT`; DDL rights only if updates run in-process).
- `FORCE_SSL_ADMIN`/HTTPS for admin and login; `home` and `siteurl` use `https`.
- `DISALLOW_FILE_EDIT` removes the theme/plugin editors; `DISALLOW_FILE_MODS` also blocks plugin/theme installs and updates and thus patch delivery, so use it only when updates ship through deployment. Neither stops a user who already has code execution.
- XML-RPC: disable if unused (`xmlrpc_enabled` filter or server rule); remember it supports multicall authentication attempts.
- REST user enumeration (`/wp/v2/users`) and author archives expose usernames; INFO unless usernames serve as secrets.
- Automatic updates: core minor and security updates are on by default; plugin and theme auto-update is opt-in. Since WordPress 6.6 a failed plugin auto-update that fatals the front end is rolled back automatically (loopback check), which restores plugin files; whether it also covers database changes made by that plugin's upgrade routine is unverified, so assume it does not.
- Application passwords available over HTTPS only; review who has them.
- Salts and keys: rotating them invalidates sessions; document it as the response to suspected session theft.

## 3. Server and filesystem

- PHP execution denied in `wp-content/uploads` (and cache, backup and export directories): Apache `.htaccess` rules apply only if `AllowOverride` is on; nginx needs an explicit `location` rule. Verify with an inert fixture such as a `.php` file containing plain text, in staging only.
- File ownership: code read-only to the web user where deployment allows; writable only for uploads/cache. Permissions of `wp-config.php` and private directories.
- Directory listing off; backups, `.git`, `.env`, `*.sql`, `*.zip`, `composer.json`/`lock` and `debug.log` not web-reachable (request each path on staging).
- PHP: `expose_php` off, `open_basedir` or container isolation, `disable_functions` as defense in depth, opcache validation settings matching the deploy model, `session.cookie_*` for non-WordPress sessions.
- Database: not network-exposed; TLS to a remote DB; separate users for application, backup and migrations; no default `wp_` prefix reliance as a control.
- Containers: pinned image digests, non-root user, read-only root filesystem where possible, no secrets in image layers or build args, published ports minimal, mounts reviewed. Never dump credential values while inspecting.

## 4. Transport, headers and cookies

Verify on real HTTPS responses (including redirects, login, cart/checkout, logout):

| Item | Check |
|---|---|
| HTTP to HTTPS | 301 to the canonical host; no mixed content |
| HSTS | `Strict-Transport-Security` with an appropriate `max-age`; `includeSubDomains`/`preload` only after subdomain audit |
| Content-Security-Policy | Roll out as `Content-Security-Policy-Report-Only`, review reports (editor, checkout, third parties), then enforce |
| Framing | `frame-ancestors` (CSP) or `X-Frame-Options`; WordPress sends `X-Frame-Options: SAMEORIGIN` on admin and login pages |
| `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy` | Present and not breaking features |
| Cache-Control | `no-store`/private on authenticated, cart, account and nonce-bearing responses |
| Cookies | `Secure`, `HttpOnly`, `SameSite` (Lax or stricter where flows allow) on session and auth cookies; scope and lifetime; check `Set-Cookie` of the plugin's own cookies |

A hardening header is INFO unless a concrete attack depends on its absence. A missing HSTS header on a site that serves login over HTTPS only is WARNING at most.

## 5. Logging, backup and monitoring

- Central logs with retention, redaction of tokens, passwords, personal data and payment data; alerting owner named.
- Authentication and privilege events logged (login failure bursts, new admin, plugin install, option changes such as `siteurl`).
- Backups encrypted, stored where the same compromise cannot delete them, and restored in an isolated environment on a schedule; record restore time and what was verified (content, configuration, uploads, DB).
- File-integrity monitoring and malware scanning complement `wp core verify-checksums`; none certifies security.
- Patch cadence: record how quickly a critical advisory reaches production.

## 6. Staged testing bounds

Use a scoped staging DAST or penetration plan: allowlisted host, named accounts per actor, request and time bounds, non-destructive payloads, cleanup steps, an owner who can stop it. A scanner alert is a lead; confirm prerequisites and an actual unauthorized effect before reporting. Rate and brute-force tests need controlled accounts and explicit request counts. Never run probes against production without explicit authorization, and never plant executable probes in production uploads.

## 7. Checks

1. Evidence table per item above: observed response or setting, environment, date.
2. `curl -sI https://staging.example/` and the login/cart responses for headers; `curl -s -o /dev/null -w '%{http_code}'` for each sensitive path.
3. `wp config get WP_DEBUG` / `wp eval 'var_dump( defined( "WP_DEBUG_LOG" ) );'` on staging, not production secrets.
4. A pass proves the sampled responses and settings only; it does not cover other hosts, CDN edge variants or other user states.

Sources: [Hardening WordPress](https://developer.wordpress.org/advanced-administration/security/hardening/) | [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/) | [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html) | [WP 6.6 auto-update rollback (Trac)](https://core.trac.wordpress.org/changeset/58128). | [core default-filters.php (send_frame_options_header)](https://github.com/WordPress/wordpress-develop/blob/trunk/src/wp-includes/default-filters.php)
