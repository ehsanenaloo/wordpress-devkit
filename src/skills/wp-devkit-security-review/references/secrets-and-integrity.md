# Secrets, integrity and personal data

Researched 2026-10-08. Contents: 1 Secret discovery | 2 Handling a hit | 3 Storing secrets in WordPress | 4 Integrity checks | 5 CSP rollout | 6 Personal data exposure | 7 Checks

## 1. Secret discovery

Search tracked files, relevant Git history, CI logs and variables, build artifacts and release zips, client bundles and source maps, error responses, backups and exports for real credentials, private keys, tokens, database URLs, salts and personal data. Redact in every report: show type, location, prefix (4 characters at most) and length.

Use the project's approved scanner with redacted output on the working tree, history and built artifacts (for example gitleaks or trufflehog if the project already uses one). Record scanner and config version and exclusions. Prove the gate with an inert synthetic canary in a disposable repository that must fail the scan. Never print a discovered secret to demonstrate detection.

Classification before reporting: active credential, expired or revoked credential, test/sandbox value, public identifier (publishable key, client ID, site key), hash or checksum, random fixture, documentation placeholder. Credential-shaped is not credential. Examples of public-by-design: Stripe publishable key, reCAPTCHA site key, Google Maps browser key (restricted by referrer). Examples of secret: WordPress salts and `DB_PASSWORD`, `sk_live_` keys, webhook signing secrets, SMTP passwords, private deploy keys, OAuth client secrets.

## 2. Handling a hit

1. Establish exposure: where it was visible, who could read it, since when, whether the repository or artifact is public.
2. Establish state: still valid? Test only through the authorized owner or the provider's own revocation console, never by using the credential.
3. Revoke and rotate through the owner; deleting the file or rewriting history does not un-leak a credential. Rewriting history is optional hygiene after rotation.
4. Look for use: provider access logs, WordPress user and option changes, new admin accounts.
5. Record the owner, rotation time and the follow-up preventing recurrence (pre-commit scan, secrets in environment or secret manager, `.gitignore`/`.distignore`).

## 3. Storing secrets in WordPress

- Prefer environment variables or constants defined in `wp-config.php` / a secrets manager over `wp_options`; options appear in database dumps, exports and sometimes in `wp-json` settings endpoints if registered with `show_in_rest`.
- If a secret must be stored in the database, treat the DB dump as sensitive and consider encryption with a key held outside the DB (for example libsodium `sodium_crypto_secretbox` with a key from the environment); do not invent reversible "obfuscation" and do not call it encryption.
- Never log secrets, authorization headers or full request bodies containing them (`error_log( print_r( $args, true ) )` of an HTTP call is a classic leak). Mask in admin settings screens (show last 4 characters, leave the field blank to keep).
- Do not ship secrets in JS (`wp_localize_script`, block attributes, REST responses to low roles).
- Compare MACs and tokens with `hash_equals()`; generate tokens with `wp_generate_password( 32, false )` or `random_bytes()`, never `rand()`, `mt_rand()`, `uniqid()` or `md5( time() )`.

## 4. Integrity checks

- `wp core verify-checksums` compares installed core files with WordPress.org MD5 checksums for the installed version and locale (pass `--version` and `--locale` to match; `--include-root` also reports unexpected items in the root). `wp plugin verify-checksums --all` does the same for plugins hosted on WordPress.org; premium, custom and unlisted plugins cannot be verified this way and need a comparison against a trusted build digest. `--strict` also fails on minor changes such as readme edits. Do not use `--insecure` in a review.
- A mismatch is an investigation lead (legitimate patches, translation files, hosting-injected files); clean output does not exclude database malware, malicious users, rogue options, stolen credentials or modified `wp-config.php`/mu-plugins.
- Preserve evidence (copy suspect files, record timestamps and logs) before authorized remediation.
- Compare custom code with the reviewed Git tag or CI artifact digest rather than with the live server.
- Review mu-plugins, `object-cache.php`, `advanced-cache.php`, cron events (`wp cron event list`), admin users (`wp user list --role=administrator`) and `siteurl/home` values for unexpected entries.

## 5. CSP rollout

1. Inventory origins required by core editor, plugins, analytics, payments and fonts.
2. Deploy `Content-Security-Policy-Report-Only` with a reporting endpoint; collect for a full business cycle including checkout and the block editor.
3. Replace inline scripts with nonce- or hash-based allowances where possible; avoid `unsafe-inline`/`unsafe-eval` unless a measured need is accepted and documented.
4. Enforce, keep Report-Only for the next stricter policy, and test login, checkout, previews and media after each change.
The block editor and many plugins rely on inline styles and scripts; a strict CSP on `wp-admin` is a project, not a one-line header.

## 6. Personal data exposure

- Identify personal data in custom tables, meta, logs, exports, REST responses and cache. Minimize collection and retention; document purpose and legal basis outside the code.
- WordPress privacy tools: register exporters with `wp_privacy_personal_data_exporters` and erasers with `wp_privacy_personal_data_erasers` (core Tools > Export/Erase Personal Data uses them) so custom storage participates in requests; add suggested policy text with `wp_add_privacy_policy_content()`.
- Logs and debug output must not contain emails, IPs, tokens or payment data unless needed; define retention and access.
- Third-party transfers (analytics, error trackers, remote fonts, embeds) need a lawful basis; flag transfers that fire before consent where consent is required. This is a privacy concern, not a code-execution vulnerability.
- Public endpoints returning user lists, order data or emails without need are access-control findings (see the access-control reference).

## 7. Checks

| Check | Passing proves | Does not prove |
|---|---|---|
| Secret scanner clean on tree, history, artifact | No matching pattern in scanned scope | No secrets in unscanned places; entropy-free secrets |
| Canary fails the gate | Gate is wired | Rule coverage |
| `wp core verify-checksums` / `wp plugin verify-checksums --all` | Hosted files match | Custom plugins, DB, users |
| Report-Only CSP reports reviewed | Policy compatible with observed traffic | Policy blocks attacks |
| Export and erase a test user through Tools > Export/Erase Personal Data on staging | Custom data participates | Complete data map |

Sources: [core verify-checksums](https://developer.wordpress.org/cli/commands/core/verify-checksums/) | [plugin verify-checksums](https://developer.wordpress.org/cli/commands/plugin/verify-checksums/) | [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html) | [Hardening WordPress](https://developer.wordpress.org/advanced-administration/security/hardening/) | [Personal data exporter](https://developer.wordpress.org/plugins/privacy/adding-the-personal-data-exporter-to-your-plugin/).
