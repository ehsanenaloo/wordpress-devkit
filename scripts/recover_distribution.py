"""Inspect and recover a replacement interrupted after rollback failed."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from distribution import is_link, remove_tree, resolve_regular_path, tree_files


def regular_path(value):
    return resolve_regular_path(value, 'recovery path')


def hashes(path):
    return {name.as_posix(): hashlib.sha256(data).hexdigest() for name, data in tree_files(path).items()}


def workspaces(destination):
    destination = regular_path(destination)
    if is_link(destination) or not destination.is_dir():
        raise ValueError(f"Expected a regular destination directory: {destination}")
    return sorted(path for path in destination.glob('.wp-devkit-*')
                  if path.name not in ('.wp-devkit.lock', '.wp-devkit-installation')
                  and path.is_dir() and not is_link(path))


def committed(destination, entries):
    """True when every target already holds the journalled new content."""
    for name, state in entries.items():
        target = destination / name
        if Path(name).name != name or is_link(target):
            return False
        if (hashes(target) if target.exists() else None) != state.get('after'):
            return False
    return True


def recover(destination, workspace):
    """Restore every backed-up directory and discard staged replacements."""
    destination = regular_path(destination)
    workspace = regular_path(workspace)
    if workspace.parent != destination or workspace.name == '.wp-devkit.lock':
        raise ValueError('Recovery workspace must be directly inside the destination.')
    if not workspace.is_dir() or is_link(workspace):
        raise ValueError(f'Unknown recovery workspace: {workspace}')
    backups = workspace / 'backups'
    staged = workspace / 'staged'
    discarded = workspace / 'discarded'
    journal = workspace / 'RECOVERY.json'
    if not any(workspace.iterdir()):
        # The journal was removed after cleanup, but final directory removal failed.
        workspace.rmdir()
        lock = destination / '.wp-devkit.lock'
        if lock.is_dir() and not any(workspaces(destination)):
            lock.rmdir()
        return []
    for path in (backups, staged, discarded, journal):
        if is_link(path):
            raise ValueError(f'Linked recovery material: {path}')
        if path.exists() and path != journal:
            tree_files(path)
    if journal.exists():
        data = json.loads(journal.read_text(encoding='utf-8'))
    else:
        # Retained workspaces from earlier installers contain directory backups.
        if not backups.is_dir() or not staged.is_dir():
            raise ValueError(f'Incomplete recovery workspace: {workspace}')
        data = {'schema_version': 1, 'entries': {path.name: {
            'before': hashes(path), 'after': hashes(destination / path.name)
            if (destination / path.name).exists() else None} for path in backups.iterdir()}}
    if not isinstance(data, dict) or set(data) not in ({'schema_version', 'entries'}, {'schema_version', 'entries', 'phase'}) or data.get('phase', 'restore') not in ('restore', 'cleanup') or type(data['schema_version']) is not int or data['schema_version'] != 1 or not isinstance(data['entries'], dict):
        raise ValueError('Invalid recovery journal.')
    entries = data['entries']
    for name, state in entries.items():
        if Path(name).name != name or name in ('.', '..', '.wp-devkit.lock') or not name:
            raise ValueError(f'Invalid recovery entry: {name}')
        if not isinstance(state, dict) or set(state) != {'before', 'after'}:
            raise ValueError('Invalid recovery state.')
        for digest_map in state.values():
            if digest_map is not None and (not isinstance(digest_map, dict) or any(
                    not isinstance(key, str) or not isinstance(value, str) or len(value) != 64
                    for key, value in digest_map.items())):
                raise ValueError('Invalid recovery hashes.')
        backup = backups / name
        target = destination / name
        if is_link(target) or is_link(backup):
            raise ValueError(f'Linked recovery entry: {name}')
        current = hashes(target) if target.exists() else None
        if data.get('phase') == 'cleanup':
            if current != state['before']:
                raise ValueError(f'Restored target changed: {name}')
            continue
        if current is not None and current not in (state['before'], state['after']):
            raise ValueError(f'Recovery target changed; inspect it before continuing: {name}')
        if backup.exists() and hashes(backup) != state['before']:
            if committed(destination, entries):
                # Installation finished and only cleanup was interrupted, so the backup is expendable.
                remove_tree(workspace)
                lock = destination / '.wp-devkit.lock'
                if lock.is_dir() and not any(workspaces(destination)):
                    lock.rmdir()
                return []
            raise ValueError(f'Backup changed: {name}')
        if state['before'] is not None and not backup.exists() and current != state['before']:
            raise ValueError(f'Prior content is missing: {name}')
        if (discarded / name).exists() and hashes(discarded / name) != state['after']:
            raise ValueError(f'Discarded replacement changed: {name}')
    for directory in (backups, discarded, staged):
        if directory.exists() and any(path.name not in entries for path in directory.iterdir()):
            raise ValueError('Unknown recovery directories; inspect the workspace.')
    if not journal.exists():
        journal.write_text(json.dumps(data, indent=2), encoding='utf-8')
    if data.get('phase') != 'cleanup':
        discarded.mkdir(exist_ok=True)
    restored = []
    for name, state in entries.items():
        backup, target = backups / name, destination / name
        if data.get('phase') != 'cleanup' and (backup.exists() or state['before'] is None):
            if target.exists():
                if (discarded / name).exists():
                    raise ValueError(f'A discarded copy already exists: {name}')
                shutil.move(str(target), str(discarded / name))
            if backup.exists():
                shutil.move(str(backup), str(target))
        if state['before'] is not None:
            restored.append(name)
    # Keep the journal until cleanup finishes so interruption remains resumable.
    data['phase'] = 'cleanup'
    pending = workspace / 'RECOVERY.pending'
    if is_link(pending):
        raise ValueError('Linked recovery journal update.')
    pending.write_text(json.dumps(data, indent=2), encoding='utf-8')
    pending.replace(journal)
    for path in workspace.iterdir():
        if path != journal:
            if is_link(path):
                raise ValueError('Linked workspace cleanup material.')
            if path.is_dir():
                remove_tree(path)
            else:
                path.unlink()
    journal.unlink()
    workspace.rmdir()
    lock = destination / '.wp-devkit.lock'
    if lock.is_dir() and not any(workspaces(destination)):
        lock.rmdir()
    return restored


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True,
                        help='installation or mirror directory')
    parser.add_argument('--restore', metavar='WORKSPACE',
                        help='restore one workspace returned by the listing')
    parser.add_argument('--clear-stale-lock', action='store_true',
                        help='remove .wp-devkit.lock when no recovery workspace exists (no installation may be running)')
    args = parser.parse_args(argv)
    try:
        found = workspaces(args.destination)
        lock = regular_path(args.destination) / '.wp-devkit.lock'
        if args.clear_stale_lock:
            if found:
                print('Recovery workspaces exist; restore them first.', file=sys.stderr)
                return 1
            if lock.is_dir() and not is_link(lock):
                lock.rmdir()
                print(f'Removed stale lock: {lock}')
            else:
                print('No lock found.')
            return 0
        if not args.restore:
            for path in found:
                print(path)
            if not found and lock.is_dir():
                print(f'No recovery workspace, but a lock exists: {lock}\n'
                      'If no installation is running, clear it with --clear-stale-lock.')
            return 0
        workspace = Path(args.restore)
        if not workspace.is_absolute():
            workspace = Path(args.destination) / workspace
        if workspace.resolve() not in found:
            print(f'Workspace is not an active recovery workspace: {workspace}', file=sys.stderr)
            return 1
        names = recover(args.destination, workspace)
        print(f'Recovered {len(names)} directories from {workspace.name}.')
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f'Recovery failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
