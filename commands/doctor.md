---
description: Read-only WordPress environment and tooling inventory with JSON and HTML evidence
argument-hint: "[file-or-directory]"
---

Use **wp-devkit-site-audit-and-onboarding** and its `references/doctor.md` workflow.

**Target**: $ARGUMENTS (if empty, use the current working directory).

Run the bundled doctor script against the requested directory and write reports to a separate evidence directory. Default filesystem/tool discovery does not load WordPress. Only use an explicitly selected container and `--trusted-runtime` when the user authorizes executing that trusted site's bootstrap. Report unavailable tooling and skipped runtime checks; do not perform repairs, installs, cache flushes, plugin updates or database writes.
