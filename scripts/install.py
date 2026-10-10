#!/usr/bin/env python3
"""Install self-contained skill trees with recoverable replacements."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from distribution import is_link, replace_directories, resolve_regular_path, tree_files

ROOT = Path(__file__).resolve().parents[1]
RECORD = '.wp-devkit-installation'
AGENT_PATHS = {
    'claude': Path('.claude/skills'),
    'codex': Path('.codex/skills'),
    'antigravity': Path('.gemini/config/skills'),
}


def default_destination(agent):
    if agent not in AGENT_PATHS:
        raise ValueError('Unknown agent: ' + str(agent))
    return Path.home() / AGENT_PATHS[agent]


def source_directories():
    source = ROOT / 'src/skills'
    tree_files(source)
    sources = {}
    for path in sorted(source.iterdir()):
        if is_link(path) or not path.is_dir() or not path.name.startswith('wp-devkit-'):
            raise ValueError(f'Invalid skill directory: {path}')
        for required in ('SKILL.md', 'references/engineering-contract.md'):
            if not (path / required).is_file():
                raise ValueError(f'Missing {required}: {path}')
        sources[path.name] = path
    return sources


def destination_path(agent, destination):
    if agent not in AGENT_PATHS:
        raise ValueError('Unknown agent: ' + str(agent))
    path = resolve_regular_path(Path(destination).expanduser(), 'destination')
    root = ROOT.resolve()
    if path == root or root in path.parents:
        raise ValueError('Choose a destination outside the source checkout.')
    return path


def selected_sources(skills=None):
    sources = source_directories()
    if skills is None:
        return sources
    if not skills or len(set(skills)) != len(skills):
        raise ValueError('Select one or more distinct skill names.')
    unknown = set(skills) - sources.keys()
    if unknown:
        raise ValueError('Unknown skills: ' + ', '.join(sorted(unknown)))
    return {name: sources[name] for name in sorted(skills)}


def hashes(files):
    return {path.as_posix(): hashlib.sha256(content).hexdigest() for path, content in files.items()}


def installation_record(destination):
    directory = destination / RECORD
    files = tree_files(directory) if directory.exists() or is_link(directory) else None
    if files is None:
        return {'schema_version': 1, 'skills': {}}, None
    if set(files) != {Path('manifest.json')}:
        raise ValueError('Invalid installation record files.')
    record = json.loads(files[Path('manifest.json')].decode('utf-8'))
    if not isinstance(record, dict) or set(record) != {'schema_version', 'skills'} or type(record['schema_version']) is not int or record['schema_version'] != 1 or not isinstance(record['skills'], dict):
        raise ValueError('Invalid installation record.')
    for name, item in record['skills'].items():
        if not isinstance(name, str) or not name.startswith('wp-devkit-') or Path(name).name != name or not isinstance(item, dict) or set(item) != {'version', 'files'} or not isinstance(item['version'], str) or not isinstance(item['files'], dict):
            raise ValueError('Invalid installed skill metadata.')
        if any(not isinstance(path, str) or not isinstance(digest, str) or len(digest) != 64 for path, digest in item['files'].items()):
            raise ValueError('Invalid installed file hashes.')
    return record, files


def apply_changes(sources, destination, record, previous_record, replace, remove=()):
    with tempfile.TemporaryDirectory(prefix='wp-devkit-record-') as temporary:
        metadata = Path(temporary) / RECORD
        metadata.mkdir()
        (metadata / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
        # Record and skill directories share the same rollback and recovery transaction.
        inputs = dict(sources, **{RECORD: metadata})
        return replace_directories(inputs, destination, replace, remove=remove,
                                   expected={RECORD: previous_record}, overwrite=(RECORD,))


def recorded_names(destination, skills=None):
    """Names to act on for removal and status: shipped skills plus any recorded skill no longer shipped."""
    record, _ = installation_record(destination)
    names = set(source_directories()) | set(record['skills'])
    if skills is None:
        return sorted(names)
    if not skills or len(set(skills)) != len(skills):
        raise ValueError('Select one or more distinct skill names.')
    unknown = set(skills) - names
    if unknown:
        raise ValueError('Unknown skills: ' + ', '.join(sorted(unknown)))
    return sorted(skills)


def preview(agent, destination, skills=None, removal=False):
    """Return the named directories an install would create or replace (or remove)."""
    destination = destination_path(agent, destination)
    sources = {name: None for name in recorded_names(destination, skills)} if removal else selected_sources(skills)
    for name in sources:
        target = destination / name
        if is_link(target):
            raise ValueError(f'Refusing a linked target: {target}')
        if target.exists():
            tree_files(target)
    existing = sorted(name for name in sources if (destination / name).exists())
    return {'destination': destination, 'create': sorted(set(sources) - set(existing)),
            'replace': existing}


def unprotected(destination, names, record):
    """Installed directories whose content no longer matches what DevKit installed."""
    changed = []
    for name in names:
        target = destination / name
        if not target.exists():
            continue
        entry = record['skills'].get(name)
        if entry is None:
            changed.append(f'{name} (not installed by DevKit)')
        elif hashes(tree_files(target)) != entry['files']:
            changed.append(f'{name} (modified after install)')
    return changed


def install(agent, destination, replace=False, skills=None, force=False):
    destination = destination_path(agent, destination)
    sources = selected_sources(skills)
    record, previous = installation_record(destination)
    if replace and not force:
        changed = unprotected(destination, sources, record)
        if changed:
            raise ValueError('Refusing to overwrite local changes: ' + ', '.join(changed) +
                             '. Copy anything you want to keep, then add --force.')
    version = json.loads((ROOT / '.claude-plugin/plugin.json').read_text(encoding='utf-8'))['version']
    if not isinstance(version, str) or not version:
        raise ValueError('Missing source version.')
    for name, source in sources.items():
        if (destination / name).exists() and not replace:
            raise FileExistsError('An installed DevKit skill exists; inspect it before --replace.')
        record['skills'][name] = {'version': version, 'files': hashes(tree_files(source))}
    paths = apply_changes(sources, destination, record, previous, replace)
    return [path for path in paths if path.name != RECORD]


def uninstall(agent, destination, confirm=False, skills=None, force=False):
    """Remove only DevKit directories after explicit confirmation."""
    if not confirm:
        raise ValueError('Uninstall requires --confirm after inspecting --preview output.')
    details = preview(agent, destination, skills, removal=True)
    destination = details['destination']
    record, previous = installation_record(destination)
    if not force:
        changed = unprotected(destination, details['replace'], record)
        if changed:
            raise ValueError('Refusing to remove local changes: ' + ', '.join(changed) +
                             '. Copy anything you want to keep, then add --force.')
    removed = []
    for name in details['replace']:
        target = destination / name
        if is_link(target):
            raise ValueError(f'Refusing to remove a linked target: {target}')
        tree_files(target)
        removed.append(target)
        record['skills'].pop(name, None)
    if removed:
        apply_changes({}, destination, record, previous, True, remove=[path.name for path in removed])
    return removed


def status(agent, destination, skills=None):
    destination = destination_path(agent, destination)
    names = recorded_names(destination, skills)
    record, _ = installation_record(destination)
    result = []
    for name in names:
        target = destination / name
        entry = record['skills'].get(name)
        files = tree_files(target) if target.exists() or is_link(target) else None
        state = 'missing' if files is None else 'untracked' if entry is None else 'unchanged' if hashes(files) == entry['files'] else 'modified'
        result.append({'skill': name, 'version': entry['version'] if entry else None, 'state': state})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=sorted(AGENT_PATHS), required=True)
    parser.add_argument('--destination', type=Path, help='Skills directory; overrides the default.')
    parser.add_argument('--replace', action='store_true', help='Replace only existing named DevKit directories.')
    parser.add_argument('--preview', action='store_true', help='Show directories that would be created or replaced.')
    parser.add_argument('--uninstall', action='store_true', help='Remove installed DevKit directories.')
    parser.add_argument('--confirm', action='store_true', help='Confirm an explicit uninstall operation.')
    parser.add_argument('--force', action='store_true', help='Allow --replace or --uninstall to discard local changes and directories DevKit did not install.')
    parser.add_argument('--skill', action='append', help='Select a full canonical skill name; repeat for multiple skills.')
    parser.add_argument('--status', action='store_true', help='Show recorded versions and changed installed files without network access.')
    args = parser.parse_args()
    default = default_destination(args.agent)
    action = 'Status check' if args.status else 'Preview' if args.preview else 'Uninstall' if args.uninstall else 'Installation'
    try:
        destination = args.destination or default
        if sum([args.status, args.preview, args.uninstall]) > 1:
            raise ValueError('Choose only one of --status, --preview and --uninstall.')
        if args.status:
            if args.replace or args.confirm or args.force:
                raise ValueError('--status cannot be combined with installation or removal actions.')
            print(json.dumps(status(args.agent, destination, args.skill), indent=2))
            raise SystemExit(0)
        if args.preview:
            details = preview(args.agent, destination, args.skill)
            print(f"Destination: {details['destination']}")
            print('Create: ' + (', '.join(details['create']) or 'none'))
            print('Replace: ' + (', '.join(details['replace']) or 'none'))
            raise SystemExit(0)
        if args.uninstall:
            paths = uninstall(args.agent, destination, args.confirm, args.skill, args.force)
            print(f'Removed {len(paths)} DevKit skills from {Path(destination).expanduser().resolve()}')
            raise SystemExit(0)
        paths = install(args.agent, destination, args.replace, args.skill, args.force)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f'{action} failed: {error}\n')
    print(f'Installed {len(paths)} self-contained skills into {paths[0].parent}')
    print('Manual skills do not install Claude namespaced plugin commands.')
