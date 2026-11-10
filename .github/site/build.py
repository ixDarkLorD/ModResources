"""Builds the Maven's website for GitHub Pages: the maven/ folder as it is, a page listing every folder in it (Pages has
no folder listings of its own), a front page with the repository to add and each artifact's versions, and the mods'
badges, the live ones drawn again (badges.py).

usage: python build.py <output folder>     (run from the repository's root)"""
import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import badges  # noqa: E402  (beside this file)

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


MINECRAFT = re.compile(r'^(1\.\d+(\.\d+)?|(2[5-9]|[3-9]\d)\.\d+(\.\d+)?)$')


def split_version(version):
    """A version's Minecraft version and its own, and whether it's in the current format (the mod's version first):
    '8.0.1+26.1.2' -> ('26.1.2', '8.0.1', True); the older '26.1.2-6' -> ('26.1.2', '6', False) and
    '1.21.1+1.0' -> ('1.21.1', '1.0', False); '1.0' -> ('', '1.0', False)."""
    if '+' in version:
        first, last = version.split('+', 1)
        if MINECRAFT.match(last) and not MINECRAFT.match(first):
            return last, first, True
    m = re.match(r'^(\d+(?:\.\d+)+)[-+](.+)$', version)
    return (m.group(1), m.group(2), False) if m else ('', version, False)


def version_key(text):
    return [(0, int(p), '') if p.isdigit() else (1, 0, p) for p in re.split(r'[.\-+]', text)]


def release_key(version):
    """Orders one Minecraft version's releases: the current format after the older ones, then by the mod's version."""
    _, own, current = split_version(version)
    return (current, version_key(own))


def folder_key(name):
    """Orders a folder's version folders by Minecraft version, then release; other folders by name."""
    mc, _, _ = split_version(name)
    return (version_key(mc), release_key(name))


def pom_info(folder, version, artifact):
    """What the POM says the artifact is ('jar', 'toml' for a version catalog, 'pom' for a Gradle plugin's marker…)
    and its name, without the loader the mods add to it ('CoolCatLib [common]' -> 'CoolCatLib')."""
    try:
        pom = ET.parse(os.path.join(folder, version, f'{artifact}-{version}.pom')).getroot()
    except (OSError, ET.ParseError):
        return 'jar', ''
    name = re.sub(r'\s*\[[^\]]*\]$', '', pom.findtext('{*}name') or '').strip()
    return pom.findtext('{*}packaging') or 'jar', name


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
        # Each Minecraft version's releases, newest first, and the Minecraft versions newest first. (Not in the order
        # they were published: an older line can be published after a newer one.)
        by_mc = {}
        for v in versions:
            by_mc.setdefault(split_version(v)[0], []).append(v)
        by_mc = {mc: sorted(by_mc[mc], key=release_key, reverse=True) for mc in sorted(by_mc, key=version_key, reverse=True)}
        newest = next(iter(by_mc.values()))[0]
        kind, title = pom_info(folder, newest, artifact)
        found.append({
            'group': group, 'artifact': artifact, 'path': os.path.relpath(folder, ROOT).replace(os.sep, '/') + '/',
            'count': len(versions), 'byMc': by_mc, 'updated': updated[:8], 'packaging': kind, 'title': title,
        })
    return sorted(found, key=lambda a: (a['group'], a['artifact']))


LOADERS = ('common', 'fabric', 'forge', 'neoforge')


def projects(found):
    """The front page's projects: a mod's loader artifacts together (coolcatlib-common, -fabric…), a Gradle plugin
    together with its marker, and anything else on its own."""
    out, mods, used = [], {}, set()
    for marker in (a for a in found if a['artifact'].endswith('.gradle.plugin')):
        plugin = marker['artifact'][:-len('.gradle.plugin')]
        impl = next((a for a in found if f"{a['group']}.{a['artifact']}" == plugin), None)
        used.update({id(marker), id(impl)})
        main = impl or marker
        out.append({'name': main['artifact'], 'title': marker['title'] or main['title'], 'kind': 'plugin', 'group': main['group'], 'plugin': plugin,
                    'artifacts': {'': main}, 'path': main['path']})
    for a in found:
        if id(a) in used:
            continue
        base, _, loader = a['artifact'].rpartition('-')
        if loader in LOADERS and base:
            key = (a['group'], base)
            if key not in mods:
                mods[key] = {'name': base, 'title': a['title'], 'kind': 'mod', 'group': a['group'], 'artifacts': {},
                             'path': a['path'].rsplit('/', 2)[0] + '/'}
                out.append(mods[key])
            mods[key]['artifacts'][loader] = a
        else:
            out.append({'name': a['artifact'], 'title': a['title'], 'kind': 'catalog' if a['packaging'] == 'toml' else 'library',
                        'group': a['group'], 'artifacts': {'': a}, 'path': a['path']})
    for p in out:
        arts = p['artifacts'].values()
        mcs = {mc for a in arts for mc in a['byMc']}
        p['mcs'] = sorted(mcs, key=version_key, reverse=True)
        p['count'] = sum(a['count'] for a in arts)
        p['title'] = p['title'] or next((a['title'] for a in arts if a['title']), '') or p['name']
        # A logo of its own, if the site has one (logos/<name>.png, the mod's mod_logo.png).
        p['logo'] = f"logos/{p['name']}.png" if os.path.exists(os.path.join(HERE, 'logos', p['name'] + '.png')) else ''
        p['updated'] = max(a['updated'] for a in arts)
        p['artifacts'] = {k: {'artifact': a['artifact'], 'byMc': a['byMc']}
                          for k, a in sorted(p['artifacts'].items(), key=lambda kv: (kv[0] not in LOADERS, LOADERS.index(kv[0]) if kv[0] in LOADERS else 0))}
    order = {'mod': 0, 'library': 1, 'plugin': 2, 'catalog': 3}
    return sorted(out, key=lambda p: (order[p['kind']], p['name']))


