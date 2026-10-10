"""Static quality gates for every canonical skill.

These checks catch structural and mechanical defects: broken references, orphaned or oversized files,
unparseable examples, missing source dates, private paths and drifting shared contracts. They cannot
prove that the guidance is correct; behavioural evidence comes from the evaluation suites.
"""
import _bootstrap  # noqa: F401 - adds scripts/ to sys.path
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / 'src/skills'
FRONTMATTER = re.compile(r'\A---\nname: ([a-z0-9-]+)\ndescription: "?(.+?)"?\n---\n')
LINK = re.compile(r'`(references/[A-Za-z0-9_./-]+\.md)`|\]\((references/[A-Za-z0-9_./-]+\.md)(?:#[^)]*)?\)')
FENCE = re.compile(r'^```([A-Za-z0-9_+-]*)[^\n]*\n(.*?)^```[ \t]*$', re.M | re.S)
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿]')
PRIVATE = re.compile(r'[A-Za-z]:\\Users\\|/home/[a-z]+/|/Users/[a-z]+/')
SECRET = re.compile(r'AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-[A-Za-z0-9]{32,}')
DATE = re.compile(r'\b20\d\d-\d\d-\d\d\b')
URL = re.compile(r'https://[^\s)>\]]+')

PHP = shutil.which('php')


def skill_dirs():
    return sorted(path for path in SKILLS.iterdir() if path.is_dir())


def markdown_files(skill):
    return sorted(skill.rglob('*.md'))


