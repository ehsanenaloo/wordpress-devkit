# Files, outbound requests and code execution

Researched 2026-10-08. Contents: 1 Uploads | 2 Paths and archives | 3 Outbound requests and SSRF | 4 Redirects | 5 Include, eval and command execution | 6 Filesystem API | 7 Review checks

## 1. Uploads

Questions: who may upload, what is checked, where it lands, what name it gets, and what the web server does with it.

- Use `wp_handle_upload()` (or `media_handle_upload()`) rather than `move_uploaded_file()`. It enforces the PHP upload status, size limit, the extension/MIME allowlist (`get_allowed_mime_types()`, filtered by `upload_mimes`) and unique names. `$overrides['mimes']` narrows the allowed types per feature; `test_form` verifies the request `action` field and is usually set to `false` for REST/handler use, so the handler must carry its own intent check.
- MIME comes from content sniffing (`wp_check_filetype_and_ext()`), not `$_FILES['x']['type']`, which the client controls. Core's check is a policy aid, not malware scanning; polyglot files can still pass. For high-risk features, re-encode images (`wp_get_image_editor()`), reject unexpected types, and store outside the web root or serve through a handler with `Content-Disposition` and `X-Content-Type-Options: nosniff`.
- Executable extensions (`php`, `phtml`, `phar`, `htaccess`, `user.ini`) must never be accepted; adding them through `upload_mimes` is a CRITICAL candidate. `.htaccess`/`web.config` writes by plugins are equally sensitive.
- SVG and HTML-like formats carry script. Accepting SVG from untrusted roles requires sanitization and serving with a restrictive `Content-Security-Policy`; treat core's default refusal of SVG as the baseline.
- Size and count limits, quota per user, and virus scanning policy belong to the abuse review. Filenames: `sanitize_file_name()`; do not trust the client name for the on-disk name. Randomized names reduce guessing but are not authorization.
- Private uploads (invoices, exports): never rely on an unguessable URL in `wp-content/uploads`; serve via an authorizing handler or protected directory, and block directory listing. Verify the web server actually enforces the protection (Apache `.htaccess` is ignored by nginx).
- Uploaded CSV/XML: parse with entity loading disabled (libxml 2.9.0+ disables entity substitution by default; `libxml_disable_entity_loader` is deprecated since PHP 8.0 and is not the fix there; use `libxml_set_external_entity_loader()` or `LIBXML_NO_XXE` on PHP 8.4 with libxml 2.13+ when external entities must be blocked; see [libxml_disable_entity_loader](https://www.php.net/manual/en/function.libxml-disable-entity-loader.php)) and bound size.

## 2. Paths and archives

- Path traversal sinks: `include`, `readfile`, `file_get_contents`, `fopen`, `unlink`, `rename`, `copy`, `ZipArchive::extractTo`, `WP_Filesystem` calls, template loaders, `get_template_part( $_GET['x'] )`.
- Control: allowlist keys mapped to fixed paths. If a path must be built, `realpath()` the result and check it starts with `realpath( $base ) . DIRECTORY_SEPARATOR`. Reject `..`, null bytes, stream wrappers (`php://`, `phar://`, `data:`) and absolute paths. `sanitize_file_name()` removes separators from a name but does not make a whole path safe.
- `phar://` plus a user-controlled path can trigger deserialization of phar metadata on older PHP (the PHP 8.0 migration guide says phar metadata is no longer automatically unserialized, so this is mainly a PHP 7.x concern; [PHP 8.0 incompatible changes](https://www.php.net/manual/en/migration80.incompatible.php)); candidate only when a file function receives user-controlled scheme or path.
- Archives (zip slip): extraction must normalize each entry name and refuse entries that resolve outside the target; `unzip_file()` and `WP_Filesystem` helpers are the core route; custom `ZipArchive::extractTo` on user archives is a lead. Also bound entry count and uncompressed size (zip bombs).
- Temporary files: use `wp_tempnam()`, delete in a `finally`, never place secrets in predictable `uploads` paths.

## 3. Outbound requests and SSRF

Reportable when an attacker controls (part of) the destination and the response, timing or side effect is reachable.

- Prefer `wp_safe_remote_get()` / `wp_safe_remote_post()` / `wp_safe_remote_request()` for any user-influenced URL. They set `reject_unsafe_urls`, which validates the URL and every redirect with `wp_http_validate_url()`: only `http`/`https`, no embedded credentials, resolvable host, and resolved addresses in loopback, private, link-local and other reserved ranges are refused. By default only ports 80, 443 and 8080 are allowed (filter `http_allowed_safe_ports`); `http_request_host_is_external` can relax the host check, so a plugin that returns `true` there silently disables protection (grep for it).
- `wp_remote_get()` without the safe variant, `curl_*`, `file_get_contents( $url )`, `SoapClient`, `simplexml_load_file( $url )`: no SSRF protection. Mark CRITICAL only when internal reach is demonstrated (cloud metadata `169.254.169.254`, localhost services, internal admin panels) or the response is returned to the attacker.
- A hostname regex or `parse_url()` allowlist alone is weak (userinfo tricks like `https://allowed.com@evil.test`, trailing dots, alternative IP encodings, redirects, DNS pointing to private addresses). Compare against an exact allowlist after parsing with `wp_parse_url()`, and still use the safe functions. Whether `wp_safe_remote_*` is safe against DNS rebinding between check and connect is not stated in the WordPress documentation; treat rebinding as an open residual risk and recommend egress network controls.
- Fixed destinations (a payment provider API) are not SSRF. Also check `sslverify => false` (reportable, MITM exposure), missing `timeout`, unbounded `limit_response_size`, and user data or secrets forwarded to third parties (privacy).
- `WP_HTTP_BLOCK_EXTERNAL` and `WP_ACCESSIBLE_HOSTS` change the picture on locked-down sites; a plugin that assumes outbound access should degrade gracefully.
- Webhook receivers and URL previewers (oEmbed-like fetchers, link checkers, image importers, "import from URL") are the common SSRF features. Importers that download remote images must apply the same validation and file checks as uploads.

## 4. Redirects

- `wp_redirect( $_GET['to'] )` is an open redirect (CWE-601): usually WARNING or INFO, higher when it is part of an OAuth/login flow.
- `wp_safe_redirect()` restricts to the site host plus `allowed_redirect_hosts`; `wp_validate_redirect( $url, $fallback )` is the validation step. Both are bypassed by plugins that add broad hosts through the `allowed_redirect_hosts` filter.
- Always `exit` after `wp_redirect()`/`wp_safe_redirect()`; code after it still runs. Mutation after a failed check but before the redirect is a common bug.
- Header injection: user data in `header()` calls; modern PHP rejects newlines in headers, but keep the check.

## 5. Include, eval and command execution

- Dynamic `include`/`require`: allowlist map, never `include $_GET['tpl'] . '.php'`.
- `eval`, `create_function` (removed in PHP 8), `assert` with strings, `preg_replace` with the removed `/e` modifier, `call_user_func( $_GET['fn'] )`, `array_map( $_GET['cb'], ... )`, `$$var` variable variables, and `extract( $_POST )` (variable overwrite, including `$wpdb`-like globals when combined with `include`) are CRITICAL when the argument is request-controlled.
- Shell: `exec`, `shell_exec`, `system`, `passthru`, `proc_open`, `popen`, backticks. Prefer PHP APIs. If unavoidable: fixed binary path, argument array form of `proc_open`, `escapeshellarg()` per argument, no user data in the command name or in flags that change behavior (`--output`, `-o`). Review `wp_filesystem` `FS_METHOD` assumptions and PHP `disable_functions`.
- Template engines and `do_shortcode( $user_string )`: executing attacker-supplied shortcode text allows any registered shortcode; apply it only to content the actor may publish.
- Plugin and theme editors: `DISALLOW_FILE_EDIT` removes the admin editors but does not stop an administrator who can install plugins; `DISALLOW_FILE_MODS` blocks installs and updates but also disables update delivery (conflicts with security patching). Present both as hardening trade-offs, not defects.

## 6. Filesystem API

`WP_Filesystem()` abstracts direct/FTP/SSH writes; direct method writes as the web server user. Code that writes outside `wp_upload_dir()` or the plugin's own data directory, or `chmod 0777`, is a lead. Use `wp_mkdir_p()` and restrictive permissions; put an `index.php`/deny rule in directories holding sensitive generated files, and verify the server honors it.

## 7. Review checks

1. Uploads: role, type allowlist, content check, name policy, storage location, serving headers, execution blocked in the upload directory (verify with an inert fixture in staging only).
2. Paths: key-to-path allowlist or `realpath()` containment; archives checked for traversal and size.
3. Outbound: safe variants for user-influenced URLs, exact destination policy, redirects, TLS verification, timeouts.
4. No request-controlled include, eval, callable or shell argument.
5. Regression: upload `x.php.jpg`, `x.phtml`, polyglot and oversized files are rejected; `../` and `phar://` keys are rejected; `http://127.0.0.1:...`, `http://169.254.169.254/`, and a redirect to an internal address are refused by the feature.

Sources: [wp_safe_remote_get](https://developer.wordpress.org/reference/functions/wp_safe_remote_get/) | [wp_http_validate_url](https://developer.wordpress.org/reference/functions/wp_http_validate_url/) | [wp_handle_upload](https://developer.wordpress.org/reference/functions/wp_handle_upload/) | [OWASP SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