def listing(folder):
    """A folder's page: where it is, then its folders and files."""
    rel = os.path.relpath(folder, ROOT).replace(os.sep, '/')
    rel = '' if rel == '.' else rel + '/'
    crumbs = ['<a href="' + '../' * rel.count('/') + '">maven</a>']
    parts = rel.strip('/').split('/') if rel else []
    for i, part in enumerate(parts):
        up = '../' * (len(parts) - i - 1)
        crumbs.append(f'<a href="{up or "./"}">{html.escape(part)}</a>')
    rows = [] if not rel else ['<li class="dir"><a href="../">..</a></li>']
    # An artifact's version folders newest first, like the front page; anything else by name.
    newest_first = os.path.exists(os.path.join(folder, 'maven-metadata.xml'))
    dirs = sorted((e for e in os.scandir(folder) if e.is_dir()), key=lambda e: folder_key(e.name), reverse=newest_first)
    files = sorted((e for e in os.scandir(folder) if e.is_file() and e.name != 'index.html'), key=lambda e: e.name)
    sums = 0
    for e in dirs:
        name = html.escape(e.name)
        rows.append(f'<li class="dir"><a href="{name}/">{name}/</a></li>')
    for e in files:
        name = html.escape(e.name)
        sum_ = bool(CHECKSUM.search(e.name))
        sums += sum_
        cls = 'file sum' if sum_ else 'file jar' if e.name.endswith('.jar') else 'file'
        rows.append(f'<li class="{cls}"><a href="{name}">{name}</a><span>{size(e.stat().st_size)}</span></li>')
    depth = rel.count('/') + 1
    base = '../' * depth
    count = f'{len(dirs)} folder{"" if len(dirs) == 1 else "s"}, {len(files)} file{"" if len(files) == 1 else "s"}'
    toggle = (f'<label><input type="checkbox" id="sums"> Show checksums ({sums})</label>') if sums else ''
    return page(f'maven/{rel}', f'''
<header class="bar"><div class="wrap bar-in">
  <a class="brand" href="{base}"><span class="mark" aria-hidden="true"></span>ModResources <span>Maven</span></a>
  <nav><a href="{base}">Add a dependency</a><a href="https://github.com/ixDarkLorD/ModResources">GitHub</a></nav>
</div></header>
<main class="wrap">
  <h1 class="path">{'<span class="sep">/</span>'.join(crumbs)}</h1>
  <div class="tools-row"><span>{count}</span>{toggle}</div>
  <ul class="files{' hide-sums' if sums else ''}" id="files">{''.join(rows)}</ul>
</main>
<script>
const box = document.getElementById('sums');
if (box) box.addEventListener('change', () => document.getElementById('files').classList.toggle('hide-sums', !box.checked));
</script>''', base)


def page(title, body, base):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · ModResources Maven</title>
<link rel="stylesheet" href="{base}site.css">
<script>try {{ const t = localStorage.getItem('mr-theme'); if (t) document.documentElement.dataset.theme = t; }} catch (e) {{}}</script>
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
    shutil.copytree(os.path.join(HERE, 'logos'), os.path.join(OUT, 'logos'))
    print(f'{badges.build(OUT)} live badges drawn')
    found = projects(artifacts())
    front = open(os.path.join(HERE, 'index.html'), encoding='utf-8').read()
    front = front.replace('{{URL}}', URL).replace('{{PROJECTS}}', json.dumps(found).replace('</', '<\\/'))
    front = front.replace('{{BUILT}}', datetime.now(timezone.utc).strftime('%b %d, %Y'))
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(front)
    print(f'{len(found)} projects, written to {OUT}')


main()
