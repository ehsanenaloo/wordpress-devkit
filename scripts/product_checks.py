"""Checks shared by the private source export and the public product repository.

Everything here works on a mapping of relative POSIX paths to bytes, so the same rules validate the
snapshot built from the development repository and the tree checked out from the public repository.
"""
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import unquote
import zipfile

# Roots that must never appear in a product tree. The publication manifest is the allowlist; this set is a
# second, independent guard against accidental inclusion.
FORBIDDEN_ROOTS = {'.git', 'technical-docs', 'build', 'guides', 'AGENTS.md', 'CLAUDE.md'}
FORBIDDEN_PREFIXES = ('tests/evals', 'src/publication', 'technical-docs/internal')
# Tests that are part of the product so the public repository can verify itself.
PUBLIC_TEST_FILES = {'tests/test_skill_content.py', 'tests/_bootstrap.py'}
# Paths that belong in the repository but not in the installable archive.
ARCHIVE_EXCLUDED_ROOTS = {'.github', 'tests'}
ARCHIVE_EXCLUDED_FILES = {'.editorconfig', '.gitattributes', '.gitignore'}


# Claude-specific instruction, configuration and memory files stay in the private development repository.
# `.claude-plugin/` is a product directory and is deliberately not matched.
CLAUDE_PRIVATE_DIRECTORIES = {'.claude'}
CLAUDE_PRIVATE_FILES = {'claude.md', 'claude.local.md'}
JUNK_NAMES = {'.ds_store', 'thumbs.db', 'desktop.ini'}
JUNK_SUFFIXES = ('.pem', '.key', '.orig', '.rej', '.bak', '.swp', '.p12', '.pfx')


def is_private_path(name):
    parts = PurePosixPath(name).parts
    if parts[0].lower() in {root.lower() for root in FORBIDDEN_ROOTS} or any(name == prefix or name.startswith(prefix + '/') for prefix in FORBIDDEN_PREFIXES):
        return True
    if parts[0] == 'tests' and name not in PUBLIC_TEST_FILES:
        return True
    leaf = parts[-1].lower()
    if leaf in CLAUDE_PRIVATE_FILES or any(part.lower() in CLAUDE_PRIVATE_DIRECTORIES for part in parts):
        return True
    if leaf in JUNK_NAMES or leaf.startswith('.env') or leaf.startswith('id_rsa') or leaf.endswith(JUNK_SUFFIXES):
        return True
    return any(part in {'.git', '__pycache__'} for part in parts) or name.endswith('.pyc')


class AssetLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for name, value in attrs if name in {'href', 'src'} and value)


