"""Validate the product tree in this checkout and build the reproducible release archive.

Run it from the public repository, where the checkout is the product. The development repository builds the
same archive from its filtered snapshot with scripts/build_release.py; both produce identical bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path

from distribution import is_link
from product_checks import antigravity_files, archive_files, validate_snapshot, write_archive

ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRECTORIES = {'.git', '__pycache__', '.pytest_cache'}
ROOT_ONLY_SKIPPED = {'build', 'node_modules', '.venv'}


def read_tree(root=ROOT):
    root = Path(root).resolve()
    files = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if (any(part in SKIPPED_DIRECTORIES for part in relative.parts) or relative.parts[0] in ROOT_ONLY_SKIPPED
                or path.suffix == '.pyc'):
            continue
        if is_link(path):
            raise ValueError(f'Linked path in product tree: {relative.as_posix()}')
        if path.is_file():
            files[relative.as_posix()] = path.read_bytes()
    return files


def check(root=ROOT):
    files = read_tree(root)
    validate_snapshot(files)
    return files


def build(output=None, root=ROOT, agent=None):
    if agent not in (None, 'antigravity'):
        raise ValueError('Unsupported archive target: ' + str(agent))
    root = Path(root).resolve()
    files = check(root)
    version = json.loads(files['.claude-plugin/plugin.json'].decode('utf-8'))['version']
    suffix = '-antigravity' if agent == 'antigravity' else ''
    output = Path(output or root / 'build' / f'wp-devkit{suffix}-{version}.zip').resolve()
    write_archive(antigravity_files(files) if agent == 'antigravity' else archive_files(files), output)
    checksum = output.with_suffix(output.suffix + '.sha256')
    checksum.write_text(f'{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}\n', encoding='utf-8', newline='\n')
    return output, checksum


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate the product tree without writing files')
    parser.add_argument('--output', type=Path, help='archive path (default: build/wp-devkit-<version>.zip)')
    parser.add_argument('--agent', choices=['antigravity'], help='build the native Google Antigravity plugin archive instead')
    args = parser.parse_args()
    try:
        if args.check:
            print(f'Product tree is valid: {len(check())} files.')
        else:
            archive, checksum = build(args.output, agent=args.agent)
            print(f'Built {archive}')
            print(f'Wrote {checksum}')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Packaging failed: {error}\n')
