---
name: wp-devkit-ci-cd-and-release-engineering
description: Build, debug or review GitHub Actions CI/CD for WordPress plugins, themes and sites: workflow trust and secrets, PHP/WP test matrices, merge gates, release zips, version drift, WordPress.org SVN delivery, host deploys and rollback. Writing the tests themselves belongs to test strategy.
---

# Trusted artifacts and release recovery

Read `references/engineering-contract.md` first. Review requests stay read-only: assess, explain and recommend without editing workflows, running pipelines, building or publishing releases, pushing tags, committing to SVN, or touching deploy targets and secrets. Use the implementation path only when the request authorizes changes. Development does not imply publication.

## Inputs to establish

CI provider and workflow files; branch and tag protection, required checks, environments and reviewers (these live in repository settings and are often not visible: ask or mark unverified); declared support policy (`Requires at least`, `Requires PHP`, `Tested up to`); lockfiles and toolchain; packaging method and exclusion list; release channels (WordPress.org, GitHub release, host deploy, Composer); credential locations; data migrations and the rollback limit.

## Route the task

| Symptom or goal | Read |
|---|---|
| Fork PR risk, `pull_request_target`, script injection, secrets, token permissions, unpinned actions, skipped required checks, concurrency | `references/github-actions-hardening-and-gates.md` |
| Which PHP/WP versions to test, flaky or missing gates, baselines, wp-env or service containers, Plugin Check, audits | `references/test-matrix-and-quality-gates.md` |
| Zip contents wrong, version drift, rebuild-on-release, digest or provenance, dependency collisions, smoke install | `references/packaging-and-artifact-verification.md` |
| WordPress.org SVN, readme rules, tag workflow, propagation, rollback, host deploy, migrations | `references/wordpress-org-release-and-rollback.md` |

Hand off: authoring tests and fixtures to `wp-devkit-test-strategy`; PHPStan configuration to `wp-devkit-phpstan-review`; WP-CLI runbooks to `wp-devkit-wpcli-and-ops`; plugin activation, upgrade and uninstall code to `wp-devkit-plugin-development`; data upgrade logic to `wp-devkit-migration-upgrade-review`; vulnerabilities in the shipped code to `wp-devkit-security-review`.

## Code Review Workflow

1. Trace events, identities and privileges from checkout to release. Decide for each privileged job whose code and whose text it executes.
2. Follow required gates: which job reports each check, whether a path filter, `if:` skip, `continue-on-error` or `|| true` lets a failure pass, and whether the release job depends on the gates.
3. Check whether the tested bytes are the promoted bytes: one build, recorded digest, no rebuild at publish. Inspect build inputs (lockfile installs, pinned toolchain).
4. Compare plugin header, readme `Stable tag`, tag, changelog and constants for the intended channel. Compare support-policy headers with what the matrix proves.
5. Check recovery: previous good artifact, who can roll back, migration reversibility, data restore, communication. A rollback keyword is not a tested path.
6. Report what is established from the repository and what depends on settings you could not see (branch rules, environments, secret scopes).

Insufficient evidence is a valid outcome; name the setting or run that would settle it. Do not downgrade a reachable secret exposure because the attacker needs a fork PR; do not escalate a pattern match without a reachable path.

## Implementation workflow

1. State the change, the pipeline stage it touches, and how it will be proven (a deliberate failing fixture and a passing run).
2. Keep permissions minimal per job; pin third-party actions to full SHAs with a version comment; interpolate untrusted values only through `env:`.
3. Make verification, packaging and promotion separate stages with `needs:`; promote only the verified artifact.
4. Never regenerate baselines, widen ignores or mark gates non-blocking to get green (contract rule 8).
5. Run the acceptance checks locally where possible (`actionlint`, dry runs, packaging inspection); report unexecuted checks. Publishing, tagging and deployment need their own task scope and approval.

## Search Patterns for Quick Detection

Read-only leads from the project root; matches are candidates, not findings. Exit 0 = match, 1 = none, 2 = error.

```sh
rg -n -g '*.{yml,yaml}' -g '!vendor' -g '!node_modules' -e 'pull_request_target|workflow_run|permissions:|persist-credentials|id-token:|environment:|concurrency:' .github
rg -n -g '*.{yml,yaml}' -e '\$\{\{ *github\.(event|head_ref)[^}]*\}\}' .github
rg -n -g '*.{yml,yaml}' -e 'uses: *[^@ ]+@(?![0-9a-f]{40}\b)' --pcre2 .github
rg -n -g '*.{yml,yaml,sh,json}' -e 'continue-on-error|\|\| *true|npm install|composer update|curl .*\| *(ba)?sh|--no-verify|baseline' .
rg -n -g '*.{php,txt,yml,yaml,sh,json}' -e 'Stable tag:|Version:|Tested up to:|Requires PHP:|svn (cp|commit|ci)|dist-archive|distignore|upload-artifact|attest' .
```

Interpolation of a `github.event` value is dangerous only when it reaches a shell or script step in a job that has secrets or a write token. An unpinned first-party action may be policy-compliant. No match proves nothing: reusable workflows, composite actions and other CI providers hide logic.

## Acceptance checks

- `actionlint` (and `zizmor` or an equivalent workflow security linter if the project uses one) reports no errors; record version and exit status.
- Broken-fixture run: a syntax error, failing test or vulnerable lockfile entry turns the correct job red; the aggregate required check is red.
- Fork PR: no secrets, read-only token, no deploy job runs.
- Build once: the artifact digest at publish equals the digest recorded in the build job; rerun of the same tag is safe.
- Archive inspection: top-level folder equals the slug, required runtime files present, forbidden paths absent; version metadata consistent; smoke install and upgrade pass on a disposable site.
- WordPress.org: dry run lists the expected file set; Plugin Check passes with narrow, justified ignores; after the propagation window the live version equals the tag.
- Rollback rehearsal on staging: restore the previous artifact and, where data changed, the backup.

A pass proves the exercised pipeline paths, matrix cells and artifact. It does not prove repository settings you did not see, production host behavior, WordPress.org review approval, or absence of vulnerabilities in the shipped code.

## Output Format

Review: result and reviewed scope first. Each confirmed finding: severity per the contract, file:line, actor, trigger, reachable path, impact, confidence, minimal fix, regression check. Candidates and unverified settings in a separate list.

Implementation: changed workflow/files, stage affected, commands run with exit status, evidence of the failing-then-passing proof, unexecuted checks, residual risk, rollback plan.

## References

- `references/github-actions-hardening-and-gates.md`: read for trust boundaries, permissions, pinning, injection, secrets, gates.
- `references/test-matrix-and-quality-gates.md`: read for matrix derivation, gate catalog, runtimes, baselines.
- `references/packaging-and-artifact-verification.md`: read for deterministic builds, archive inspection, version checks, provenance.
- `references/wordpress-org-release-and-rollback.md`: read for SVN/readme mechanics, tag workflow, deploy and rollback.
