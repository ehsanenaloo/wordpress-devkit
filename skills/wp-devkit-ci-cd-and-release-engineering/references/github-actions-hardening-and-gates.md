# GitHub Actions: trust boundaries, permissions and merge/release gates

Contents: threat model; triggers and checkout rules; permissions; pinning; script injection; secrets and environments; caches and artifacts across trust levels; gates that really gate; concurrency; reference workflow skeleton; review procedure; false positives.

Researched 2026-10-08. Sources: [GitHub Actions secure use reference](https://docs.github.com/en/actions/reference/security/secure-use), [events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), [troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks), [runner images](https://github.com/actions/runner-images), [artifact attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds), [dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching). Versions quoted in examples are placeholders: look up the latest release and its commit SHA of each action online before editing a workflow.

## Threat model in one paragraph

Anyone who can get text or code into a job (fork PR, issue title, branch name, dependency script, third-party action, cache entry, artifact) can run commands with that job's token and secrets. The defense is separating jobs by trust: unprivileged jobs run untrusted code with no secrets and a read-only token; privileged jobs run only reviewed code from protected refs.

## Triggers and checkout rules

| Trigger | Runs what | Secrets / token | Rule |
|---|---|---|---|
| `pull_request` (fork) | Merge ref of the PR | No secrets; `GITHUB_TOKEN` read-only | Safe place to run tests and linters on untrusted code |
| `pull_request_target` | Workflow from the base repo default branch | Secrets and write token available, even for forks | Never check out or execute PR head code (build, `npm install`, `composer install`, test scripts). Use only to label or comment, with no PR code executed |
| `workflow_run` | Default-branch workflow, after another run | Secrets and write token available | Treat the triggering run's artifacts as untrusted input; do not execute them; validate before use |
| `push` to protected branch / tag | The pushed commit | Secrets per environment | The release path; require branch/tag protection |
| `workflow_dispatch`, `schedule` | Default-branch workflow | Secrets | Fine for maintenance; inputs are user text (see injection) |

- Dependabot PRs are treated like fork PRs (no secrets) unless secrets are added as Dependabot secrets.
- Events caused by `GITHUB_TOKEN` do not start new workflow runs (except `workflow_dispatch` and `repository_dispatch`). A release created by a workflow will not trigger a `release` workflow unless a PAT or app token is used; design the chain explicitly.
- `actions/checkout` persists the auth token for later git commands by default (in `.git/config` up to v5; from v6 in a separate file under `$RUNNER_TEMP`, per the action README). Set `persist-credentials: false` unless the job pushes. Checkout v7 also refuses fork PR code under `pull_request_target` or `workflow_run` unless `allow-unsafe-pr-checkout: true` is set; do not set it.
- Merge queues need the `merge_group` event in every workflow that provides a required check; otherwise the check never reports and the merge blocks.

## Permissions

Declare `permissions: {}` or `permissions: { contents: read }` at workflow level and widen per job:

```yaml
permissions:
  contents: read
jobs:
  release:
    permissions:
      contents: write        # create release
      id-token: write        # OIDC / attestations
      attestations: write
```

An unspecified `permissions` key inherits the repository default, which may be read-write in older repositories. Check Settings > Actions > General for the default and the "allow Actions to create and approve pull requests" switch.

## Pinning and supply chain

- Pin third-party actions to a full-length commit SHA (the only immutable reference) and keep a version comment: `uses: actions/checkout@<40-hex-sha> # v7.0.1`. Verify the SHA belongs to the action's repository, not a fork. First-party `actions/*` tags are a lower risk; a policy should still say which.
- Enable Dependabot version updates for `github-actions` so pins are updated by reviewable PRs. Use dependency review on PRs. Enforce SHA pinning with an organization or repository policy where available.
- Require `CODEOWNERS` review for `.github/workflows/**` and for release scripts.
- Restrict to the action allow-list the organization maintains. Prefer shell steps over a third-party action for simple things on jobs that hold deploy credentials.
- Prefer lockfile installs: `npm ci`, `composer install` with `composer.lock`. Do not run `npm install` or `composer update` in a release job.

## Script injection

Never interpolate untrusted context directly into `run:`.

```yaml
# Vulnerable: title is shell-interpreted
- run: echo "${{ github.event.pull_request.title }}"

# Safe: pass through an environment variable and quote it
- env:
    TITLE: ${{ github.event.pull_request.title }}
  run: echo "$TITLE"
```

Untrusted fields include PR/issue titles and bodies, branch names (`github.head_ref`), commit messages, author names, `workflow_dispatch` inputs, and artifact contents. Also check `actions/github-script` bodies and composite action inputs. A pattern match for `${{ github.event` in `run:` is a lead; judge it by who controls the value and whether the job has secrets.

## Secrets, environments, OIDC

- Anyone with write access to the repository can read its repository secrets through a workflow. Secrets that can publish (WordPress.org SVN password, deploy keys, package tokens) belong to an environment with required reviewers and a branch/tag deployment rule, not to repository-level secrets.
- One secret per value; structured blobs (JSON/YAML) defeat masking. Mask derived values with `::add-mask::`. A secret printed to a log is rotated, not just deleted.
- Prefer OpenID Connect to long-lived cloud keys where the target supports it.
- Separate staging and production credentials; a PR or preview job must not reach production secrets.
- Self-hosted runners: avoid for public repos; use ephemeral, isolated runners; never persist state or credentials between jobs.

## Caches and artifacts across trust levels

- Cache scope (GitHub dependency-caching reference): a run restores caches from its own ref, the base branch for pull requests, and the default branch; caches created by a pull request run are scoped to its merge ref and cannot be restored by the base branch or other PRs, and runs cannot restore caches from tag refs. The residual risk is a privileged job on the default branch (`pull_request_target`, `workflow_run`, a push after merge) that runs untrusted or unreviewed code and then saves a cache. Key release caches by lockfile hash and prefer no cache in release jobs; never put secrets in cached paths, because anyone who can open a PR can read base-branch caches.
- `actions/upload-artifact` v4+ artifacts are immutable and names must be unique per run; hidden files are excluded unless `include-hidden-files: true` (check `.distignore`d files are not accidentally shipped or dropped). Use `if-no-files-found: error` for release archives. The `artifact-digest` output records the SHA-256 for later verification. v3 of the artifact actions is deprecated.
- A job that downloads an artifact built by another job must verify what it receives (digest or attestation) before publishing.

## Gates that actually gate

- Required status checks are matched by name (GitHub: if a check and a commit status share a name, both must pass). A workflow filtered out by `paths:` or branch filters never reports and leaves the PR "waiting for status"; GitHub advises against path-filtering workflows that are required. A job skipped by `if:` counts as passing for the required check, so a skipped test job is a bypass. Use one aggregate job (`needs:` all gates, `if: always()`, fail when any result is `failure`, `cancelled` or `skipped` unexpectedly) as the single required check.
- Required checks must have completed successfully in the repository during the past seven days to be selectable. Rename a job and the rule silently stops matching until updated.
- Release jobs depend (`needs`) on the verification jobs and consume their artifact; they must not rebuild.
- Do not mark steps `continue-on-error: true` on a gate. Do not use `|| true`. A skipped gate or a loosened baseline needs a stated owner and expiry, per the engineering contract.

## Concurrency and idempotence

```yaml
concurrency:
  group: release-${{ github.ref }}
  cancel-in-progress: false      # never cancel a release mid-publish
```

CI on PRs can cancel superseded runs; release and deploy must not. Rerunning a release job for the same tag must be safe: check "does this version already exist on the target" and stop or no-op.

## Reference skeleton (verification then promotion)

```yaml
name: ci
on:
  pull_request:
  merge_group:
  push:
    branches: [main]
    tags: ['v*']
permissions:
  contents: read
jobs:
  verify:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@<sha> # v7.0.1
        with: { persist-credentials: false }
      - uses: shivammathur/setup-php@<sha> # 2.40.0
        with: { php-version: '8.3', tools: composer }
      - run: composer install --no-interaction --prefer-dist
      - run: composer lint && composer analyse && composer test
  gate:
    if: always()
    needs: [verify]
    runs-on: ubuntu-24.04
    steps:
      - run: test "${{ needs.verify.result }}" = "success"
  package:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: [gate]
    runs-on: ubuntu-24.04
    steps: [] # build once, inspect, upload-artifact (see packaging reference)
```

Look up which Ubuntu version `ubuntu-latest` maps to in the runner images list, and pin the label you tested so image migrations are a change you make.

## Review procedure (read-only)

1. List triggers, `permissions`, `uses:` refs, `run:` interpolations, secrets and environments per workflow.
2. For each privileged workflow decide whose code it runs. Trace PR-controlled values to `run:` and `with:`.
3. For each required check, confirm which job reports it and whether a skip or path filter can bypass it.
4. Trace the artifact from build to publish; confirm one build, a recorded digest, and the same bytes at promotion.
5. Report findings with evidence; mark gaps (branch protection and environment settings live in the GitHub UI and are not visible in the repository) as unverified.

## Looks wrong but is fine

- `pull_request_target` that only applies labels, never checks out PR code, and has minimal permissions.
- `actions/*` first-party actions on a tag when policy allows it.
- `secrets.GITHUB_TOKEN` usage with narrow job permissions.
- `workflow_dispatch` input used only through `env:` and quoted.
- `if: always()` on a cleanup or aggregate job.
