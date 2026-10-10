"""Stage directory replacements and roll back caught failures."""
import os
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile

# Windows reparse tags that redirect to another location. Cloud placeholders (OneDrive and similar) also
# carry the reparse attribute but are ordinary files, so they must not be treated as links.
LINK_REPARSE_TAGS = {0xA000000C, 0xA0000003}  # IO_REPARSE_TAG_SYMLINK, IO_REPARSE_TAG_MOUNT_POINT


def is_link(path):
    path = Path(path)
    if path.is_symlink():
        return True
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    if getattr(metadata, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
        tag = getattr(metadata, 'st_reparse_tag', None)
        return tag is None or tag in LINK_REPARSE_TAGS
    return False


def resolve_regular_path(path, label):
    """Resolve a user-chosen directory. The directory itself must not be a link. Links above it are followed
    (for example /home -> /var/home or a dotfile-managed ~/.claude); on POSIX only when the link belongs to root
    or to the current user, so another user cannot redirect the write."""
    path = Path(path).absolute()
    if is_link(path):
        raise ValueError(f'Refusing a linked {label}: {path}')
    if hasattr(os, 'geteuid'):
        trusted = {0, os.geteuid()}
        for item in path.parents:
            if is_link(item) and item.lstat().st_uid not in trusted:
                raise ValueError(f'Refusing a {label} below a link owned by another user: {item}')
    return path.resolve()


def remove_tree(path):
    """Delete a directory tree, clearing the read-only attribute that blocks deletion on Windows."""
    def clear_and_retry(function, target, *_):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=clear_and_retry)
    else:
        shutil.rmtree(path, onerror=clear_and_retry)


def tree_files(directory):
    directory = Path(directory)
    if is_link(directory) or not directory.is_dir():
        raise ValueError(f'Expected a regular directory: {directory}')
    files = {}
    def fail(error):
        raise error
    for current, directories, names in os.walk(directory, followlinks=False, onerror=fail):
        for name in directories + names:
            path = Path(current) / name
            if is_link(path):
                raise ValueError(f'Links are not supported: {path}')
        for name in names:
            path = Path(current) / name
            if not path.is_file():
                raise ValueError(f'Expected a regular file: {path}')
            files[path.relative_to(directory)] = path.read_bytes()
    return files


def replace_directories(sources, destination, replace=False, remove=(), expected=None, overwrite=()):
    if not sources:
        raise ValueError('No skill directories found.')
    snapshots = {}
    names = list(sources) + list(remove)
    if len(set(names)) != len(names):
        raise ValueError('Replacement and removal names must be distinct.')
    for name in names:
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError(f'Invalid directory name: {name}')
    for name, source in sources.items():
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError(f'Invalid directory name: {name}')
        snapshots[name] = tree_files(source)
        if not snapshots[name]:
            raise ValueError(f'Empty source directory: {source}')
    if is_link(destination):
        raise ValueError(f'Refusing a linked destination: {destination}')
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    lock = destination / '.wp-devkit.lock'
    try:
        lock.mkdir()  # Cooperating writers cannot interleave replacements.
    except FileExistsError:
        raise RuntimeError(
            f'Another installation is running or an earlier one was interrupted ({lock}). '
            f'Run: python scripts/recover_distribution.py --destination "{destination}". '
            'If it lists nothing, no installation is running and the lock can be cleared with --clear-stale-lock.') from None
    workspace = None
    backed_up, committed = [], []
    preserve = False
    try:
        previous = {}
        for name in names:
            target = destination / name
            if is_link(target):
                raise ValueError(f'Refusing a linked target: {target}')
            if target.exists() and not replace and name not in overwrite:
                raise FileExistsError('An installed DevKit skill exists; inspect it before --replace.')
            previous[name] = tree_files(target) if target.exists() else None
        for name, content in (expected or {}).items():
            if name not in previous or previous[name] != content:
                raise RuntimeError('Installation record changed; inspect the destination and retry.')
        workspace = Path(tempfile.mkdtemp(prefix='.wp-devkit-', dir=destination))
        staged, backups = workspace / 'staged', workspace / 'backups'
        staged.mkdir()
        backups.mkdir()
        for name, source in sources.items():
            shutil.copytree(source, staged / name)
            if tree_files(staged / name) != snapshots[name] or tree_files(source) != snapshots[name]:
                raise RuntimeError(f'Source changed during staging: {source}')
        for name in names:
            target = destination / name
            if is_link(target):
                raise ValueError(f'Target became a link: {target}')
            current = tree_files(target) if target.exists() else None
            if current != previous[name]:
                raise RuntimeError(f'Target changed during staging: {target}')
        (workspace / 'RECOVERY.txt').write_text(
            'Interrupted replacement: backups contain prior directories. Inspect staged, '
            'backups, and destination before restoring or removing the lock.\n', encoding='utf-8')
        def hashes(files):
            return None if files is None else {path.as_posix(): hashlib.sha256(data).hexdigest()
                                               for path, data in files.items()}
        (workspace / 'RECOVERY.json').write_text(json.dumps({
            'schema_version': 1, 'entries': {name: {'before': hashes(previous[name]),
                'after': hashes(snapshots.get(name))} for name in names}}, indent=2), encoding='utf-8')
        for name in names:
            target = destination / name
            if target.exists():
                os.replace(target, backups / name)
                backed_up.append(name)
            if name in sources:
                os.replace(staged / name, target)
                committed.append(name)
    except BaseException:
        try:
            for name in reversed(committed):
                target = destination / name
                if is_link(target) or target.parent != destination:
                    raise RuntimeError(f'Unsafe rollback target: {target}')
                remove_tree(target)
            for name in reversed(backed_up):
                os.replace(workspace / 'backups' / name, destination / name)
        except BaseException as error:
            preserve = True
            raise RuntimeError(f'Rollback incomplete; retain lock and recover from {workspace}') from error
        raise
    finally:
        if not preserve:
            try:
                if workspace is not None:
                    remove_tree(workspace)
                lock.rmdir()
            except OSError as error:
                # The change is already committed (or rolled back); never report it as a failed install.
                print(f'Warning: could not delete the temporary workspace {workspace}: {error}. '
                      f'Run python scripts/recover_distribution.py --destination "{destination}" to finish cleanup.',
                      file=sys.stderr)
    return [destination / name for name in sources]
