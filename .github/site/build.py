"""Builds the Maven's website for GitHub Pages: the maven/ folder as it is, a page listing every folder in it (Pages has
no folder listings of its own), and a front page with the repository to add and each artifact's versions.

usage: python build.py <output folder>     (run from the repository's root)"""
import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = 'maven'
OUT = sys.argv[1] if len(sys.argv) > 1 else '_site'
URL = 'https://ixdarklord.github.io/ModResources/maven/'
HERE = os.path.dirname(os.path.abspath(__file__))
CHECKSUM = re.compile(r'\.(md5|sha1|sha256|sha512|asc)$')


def size(n):
    for unit in ('B', 'KB', 'MB'):
        if n < 1024 or unit == 'MB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024


def split_version(version):
    """'26.1.2-6' -> ('26.1.2', '6'); '1.21.1+1.0' -> ('1.21.1', '1.0'); '1.0' -> ('', '1.0')."""
    m = re.match(r'^(\d+(?:\.\d+)+)[-+](.+)$', version)
    return (m.group(1), m.group(2)) if m else ('', version)


def version_key(text):
    return [(0, int(p), '') if p.isdigit() else (1, 0, p) for p in re.split(r'[.\-+]', text)]


def artifacts():
    """Every artifact in the Maven, read from its maven-metadata.xml."""
    found = []
    for folder, _, files in os.walk(ROOT):
        if 'maven-metadata.xml' not in files:
            continue
        meta = ET.parse(os.path.join(folder, 'maven-metadata.xml')).getroot()
        versions = [v.text for v in meta.iter('version')]
        if not versions:
            continue
        group, artifact = meta.findtext('groupId'), meta.findtext('artifactId')
        updated = meta.findtext('versioning/lastUpdated') or ''
        # Each Minecraft version's newest release (the last one published), newest Minecraft first.
        latest = {}
        for v in versions:
            latest[split_version(v)[0]] = v
        found.append({
            'group': group, 'artifact': artifact, 'path': os.path.relpath(folder, ROOT).replace(os.sep, '/') + '/',
            'versions': versions, 'count': len(versions),
            'latest': [latest[mc] for mc in sorted(latest, key=version_key, reverse=True)],
            'updated': updated[:8],
        })
    return sorted(found, key=lambda a: (a['group'], a['artifact']))


def listing(folder):
    """A folder's page: where it is, then its folders and files."""
    rel = os.path.relpath(folder, ROOT).replace(os.sep, '/')
    rel = '' if rel == '.' else rel + '/'
    crumbs = ['<a href="' + '../' * rel.count('/') + '">maven</a>']
    parts = rel.strip('/').split('/') if rel else []
    for i, part in enumerate(parts):
        up = '../' * (len(parts) - i - 1)
        crumbs.append(f'<a href="{up or "./"}">{html.escape(part)}</a>')
    rows = [] if not rel else ['<li class="dir"><a href="../">../</a></li>']
    entries = sorted(os.scandir(folder), key=lambda e: (not e.is_dir(), version_key(e.name) if e.is_dir() else [(1, 0, e.name)]))
    for e in entries:
        if e.name == 'index.html':
            continue
        name = html.escape(e.name)
        if e.is_dir():
            rows.append(f'<li class="dir"><a href="{name}/">{name}/</a></li>')
        else:
            cls = 'file sum' if CHECKSUM.search(e.name) else 'file'
            rows.append(f'<li class="{cls}"><a href="{name}">{name}</a><span>{size(e.stat().st_size)}</span></li>')
    depth = rel.count('/') + 1
    return page(f'maven/{rel}', f'''
<header class="bar"><a class="home" href="{'../' * depth}">← ModResources Maven</a></header>
<main class="wrap">
  <h1 class="path">{' / '.join(crumbs)}</h1>
  <ul class="files">{''.join(rows)}</ul>
</main>''', '../' * depth)


def page(title, body, base):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · ModResources Maven</title>
<link rel="stylesheet" href="{base}site.css">
</head>
<body>{body}
</body>
</html>
'''


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(ROOT, os.path.join(OUT, ROOT))
    for folder, _, _ in os.walk(ROOT):
        with open(os.path.join(OUT, folder, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(listing(folder))
    shutil.copy(os.path.join(HERE, 'site.css'), os.path.join(OUT, 'site.css'))
    found = artifacts()
    front = open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()
    front = front.replace('{{URL}}', URL).replace('{{ARTIFACTS}}', json.dumps(found).replace('</', '<\\/'))
    front = front.replace('{{BUILT}}', datetime.now(timezone.utc).strftime('%b %d, %Y'))
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(front)
    print(f'{len(found)} artifacts, written to {OUT}')


main()
