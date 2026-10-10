# Contributing to WordPress DevKit

Thank you for helping make WordPress workflows clearer and more reliable. The most valuable contributions are specific: a wrong or outdated statement with a primary source, a false positive with a minimal example, a missing edge case, or a tutorial step that confused you.

**[Report a problem](#report-a-problem)** · **[Ways to contribute](#ways-to-contribute)** · **[Set up](#set-up)** · **[Edit a skill](#edit-a-skill)** · **[Check your change](#check-your-change)** · **[Pull requests](#pull-requests)**

Please read the [Code of Conduct](CODE_OF_CONDUCT.md). Questions go to [Support](SUPPORT.md); security problems go to the [private reporting form](SECURITY.md), never to a public issue.

## Report a problem

Use the issue forms: [bug report](https://github.com/ehsanenaloo/wordpress-devkit/issues/new?template=bug_report.yml), [skill quality report](https://github.com/ehsanenaloo/wordpress-devkit/issues/new?template=skill_quality.yml) (a wrong, unsafe, outdated or missing answer, or a false alarm) or [feature request](https://github.com/ehsanenaloo/wordpress-devkit/issues/new?template=feature_request.yml).

A good report names the skill or script, the DevKit version and agent client, the WordPress, PHP and WooCommerce versions involved, a minimal example and what you expected. Redact credentials, customer data and private site code. For a guidance error, link the official page that contradicts it.

## Ways to contribute

| You want to | Edit | Include |
|---|---|---|
| Correct or deepen a skill | `src/skills/<name>/` | The primary source, the version gate and, for a review skill, a case that should and should not trigger a finding |
| Fix a script or installer | `scripts/` | A reproduction and a regression test for the original failure |
| Improve a tutorial | `docs/` | Working links and the exact commands you ran |
| Add a skill or command | Open an issue first | The user goal, how it differs from the 20 existing skills and its acceptance cases |

Keep one topic per pull request. A documentation fix does not need an installer change, and a review fix must not turn a review skill into one that edits code.

## Set up

Python 3.10 or newer is the only requirement for the repository tooling. Agent clients and WordPress tooling are optional and only needed for the checks that use them.

```sh
git clone https://github.com/ehsanenaloo/wordpress-devkit.git
cd wordpress-devkit
python scripts/package_product.py --check
python tests/test_skill_content.py
```

## Edit a skill

`src/skills/` is the source of truth. `skills/` is a generated mirror kept as real files so the project works on Windows without symlink privileges. Never edit `skills/` by hand.

```sh
# 1. edit src/skills/<name>/...
python scripts/sync_skills.py
python scripts/package_product.py --check
python tests/test_skill_content.py
```

A skill keeps a lean `SKILL.md` (inputs, workflow, decision points, output format) and moves depth into `references/`, one level deep and linked from `SKILL.md` with a "read when" hint. Use these standards:

- **Verified, dated, sourced.** Every version-sensitive statement is checked against a primary source (developer.wordpress.org, make.wordpress.org, WooCommerce documentation or source, the PHP manual, W3C, the tool's own documentation). Each reference lists its sources and a research date, and marks anything you could not confirm as unverified instead of guessing.
- **Evidence before severity.** Follow the shared `references/engineering-contract.md`. A search match is a lead. Severity follows demonstrated impact, and "insufficient evidence" is a valid outcome that names the missing fact.
- **Review stays read-only.** Implementation guidance belongs to the implementation path and ends with a regression check.
- **Include what looks wrong but is fine** and what looks fine but is wrong. Those lists prevent false positives and false negatives.
- **Correct, minimal examples.** Show secure code (escaping, capabilities, prepared queries) and keep complete PHP examples syntactically valid; the test suite lints them.
- **Plain English.** Imperative, compact, no marketing language, no emoji.

Descriptions in the `SKILL.md` header decide when an agent selects a skill. Name concrete goals and symptoms, and say which sibling skill handles what this one does not.

## Check your change

| Command | What it proves |
|---|---|
| `python scripts/sync_skills.py` | The mirror matches the source. |
| `python scripts/package_product.py --check` | Manifests, links, command and skill coverage and the public file set are valid. |
| `python tests/test_skill_content.py` | Metadata, links, sources and dates, size limits and example syntax. |
| `python scripts/install.py --agent claude --destination <scratch-dir>` | The skills install cleanly. |

Passing checks establish that the package is well formed. They do not establish that the guidance is correct; that depends on the sources you cite and the cases you add. Say in the pull request what you ran and what you could not run.

## Pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/) style messages (`fix(security-review): ...`, `docs: ...`).
- Fill in the pull request template honestly. Do not tick a check you did not run.
- Record user-visible changes in `CHANGELOG.md`.
- Accepted changes are integrated by the maintainer, who also regenerates the catalog and the README skill table.

By contributing you confirm that you wrote the change or have the right to submit it, and you agree that it is licensed under the [MIT License](../LICENSE). See [project history and attribution](../docs/ATTRIBUTION.md).
