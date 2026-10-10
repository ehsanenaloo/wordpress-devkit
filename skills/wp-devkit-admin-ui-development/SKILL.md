---
name: wp-devkit-admin-ui-development
description: Build, debug or review WordPress admin settings pages, list tables, custom save handlers and editor-side tools. Use for save-says-success-but-unchanged, role/capability gaps, scoped assets, notices, and accessible loading/error states; not REST route design.
---

# Administrative screens and save behavior

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without edits, mutations or untrusted runtime execution. Use the implementation path only when the request authorizes changes.

## Inputs and scope

Screen ID or menu slug, actor role and capability, option/meta owner, save path (Settings API, `admin-post`, AJAX, REST), rendered form and save request, asset handles, target WordPress version, single site or multisite.

Inspect project evidence before asking. State material assumptions. Ask only what changes the decision or execution boundary. Follow existing architecture, option names, stored types and UI conventions.

## Boundaries with sibling skills

REST route design and auth go to `wp-devkit-rest-api-development`; plugin bootstrap and storage to `wp-devkit-plugin-development`; block editor blocks to `wp-devkit-block-development`; formal WCAG evidence to `wp-devkit-wcag-review`; code-level accessibility defects to `wp-devkit-accessibility-review`; visual design direction to `wp-devkit-ui-design`. This skill owns the admin screen, its save boundary and its interaction states.

## Code Review Workflow

1. Follow screen registration and each write handler separately. Menu visibility and direct-URL access control are not enforcement at `admin-post`, AJAX or REST write boundaries.
2. Trace the save path: option group, registered setting, posted field names, sanitizer, validation, nonce mechanism, capability. Confirm previous valid data survives a failed submission.
3. Trace assets to the exact screen (hook suffix) and their dependencies. Prefer installed WordPress components; do not add a parallel UI framework for a small change.
4. Assess labels, errors, pending/success/empty states, focus management and announcements. Gather keyboard evidence; describe duplicate-submit verification without making live writes.
5. Report the screen/save boundary, confirmed behavior and the scoped correction with permission and interaction checks. Leave options, metadata and assets unchanged during review.
6. Classify per the contract; pattern hits remain candidates; use `insufficient evidence` when the save path, role set or version is unknown.

Read `references/admin-ui-development-workbook.md` for symptom triage, worked decisions, benign look-alikes and verification. Load topic references only when in scope:

- `references/settings-and-save-flows.md`: read for the Settings API lifecycle, sanitize vs validate, `options.php` capability, `admin-post`/AJAX handlers, REST-backed settings, secrets.
- `references/screens-assets-and-lists.md`: read for menus and access, hook-suffix scoping, enqueue arguments, translations, React/components, `WP_List_Table`, notices, 7.0 admin changes.
- `references/admin-accessibility-and-verification.md`: read for labels, status announcements, focus, WCAG 2.2 criteria that apply, and the Playwright/axe/role-matrix verification method.

## Implementation workflow

1. Name the screen, role and save path; state the expected behavior and smallest boundary before editing.
2. Use the Settings API when the data is a plain option; otherwise a handler with capability check first, intent check second, validation third, PRG redirect last. Keep the stored shape stable.
3. Scope assets to the screen; take dependencies from the generated asset file; namespace CSS.
4. Provide persisted-success, error, pending and empty states with accessible announcements; preserve input and prior valid data on failure.
5. Write the failing role/interaction test first, then the fix. Queue long work instead of blocking the request.
6. Report unavailable checks as unexecuted. Deployment and live data changes need their own scope.

## Search Patterns for Quick Detection

Run only the relevant group from the first-party root; narrow `.`. Commands read files and never load WordPress. Hits are leads, not findings; no hit proves nothing (helpers, classes and generated markup hide matches). Exit 0 match, 1 none, 2 error.

```sh
# Screens and capability
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'add_(menu|submenu|options|management|theme|users)_page|current_user_can|map_meta_cap|option_page_capability' .
# Settings API
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'register_setting|settings_fields|do_settings_sections|add_settings_(section|field|error)|settings_errors|sanitize_callback|options\.php' .
# Custom submit paths
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'admin_post_|wp_ajax_|check_admin_referer|check_ajax_referer|wp_verify_nonce|wp_nonce_(field|url)' .
# Scoped assets
rg -n -g '*.php' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'admin_enqueue_scripts|get_current_screen|hook_suffix|wp_enqueue_(script|style)|wp_set_script_translations|wp_add_inline_script' .
# Feedback and accessible controls
rg -n -g '*.{php,js,jsx,ts,tsx,html}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'admin_notices|wp_admin_notice|a11y\.speak|aria-(live|describedby|invalid)|role="(alert|status)"|<label|<button' .
# State and output boundaries
rg -n -g '*.{php,js,jsx,ts,tsx}' -g '!**/{vendor,node_modules,build,dist,coverage,backups}/**' -e 'update_(option|user_meta)|esc_(html|attr|url|textarea)|wp_kses|innerHTML|dangerouslySetInnerHTML' .
```

Read the match context; confirm reachability and what core already enforces (for example `settings_fields()` supplies a group nonce) before reporting.

## Acceptance checks

Role matrix (administrator, lowest role with menu access, role without capability sending the request directly) on the real handlers with stored state asserted afterwards; invalid and partial input keeps prior values; keyboard-only run, double submit and failed-request path; unrelated admin screens unchanged; axe on each UI state plus a manual screen reader pass of the primary task; PHPCS (WordPress standards) and JS lint. A pass proves the tested roles, browser, viewport and WordPress version; it does not prove other roles, multisite, browsers or assistive technology.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: `file:line`, actor, trigger, reachable path, impact, confidence, severity (per contract), minimal fix, regression. Candidates and missing evidence separate. Implementation: changed boundaries, role/interaction checks with results and exit status, unexecuted checks, residual risk.
