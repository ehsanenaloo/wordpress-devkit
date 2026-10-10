"""Portable, strict JSON/HTML evidence reports. No third-party dependencies."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path

STATUSES = {'passed', 'failed', 'unavailable', 'skipped'}


def new_report(target):
    return {'schema_version': 1, 'target': target,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'checks': [], 'findings': [], 'limits': []}


def validate(report):
    if not isinstance(report, dict) or type(report.get('schema_version')) is not int or report['schema_version'] != 1:
        raise ValueError('Unsupported evidence report schema.')
    for key in ('target', 'generated_at'):
        if not isinstance(report.get(key), str) or not report[key].strip():
            raise ValueError(f'{key} must be a nonempty string.')
    try:
        timestamp = datetime.fromisoformat(report['generated_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError('Timestamp must include a timezone.')
    except ValueError as error:
        raise ValueError('generated_at must be an ISO timestamp with timezone.') from error
    for key in ('checks', 'findings', 'limits'):
        if not isinstance(report.get(key), list):
            raise ValueError(f'{key} must be an array.')
    if any(not isinstance(value, str) for value in report['limits']):
        raise ValueError('Limits must be strings.')
    for collection in ('checks', 'findings'):
        seen = set()
        for item in report[collection]:
            if not isinstance(item, dict):
                raise ValueError(f'{collection} entries must be objects.')
            for key in ('id', 'message'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError(f'{collection}.{key} must be a nonempty string.')
            if item['id'] in seen:
                raise ValueError(f'Duplicate {collection} id: {item["id"]}')
            seen.add(item['id'])
            if collection == 'checks':
                if item.get('status') not in STATUSES:
                    raise ValueError('Unknown check status.')
            else:
                if item.get('classification') not in {'confirmed', 'candidate'}:
                    raise ValueError('Unknown finding classification.')
                if item.get('severity') not in {'CRITICAL', 'WARNING', 'INFO'}:
                    raise ValueError('Unknown severity.')
                if item.get('remediation') not in {'open', 'fixed', 'unverified', 'accepted'}:
                    raise ValueError('Unknown remediation status.')
                for key in ('location', 'evidence'):
                    if not isinstance(item.get(key), str) or not item[key].strip():
                        raise ValueError(f'Finding {key} is required.')
    # Reject non-JSON values and nonfinite floats instead of producing invalid JSON.
    json.dumps(report, allow_nan=False)
    return report


def compare(current, previous):
    validate(current)
    validate(previous)
    if current['target'] != previous['target']:
        raise ValueError('Cannot compare reports for different targets.')
    changes = []
    for collection, fields in (('checks', ('status',)),
                               ('findings', ('classification', 'severity', 'remediation'))):
        before = {item['id']: item for item in previous[collection]}
        after = {item['id']: item for item in current[collection]}
        for identifier in sorted(before.keys() | after.keys()):
            if identifier not in after:
                changes.append(f'{collection}/{identifier}: absent in current report; resolution unverified')
            elif identifier not in before:
                changes.append(f'{collection}/{identifier}: added')
            else:
                for field in fields:
                    if before[identifier][field] != after[identifier][field]:
                        changes.append(f'{collection}/{identifier}: {field} {before[identifier][field]} -> {after[identifier][field]}')
    return changes


def render(report, previous=None):
    validate(report)
    escape = lambda value: html.escape(str(value), quote=True)
    rows = ''.join('<tr><td>' + escape(item['id']) + '</td><td>' + escape(item['status'])
                   + '</td><td>' + escape(item['message']) + '</td><td><pre>'
                   + escape(json.dumps(item.get('evidence', {}), indent=2, ensure_ascii=False))
                   + '</pre></td></tr>' for item in report['checks'])
    findings = ''.join('<li><b>' + escape(item['id']) + '</b> [' + escape(item['classification'])
                       + ', ' + escape(item['severity']) + ', ' + escape(item['remediation'])
                       + '] ' + escape(item['message']) + '<p>' + escape(item['location'])
                       + ': ' + escape(item['evidence']) + '</p></li>' for item in report['findings'])
    limits = ''.join('<li>' + escape(value) + '</li>' for value in report['limits'])
    differences = ''
    if previous is not None:
        differences = '<h2>Comparison</h2><ul>' + ''.join('<li>' + escape(value) + '</li>'
                            for value in compare(report, previous)) + '</ul>'
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>WordPress DevKit evidence</title><style>body{font:16px system-ui;max-width:1200px;'
            'margin:2rem auto;padding:0 1rem;color:#172033}table{border-collapse:collapse;width:100%}'
            'td,th{padding:.6rem;border:1px solid #ccd3df;text-align:left;vertical-align:top}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere}li{margin:.7rem 0}</style>'
            '<h1>WordPress DevKit evidence</h1><p>Target: ' + escape(report['target'])
            + '</p><p>Generated: ' + escape(report['generated_at'])
            + '</p><h2>Checks</h2><table><thead><tr><th>ID</th><th>Status</th><th>Result</th>'
            '<th>Evidence</th></tr></thead><tbody>' + rows + '</tbody></table><h2>Findings</h2><ul>'
            + findings + '</ul><h2>Limits</h2><ul>' + limits + '</ul>' + differences + '</html>')


def write_report(report, destination, previous=None):
    validate(report)
    if previous is not None:
        compare(report, previous)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False,
                                                       allow_nan=False) + '\n', encoding='utf-8')
    (destination / 'report.html').write_text(render(report, previous), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    try:
        report = json.loads(args.input.read_text(encoding='utf-8'))
        previous = json.loads(args.previous.read_text(encoding='utf-8')) if args.previous else None
        write_report(report, args.output, previous)
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
