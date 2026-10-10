#!/usr/bin/env python3
"""Synchronize the physical plugin mirror after staging the entire source."""
from pathlib import Path
from distribution import replace_directories

ROOT = Path(__file__).resolve().parents[1]


def synchronize(root=ROOT):
    root = Path(root).resolve()
    return replace_directories({'skills': root / 'src/skills'}, root, replace=True)


if __name__ == '__main__':
    try:
        synchronize()
    except (ValueError, OSError, RuntimeError) as error:
        raise SystemExit(f'Synchronization failed: {error}')
    print('Plugin skills mirror synchronized.')
