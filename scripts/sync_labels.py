"""Create or update the repository labels listed in .github/labels.yml.

Needs GH_TOKEN (or GITHUB_TOKEN) and GH_REPO (owner/name) in the environment, as the "Sync labels" workflow
provides. Use --dry-run to print the planned changes without calling the API.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LABELS = ROOT / '.github/labels.yml'


def parse_labels(text):
    """Parse the flat list-of-mappings subset of YAML used by labels.yml."""
    labels, current = [], None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue
        match = re.match(r'^(- )?\s*(name|color|description): ?(.*)$', line)
        if not match:
            raise ValueError(f'labels.yml line {number}: unsupported syntax')
        if match[1]:
            current = {}
            labels.append(current)
        if current is None:
            raise ValueError(f'labels.yml line {number}: field before the first label')
        value = match[3].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        current[match[2]] = value
    for label in labels:
        if not label.get('name') or not re.fullmatch(r'[0-9a-fA-F]{6}', label.get('color', '')):
            raise ValueError(f'Invalid label entry: {label}')
        label.setdefault('description', '')
    return labels


def request(method, url, token, body=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'wp-devkit-sync-labels'}
    if data:
        headers['Content-Type'] = 'application/json'
    with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=headers), timeout=30) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='print the plan only')
    parser.add_argument('--file', type=Path, default=LABELS)
    args = parser.parse_args(argv)
    labels = parse_labels(args.file.read_text(encoding='utf-8'))
    if args.dry_run:
        for label in labels:
            print(f"{label['name']:<18} #{label['color']}  {label['description']}")
        print(f'{len(labels)} labels would be synced.')
        return 0
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    repository = os.environ.get('GH_REPO') or os.environ.get('GITHUB_REPOSITORY')
    if not token or not repository or not re.fullmatch(r'[\w.-]+/[\w.-]+', repository):
        print('Set GH_TOKEN and GH_REPO (owner/name), or use --dry-run.', file=sys.stderr)
        return 2
    base = f'https://api.github.com/repos/{repository}/labels'
    try:
        for label in labels:
            payload = {'name': label['name'], 'color': label['color'], 'description': label['description']}
            try:
                request('PATCH', f"{base}/{urllib.parse.quote(label['name'], safe='')}", token, payload)
                action = 'updated'
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                request('POST', base, token, payload)
                action = 'created'
            print(f"{action}: {label['name']}")
    except urllib.error.HTTPError as error:
        print(f'GitHub API error {error.code}: {error.reason} {error.read().decode("utf-8", "replace")[:300]}', file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError) as error:
        print(f'Network error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
