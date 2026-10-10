# Security Policy

## Supported versions

Security fixes are made to the latest release published on the [Releases page](https://github.com/ehsanenaloo/wordpress-devkit/releases). Older versions are not patched; please update before you report a problem.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Report it privately with GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Describe the problem and how to reproduce it.

Direct link: <https://github.com/ehsanenaloo/wordpress-devkit/security/advisories/new>

Helpful details:

- the DevKit version and agent client,
- the affected component (a skill, command, installer, doctor/report script or packaging file),
- clear reproduction steps using synthetic data,
- the impact you believe it has.

Please do not include real credentials, customer data or private site code in a report.

## What to expect

This is a volunteer-maintained project, so response times are best effort. The maintainer will acknowledge a report, assess it, work on a fix for confirmed issues and credit you in the release notes if you wish. Please allow time for a fix before disclosing details publicly.

## Scope

In scope:

- code in this repository that runs on a user's machine: the installer, recovery, doctor, report and packaging scripts,
- instructions in a skill or command that could cause an agent to run destructive, untrusted or exfiltrating actions without clear user authorisation,
- path traversal, unsafe overwrite or unsafe archive handling during install or recovery,
- leakage of secrets or personal data by doctor or evidence reports.

Out of scope:

- vulnerabilities in WordPress, WooCommerce, PHP, Claude, Codex, ChatGPT or Antigravity themselves,
- findings that depend on a modified copy of DevKit,
- the accuracy of a review result for a specific project (report those as a skill quality issue instead),
- social engineering.

## Design notes relevant to security researchers

- DevKit is an instruction pack with local helper scripts. It ships no server, no telemetry and no network service.
- Review skills are read-only by contract; implementation needs an explicit request.
- Installer and recovery stage replacements and roll back on caught failure; links and malformed sources are rejected.
- Doctor and evidence reports redact secret values and mark unavailable checks as unavailable.