def validate_snapshot(files):
    required = {'README.md', '.github/CONTRIBUTING.md', '.github/SECURITY.md', 'LICENSE', '.claude-plugin/plugin.json', 'plugin.json',
                'scripts/install.py', 'scripts/distribution.py', 'docs/index.html',
                '.agents/plugins/marketplace.json'}
    if required - files.keys():
        raise ValueError(f'Incomplete publication: {sorted(required - files.keys())}')
    portable = json.loads(files['plugin.json'].decode('utf-8'))
    claude = json.loads(files['.claude-plugin/plugin.json'].decode('utf-8'))
    if not isinstance(portable, dict) or not isinstance(claude, dict):
        raise ValueError('Plugin manifests must be objects.')
    if portable.get('$schema') != 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':
        raise ValueError('Invalid portable plugin schema.')
    if any(portable.get(field) != claude.get(field) for field in ('name', 'version', 'author', 'license')):
        raise ValueError('Portable and Claude plugin identity differ.')
    marketplace = json.loads(files['.agents/plugins/marketplace.json'].decode('utf-8'))
    expected_entry = {
        'name': portable.get('name'),
        'source': {'source': 'local', 'path': './'},
        'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
        'category': 'Productivity',
    }
    # This product has one root plugin. Resolve its source from the marketplace root.
    if (not isinstance(marketplace, dict)
            or marketplace.get('name') != 'wordpress-devkit'
            or marketplace.get('interface') != {'displayName': 'WordPress DevKit'}
            or marketplace.get('plugins') != [expected_entry]):
        raise ValueError('Invalid DevKit marketplace identity, root source or install policy.')
    canonical = {name.removeprefix('src/skills/'): content for name, content in files.items()
                 if name.startswith('src/skills/')}
    mirror = {name.removeprefix('skills/'): content for name, content in files.items()
              if name.startswith('skills/')}
    if not canonical or canonical != mirror:
        raise ValueError('Product publication requires exact canonical/mirror parity.')
    readme = files['README.md'].decode('utf-8-sig')
    for name in canonical:
        if name.endswith('/SKILL.md') and not re.search(r'(?<![\w-])' + re.escape(name.split('/')[0]) + r'(?![\w-])', readme):
            raise ValueError(f'Public README omits skill: {name}')
    for name in files:
        if name.startswith('commands/') and name.endswith('.md') and '/wp-devkit:' + Path(name).stem not in readme:
            raise ValueError(f'Public README omits command: {name}')
    for name, content in files.items():
        if is_private_path(name):
            raise ValueError(f'Private publication path: {name}')
        if Path(name).suffix not in {'.md', '.html', '.txt'}:
            continue
        text = content.decode('utf-8-sig')
        if 'technical-docs/' in text or 'wordpress-devkit-Develop' in text:
            raise ValueError(f'Private reference in public content: {name}')
        if name.endswith('.md'):
            # Code samples are teaching material, not links in the rendered guide.
            text = re.sub(r'^```[^\n]*\n.*?^```[^\n]*$', '', text, flags=re.M | re.S)
            text = re.sub(r'`[^`\n]*`', '', text)
        parser = AssetLinks()
        parser.feed(text)
        targets = parser.links + (re.findall(r'\]\(([^)]+)\)', text) if name.endswith('.md') else [])
        for target in targets:
            target = target.strip().split(' "', 1)[0].split('#', 1)[0].strip('<>')
            target = unquote(target.split('?', 1)[0])
            if not target or re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            parts = list(PurePosixPath(name).parent.parts)
            for part in target.split('/'):
                if part == '..':
                    if not parts:
                        raise ValueError(f'Publication link escapes root: {name} -> {target}')
                    parts.pop()
                elif part not in {'', '.'}:
                    parts.append(part)
            resolved = '/'.join(parts)
            if not resolved:
                continue
            if resolved not in files and not any(path.startswith(resolved + '/') for path in files):
                raise ValueError(f'Unresolved publication link: {name} -> {target}')




def antigravity_files(files):
    """Derive Google's native skill-only plugin from a product tree (a mapping of paths to bytes)."""
    for required in ('plugin.json', 'LICENSE', 'src/antigravity/plugin.json', 'src/antigravity/README.md'):
        if required not in files:
            raise ValueError(f'Missing file for the native Antigravity plugin: {required}')
    native = files['src/antigravity/plugin.json']
    manifest = json.loads(native.decode('utf-8'))
    identity = json.loads(files['plugin.json'].decode('utf-8'))
    if (not isinstance(manifest, dict) or set(manifest) != {'name', 'description'}
            or manifest['name'] != identity['name']
            or not isinstance(manifest['description'], str) or not manifest['description'].strip()):
        raise ValueError('Invalid native Antigravity plugin manifest.')
    result = {name: content for name, content in files.items() if name.startswith('skills/')}
    if not result:
        raise ValueError('The product tree has no skills.')
    result.update({'plugin.json': native, 'LICENSE': files['LICENSE'], 'README.md': files['src/antigravity/README.md']})
    # Check guide links in the native package's own context, without OpenAI metadata.
    for target in re.findall(r'\]\(([^)]+)\)', result['README.md'].decode('utf-8')):
        if not re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) and target not in result:
            raise ValueError(f'Unresolved Antigravity guide link: {target}')
    return result


def archive_files(files):
    """Return the installable subset of a product tree (no repository metadata or tests)."""
    return {name: content for name, content in files.items()
            if PurePosixPath(name).parts[0] not in ARCHIVE_EXCLUDED_ROOTS and name not in ARCHIVE_EXCLUDED_FILES}


def write_archive(files, output, prefix='wp-devkit/'):
    """Write a ZIP with sorted entries, fixed timestamps and permissions.

    The compressed bytes also depend on the zlib build (CPython 3.14 on Windows uses zlib-ng), so only the archive
    built by the CI workflow is canonical.

    The archive is built beside the target and moved into place, so a failure never leaves a partial file."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + '.partial')
    try:
        with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, content in sorted(files.items()):
                metadata = zipfile.ZipInfo(prefix + name, date_time=(1980, 1, 1, 0, 0, 0))
                metadata.compress_type = zipfile.ZIP_DEFLATED
                metadata.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(metadata, content)
        os.replace(partial, output)
    finally:
        partial.unlink(missing_ok=True)
    return output
