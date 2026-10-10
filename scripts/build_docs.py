"""Generate the 20 specialist guide pages from the skills they describe, so the guides cannot drift.

Each page keeps the site shell of the existing file (header, navigation, footer) and replaces the title,
description, lead and article body with content derived from the skill's SKILL.md and the command catalog.
"""
import argparse
import html
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

TITLES = {
    'accessibility-review': 'Accessible components',
    'acf-and-content-modeling': 'Content modeling and ACF',
    'admin-ui-development': 'Admin interfaces',
    'block-development': 'Gutenberg blocks',
    'ci-cd-and-release-engineering': 'CI/CD and release engineering',
    'headless-and-wpgraphql': 'Headless and WPGraphQL',
    'migration-upgrade-review': 'Migrations and upgrades',
    'performance-review': 'Performance',
    'phpstan-review': 'PHPStan',
    'playground-development': 'WordPress Playground',
    'plugin-development': 'Plugin development',
    'rest-api-development': 'REST API',
    'security-review': 'Security review',
    'site-audit-and-onboarding': 'Site audit and onboarding',
    'test-strategy': 'Testing strategy',
    'theme-development': 'Theme development',
    'ui-design': 'Interface design',
    'wcag-review': 'WCAG conformance review',
    'woocommerce-dev': 'WooCommerce extensions',
    'wpcli-and-ops': 'WP-CLI and operations',
}


def inline(text):
    """Render the small Markdown subset used in SKILL.md (code spans, bold, links) as HTML."""
    parts = re.split(r'(`[^`]+`)', text)
    out = []
    for part in parts:
        if part.startswith('`') and part.endswith('`') and len(part) > 2:
            out.append('<code>' + html.escape(part[1:-1]) + '</code>')
        else:
            escaped = html.escape(part, quote=False)
            escaped = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', escaped)
            escaped = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', escaped)
            out.append(escaped)
    return ''.join(out)


def sections(body):
    """Split the body of a SKILL.md into {heading: text}."""
    result, current, lines = {}, None, []
    for line in body.splitlines():
        match = re.match(r'^## (.+)$', line)
        if match:
            if current is not None:
                result[current] = '\n'.join(lines).strip()
            current, lines = match[1].strip(), []
        elif current is not None:
            lines.append(line)
    if current is not None:
        result[current] = '\n'.join(lines).strip()
    return result


def bullet_items(text):
    return [re.sub(r'^[-*] ', '', item.strip()) for item in re.split(r'\n(?=[-*] )', text) if item.strip().startswith(('-', '*'))]


def numbered_items(text):
    return [re.sub(r'^\d+\. ', '', item.strip()) for item in re.split(r'\n(?=\d+\. )', text) if re.match(r'^\d+\. ', item.strip())]


def blocks(text):
    """Render paragraphs and bullet lists from a SKILL.md section."""
    out, items = [], []
    def flush():
        if items:
            out.append('<ul>' + ''.join(f'<li>{inline(item)}</li>' for item in items) + '</ul>')
            items.clear()
    for chunk in re.split(r'\n\s*\n', text.strip()):
        lines = chunk.splitlines()
        if lines and all(line.startswith(('- ', '* ', '  ')) for line in lines):
            items.extend(re.sub(r'^[-*] ', '', item.strip()) for item in re.split(r'\n(?=[-*] )', chunk))
            continue
        flush()
        if chunk.lstrip().startswith(('|', '```')):
            continue
        out.append(f'<p>{inline(" ".join(chunk.split()))}</p>')
    flush()
    return ''.join(out)


def reference_entries(skill, text, root):
    """(file, description) for every reference except the shared contract."""
    described = dict(re.findall(r'^- `references/([^`]+)`: (.+)$', text, re.M))
    entries = []
    for path in sorted((root / 'src/skills' / skill / 'references').glob('*.md')):
        if path.name == 'engineering-contract.md':
            continue
        title = path.read_text(encoding='utf-8').splitlines()[0].lstrip('# ').strip()
        entries.append((path.name, described.get(path.name) or title))
    return entries


def commands_for(skill, root):
    found = {}
    for path in sorted((root / 'commands').glob('*.md')):
        match = re.search(r'wp-devkit-[a-z0-9-]+', path.read_text(encoding='utf-8-sig'))
        if match and match[0] == skill:
            found[path.stem] = path
    return sorted(found, key=lambda name: (not name.endswith('-review'), name))