class SkillContentTests(unittest.TestCase):
    def test_metadata_is_valid_unique_and_portable(self):
        descriptions = {}
        for skill in skill_dirs():
            text = (skill / 'SKILL.md').read_text(encoding='utf-8')
            match = FRONTMATTER.match(text)
            if match is None:
                self.fail(f'{skill.name}: invalid frontmatter')
            self.assertEqual(match[1], skill.name)
            description = match[2]
            self.assertTrue(skill.name.startswith('wp-devkit-'))
            self.assertLessEqual(len(description), 1024, f'{skill.name}: description exceeds the client limit')
            self.assertGreaterEqual(len(description), 60, f'{skill.name}: description is too vague to select')
            self.assertNotIn('<', description, f'{skill.name}: XML-like text in description')
            self.assertNotIn(description, descriptions, f'{skill.name}: duplicate description of {descriptions.get(description)}')
            descriptions[description] = skill.name

    def test_frontmatter_descriptions_are_strict_yaml(self):
        """Antigravity parses frontmatter as strict YAML: a plain scalar with ': ' or ' #' drops the skill."""
        for skill in skill_dirs():
            text = (skill / 'SKILL.md').read_text(encoding='utf-8')
            raw = re.match(r'\A---\nname: [^\n]+\ndescription: ([^\n]+)\n---\n', text)
            self.assertIsNotNone(raw, f'{skill.name}: invalid frontmatter')
            value = raw[1]
            if value.startswith('"'):
                self.assertTrue(value.endswith('"') and len(value) > 1, f'{skill.name}: unclosed quote')
                self.assertNotRegex(value[1:-1], r'(?<!\\)"', f'{skill.name}: unescaped quote in description')
            else:
                self.assertNotRegex(value, r': | #|^[\[\]{}&*!|>\'%@`]', f'{skill.name}: quote the description')

    def test_entrypoints_stay_lean(self):
        for skill in skill_dirs():
            lines = (skill / 'SKILL.md').read_text(encoding='utf-8').count('\n')
            self.assertLessEqual(lines, 220, f'{skill.name}: SKILL.md is {lines} lines; move detail into references/')

    def test_selected_references_exist_and_none_are_orphaned(self):
        for skill in skill_dirs():
            entry = (skill / 'SKILL.md').read_text(encoding='utf-8')
            selected = {a or b for a, b in LINK.findall(entry)}
            self.assertIn('references/engineering-contract.md', selected, f'{skill.name}: contract is not selected')
            for target in selected:
                self.assertTrue((skill / target).is_file(), f'{skill.name}: missing {target}')
            reachable = set(selected)
            queue = list(selected)
            while queue:
                current = queue.pop()
                text = (skill / current).read_text(encoding='utf-8')
                for a, b in LINK.findall(text):
                    nested = a or b
                    if nested not in reachable and (skill / nested).is_file():
                        reachable.add(nested)
                        queue.append(nested)
                for relative in re.findall(r'\]\(([A-Za-z0-9_.-]+\.md)(?:#[^)]*)?\)', text):
                    nested = 'references/' + relative
                    if nested not in reachable and (skill / nested).is_file():
                        reachable.add(nested)
                        queue.append(nested)
            actual = {path.relative_to(skill).as_posix() for path in (skill / 'references').glob('**/*.md')}
            self.assertFalse(actual - reachable, f'{skill.name}: orphaned references {sorted(actual - reachable)}')

    def test_long_references_have_contents_and_are_bounded(self):
        for skill in skill_dirs():
            for path in (skill / 'references').glob('**/*.md'):
                if path.name == 'engineering-contract.md':
                    continue
                text = path.read_text(encoding='utf-8')
                lines = text.count('\n')
                label = path.relative_to(SKILLS).as_posix()
                self.assertLessEqual(lines, 600, f'{label}: {lines} lines; split by topic')
                if lines > 100:
                    head = '\n'.join(text.splitlines()[:30]).lower()
                    self.assertRegex(head, r'contents|table of contents|in this file|jump to',
                                     f'{label}: add a contents list to the top')

    def test_references_record_primary_sources_and_a_research_date(self):
        for skill in skill_dirs():
            for path in (skill / 'references').glob('**/*.md'):
                if path.name == 'engineering-contract.md':
                    continue
                text = path.read_text(encoding='utf-8')
                label = path.relative_to(SKILLS).as_posix()
                self.assertTrue(URL.search(text), f'{label}: cite at least one primary source URL')
                self.assertTrue(DATE.search(text), f'{label}: record the research date (YYYY-MM-DD)')

    def test_shared_contract_is_identical_except_for_the_wcag_specialization(self):
        specialised = {'wp-devkit-wcag-review'}
        contracts = {skill.name: (skill / 'references/engineering-contract.md').read_bytes() for skill in skill_dirs()}
        general = {name: body for name, body in contracts.items() if name not in specialised}
        self.assertEqual(len(set(general.values())), 1, 'engineering-contract.md differs between general skills')
        for name in specialised:
            self.assertNotEqual(contracts[name], next(iter(general.values())), f'{name}: remove the specialization exception')

    def test_no_private_paths_secrets_markers_or_emoji(self):
        for skill in skill_dirs():
            for path in skill.rglob('*'):
                if not path.is_file() or path.suffix not in {'.md', '.yaml', '.yml', '.json', '.py', '.php'}:
                    continue
                text = path.read_text(encoding='utf-8')
                label = path.relative_to(SKILLS).as_posix()
                self.assertFalse(PRIVATE.search(text), f'{label}: local path or account name')
                self.assertFalse(SECRET.search(text), f'{label}: looks like a real credential')
                self.assertFalse(re.search(r'\b(TODO|FIXME|XXX|lorem ipsum)\b', text), f'{label}: unfinished marker')
                if path.suffix == '.md':
                    self.assertFalse(EMOJI.search(text), f'{label}: emoji in technical guidance')

    def test_review_boundary_is_explicit(self):
        for skill in skill_dirs():
            text = (skill / 'SKILL.md').read_text(encoding='utf-8').lower()
            self.assertRegex(text, r'read-only|review requests|implementation', f'{skill.name}: state the review/implementation boundary')

    def test_structured_examples_parse(self):
        for skill in skill_dirs():
            for path in markdown_files(skill):
                text = path.read_text(encoding='utf-8')
                label = path.relative_to(SKILLS).as_posix()
                for language, body in FENCE.findall(text):
                    if language == 'json' and '...' not in body and '//' not in body:
                        try:
                            json.loads(body)
                        except ValueError as error:
                            self.fail(f'{label}: invalid JSON example ({error})')
                    elif language in {'python', 'py'}:
                        try:
                            ast.parse(body)
                        except SyntaxError as error:
                            self.fail(f'{label}: invalid Python example ({error})')

    @unittest.skipUnless(PHP, 'PHP is not installed; syntax of PHP examples is checked in CI')
    def test_complete_php_examples_have_valid_syntax(self):
        for skill in skill_dirs():
            for path in markdown_files(skill):
                label = path.relative_to(SKILLS).as_posix()
                for language, body in FENCE.findall(path.read_text(encoding='utf-8')):
                    if language != 'php' or not body.lstrip().startswith('<?php'):
                        continue
                    with tempfile.TemporaryDirectory() as directory:
                        sample = Path(directory) / 'sample.php'
                        sample.write_text(body, encoding='utf-8')
                        result = subprocess.run([str(PHP), '-l', str(sample)], capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, f'{label}: {result.stdout}{result.stderr}')


if __name__ == '__main__':
    unittest.main()
