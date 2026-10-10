## Summary

<!-- What does this change and why? Keep it to one topic. -->

## Related issue

<!-- For example "Fixes #123". For a small typo, write "None". -->

## Type of change

- [ ] Skill content (workflow, reference or description)
- [ ] Command
- [ ] Installer, doctor or scripts
- [ ] Documentation
- [ ] Maintenance or CI

## How I tested it

<!-- Say what you ran and what you saw. For skill changes, name the case you used to compare behaviour before and after.
Do not claim a check you did not execute. -->

## Checklist

- [ ] I edited the canonical source in `src/skills/`, then ran `python scripts/sync_skills.py`
- [ ] `python scripts/package_product.py --check` and `python tests/test_skill_content.py` pass
- [ ] I added or updated a case (a defect, a benign look-alike or insufficient evidence), or I explained why the change cannot be tested
- [ ] Version-sensitive guidance is backed by a primary source (linked in the reference)
- [ ] Review skills stay read-only; implementation steps stay in the implementation path
- [ ] No secrets, customer data or private site code in the diff
- [ ] User-visible changes are recorded in `CHANGELOG.md`
- [ ] I wrote this change or I have the right to submit it under the MIT License