def article(skill, root):
    text = (root / 'src/skills' / skill / 'SKILL.md').read_text(encoding='utf-8')
    meta = re.match(r'^---\nname: (.+)\ndescription: (.+)\n---\n', text)
    description = meta[2]
    parts = sections(text[meta.end():])
    commands = commands_for(skill, root)
    review = next((c for c in commands if c.endswith('-review')), commands[0] if commands else None)
    short = next((c for c in commands if not c.endswith('-review')), None)
    body = ['<h2>When to use it</h2>', f'<p>{inline(description)}</p>']
    boundary_key = next((key for key in parts if key.lower().startswith(('boundar', 'route the task'))), None)
    handoff = re.search(r'^Hand off:(.*)$', text, re.M)
    if boundary_key and not parts[boundary_key].lstrip().startswith('|'):
        body += ['<h2>Boundaries and hand-offs</h2>', blocks(parts[boundary_key])]
    elif handoff:
        body += ['<h2>Boundaries and hand-offs</h2>', blocks(handoff[1].strip()[:1].upper() + handoff[1].strip()[1:])]
    body += ['<h2>Ask Claude</h2>',
             '<p>With the plugin loaded, start a read-only review of a bounded target:</p>',
             f'<pre><code>/wp-devkit:{review} &lt;target-path&gt;</code></pre>' if review else '']
    if short:
        meaning = 'requests an implementation; use the review form to stay read-only' if short == 'design' else 'requests a quick scan'
        body.append(f'<p>The short form <code>/wp-devkit:{short}</code> {meaning}.</p>')
    body += ['<h2>Ask Codex, ChatGPT or Antigravity</h2>',
             '<p>Name the installed skill and keep the request bounded. Replace the target with your files or journey.</p>',
             f'<pre><code>${skill}\nReview the target without editing files.\nRead the project instructions and the skill\'s engineering contract first.\n'
             'Separate confirmed findings from candidates and state the evidence and checks you could not run.</code></pre>']
    resources = reference_entries(skill, text, root)
    if resources:
        body += ['<h2>What it covers</h2>', '<p>The agent loads only the reference that matches the task:</p>', '<ul>']
        for name, description_text in resources:
            body.append(f'<li><code>{html.escape(name)}</code>: {inline(description_text)}</li>')
        body.append('</ul>')
    steps = numbered_items(parts.get('Code Review Workflow', ''))
    if steps:
        body += ['<h2>How a review runs</h2>', '<ol>'] + [f'<li>{inline(step)}</li>' for step in steps] + ['</ol>']
    output = parts.get('Output Format')
    if output:
        body += ['<h2>What you get back</h2>', blocks(output)]
    body.append('<aside class="callout"><p>Reviews are read-only. A clean review covers the inspected scope; it is not a certification. '
                'Ask for implementation as a separate, bounded task with a regression check.</p></aside>')
    body += ['<h2>Where to go next</h2>',
             '<p>Use <a href="review-to-fix.html">review to fix</a> for a bounded implementation and '
             '<a href="doctor-and-reports.html">Doctor and reports</a> for environment and evidence tooling.</p>',
             '<div class="reading-footer"><a href="index.html">← All guides</a><a href="quick-start.html">Your first review →</a></div>']
    return '\n'.join(item for item in body if item), description


def render(skill, root=ROOT):
    path = root / 'docs/guides' / (skill.removeprefix('wp-devkit-') + '.html')
    page = path.read_text(encoding='utf-8')
    content, description = article(skill, root)
    title = TITLES[skill.removeprefix('wp-devkit-')]
    lead = description.split('. Use ')[0].split(': ')[0].rstrip('.') + '.'
    page = re.sub(r'<title>.*?</title>', lambda m: f'<title>{html.escape(title)} | WordPress DevKit</title>', page, count=1, flags=re.S)
    page = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{html.escape(lead, quote=True)}">', page, count=1)
    page = re.sub(r'(<p class="eyebrow">[^<]*</p>)<h1>.*?</h1><p class="lead">.*?</p>',
                  lambda m: f'{m[1]}<h1>{html.escape(title)}</h1><p class="lead">{html.escape(lead)}</p>', page, count=1, flags=re.S)
    return re.sub(r'(<article class="prose">).*?(</article>)', lambda m: m[1] + content + m[2], page, count=1, flags=re.S)


def skills(root=ROOT):
    return sorted(path.name for path in (root / 'src/skills').iterdir() if path.is_dir())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail when a guide page is stale')
    args = parser.parse_args(argv)
    stale = []
    for skill in skills():
        path = ROOT / 'docs/guides' / (skill.removeprefix('wp-devkit-') + '.html')
        expected = render(skill)
        if path.read_text(encoding='utf-8') != expected:
            stale.append(path.name)
            if not args.check:
                path.write_text(expected, encoding='utf-8', newline='\n')
    if args.check and stale:
        print('Stale guide pages (run python scripts/build_docs.py): ' + ', '.join(stale), file=sys.stderr)
        return 1
    print(('Guide pages are current.' if args.check else f'Regenerated {len(stale)} guide pages.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
