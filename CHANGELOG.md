# Changelog

All notable changes to this project are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [2.0.1] - 2026-10-09

### Added

- Releases include a native Google Antigravity plugin archive with its own SHA-256 checksum.

## [2.0.0] - 2026-10-09

First public release, under the [MIT License](LICENSE).

### Added

- Support for Google Antigravity, ChatGPT and Codex: a native Antigravity plugin archive, a portable plugin manifest and a local marketplace catalog.
- A skill for WCAG 2.1 and 2.2 A and AA conformance reviews.
- An environment doctor that checks the project layout and tool versions without loading WordPress. It writes JSON and HTML reports.
- Report comparison for the same project, so a missing finding is not mistaken for a verified fix.
- Install, update, check or remove single skills. Status works offline and shows recorded versions and local file changes. Previews, confirmed removal and a recovery tool for interrupted installs are included.
- A guide site with tutorials, one guide for each skill, a searchable command list and a workflow chooser that writes a review request.
- Topic references for every skill. Each lists its sources and research date, so agents load only what a task needs.
- Releases include a ZIP archive with a SHA-256 checksum.
- A contributor guide, security policy, support guide, code of conduct and issue forms.

### Changed

- All 20 skills are now short workflows with topic references. Their descriptions name concrete goals and symptoms. Statements that could not be confirmed are labelled "unverified". The accessibility and WCAG skills now have a clear boundary: component behavior versus conformance assessment.
- **Breaking:** `--replace` and `--uninstall` now refuse to remove local edits or folders that DevKit did not install. Add `--force` to keep the old behavior.
- **Breaking:** Skill sources moved from `claude-skills/` to `src/skills/`, and Codex wrappers from `codex-skills/` to `src/codex/`. Update any tool that reads these paths. Installed skills and their names are unchanged.
- Uninstall and status now include installed skills that a newer version no longer ships.

### Fixed

- Replacing a skill that contains a read-only file no longer fails or leaves a stuck lock. A leftover lock now names the recovery command, and `recover_distribution.py --clear-stale-lock` removes it.
- `install.ps1` accepts comma-separated skill names and paths that end with a backslash. It no longer mistakes the Microsoft Store Python alias for Python.
- Checksum files use Unix line endings on every platform.
- Installation and removal reject destinations inside the source checkout.
- Command argument hints work in strict slash-command loaders.

### Security

- The doctor no longer runs programs found inside the project it inspects, and it no longer writes its reports there.

## [1.0.0] - 2026-06-03

The first version recorded in this repository.

### Added

- Specialist WordPress engineering workflows for Claude Code and Codex with shared canonical references.
- Evidence-based engineering contracts and contextual security and theme reviews.
- Operational workflows for WP-CLI, WordPress Playground and PHPStan adoption.
- Interface-design guidance with responsive, RTL and screenshot verification.
- A physical Claude plugin mirror and Python/PowerShell manual installation entrypoints.
- Distribution regression tests and command migration support.

[Unreleased]: https://github.com/ehsanenaloo/wordpress-devkit/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/ehsanenaloo/wordpress-devkit/releases/tag/v2.0.1
[2.0.0]: https://github.com/ehsanenaloo/wordpress-devkit/releases/tag/v2.0.1
