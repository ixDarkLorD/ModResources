"""Badges the site keeps current, like shields.io's, in each mod's own colors: how many times it was downloaded (from
CurseForge, Modrinth and both), its newest version and the Minecraft versions it's for (from updates/). Each folder of
badges/ named in badges.json gets them beside its static badges, all published under the site's badges/; a page there
lists them, ready to copy, and has a builder for badges of one's own. The site is rebuilt on a schedule
(.github/workflows/pages.yml), so the numbers keep up.

Every badge, the static ones too, is published in each style badge.mjs draws: glass (the default, at
badges/<folder>/<name>.svg), and flat, square and big at badges/<folder>/<style>/<name>.svg. A mod's colors can be set in
badges.json ("label_color", "value_color"); otherwise they're its static badge's. The badges are drawn by badge.mjs (run
with Node, through render.mjs), the same code the builder page draws with.

A badge whose numbers can't be had (a project not public yet, a service down) is drawn without them: its label alone,
so a link to it never breaks.

Called by build.py: build(out)."""
import base64
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BADGES = 'badges'
UPDATES = 'updates'
LOADERS = ('neoforge', 'fabric', 'forge')
AGENT = 'ixDarkLorD/ModResources badges (https://ixdarklord.github.io/ModResources/badges/)'
SITE = 'https://ixdarklord.github.io/ModResources/badges/'
STYLES = ('glass', 'flat', 'square', 'big')
MINECRAFT = re.compile(r'^(1\.\d+(\.\d+)?|(2[5-9]|[3-9]\d)\.\d+(\.\d+)?)$')


def icon(svg):
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()


# White icons for the badges that have no store's: a tag, a block, an arrow into a tray.
VERSION_ICON = icon("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#fff'><path d='M2 12.6V3.4C2 2.6 2.6 2 3.4 2h9.2c.4 0 .7.1 1 .4l8 8c.5.5.5 1.4 0 2l-9.2 9.2c-.6.5-1.5.5-2 0l-8-8c-.3-.3-.4-.6-.4-1zM7.5 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z'/></svg>")
MINECRAFT_ICON = icon("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#fff'><path d='M12 1.5 21.5 7v10L12 22.5 2.5 17V7L12 1.5zm0 2.3L5 7.9l7 4 7-4-7-4.1zM4.5 9.6v6.3l6.5 3.8v-6.3L4.5 9.6zm15 0L13 13.4v6.3l6.5-3.8V9.6z'/></svg>")
DOWNLOADS_ICON = icon("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#fff'><path d='M11 2h2v10.2l3.6-3.6 1.4 1.4-6 6-6-6 1.4-1.4 3.6 3.6V2zM3 15h2v4h14v-4h2v6H3v-6z'/></svg>")


def look_of(svg):
    """A static badge's colors: its gradient's definition (if it has one), what fills its icon's square, and the accent
    for a value (the gradient's darker end, or the square's color)."""
    gradient = re.search(r'<linearGradient id="logo".*?</linearGradient>', svg, re.S)
    fill = re.search(r'<g clip-path="url\(#r\)"><rect width="24" height="20" fill="([^"]+)"', svg).group(1)
    stops = re.findall(r'stop-color="(#[0-9a-fA-F]{6})"', gradient.group(0)) if gradient else []
    return (gradient.group(0) if gradient else '', fill, stops[-1] if stops else fill)


def image_of(svg):
    found = re.search(r'<image [^>]*href="([^"]+)"', svg)
    return found.group(1) if found else DOWNLOADS_ICON


def fetch(url):
    try:
        request = urllib.request.Request(url, headers={'User-Agent': AGENT, 'Accept': 'application/json'})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response) if response.status == 200 else None
    except Exception:                               # (not public yet, or the service is down: drawn without it)
        return None


def modrinth_downloads(project):
    data = fetch(f'https://api.modrinth.com/v2/project/{project}') if project else None
    return data.get('downloads') or None if data else None


def curseforge_downloads(project):
    # CurseForge's own API wants a key; CFWidget serves a project's public numbers without one.
    data = fetch(f'https://api.cfwidget.com/{project}') if project else None
    total = (data or {}).get('downloads', {}).get('total')
    return total if isinstance(total, int) and total > 0 else None


def count(n):
    """A download count as shields.io writes one: 867 -> 867, 1234 -> 1.2k, 536268 -> 536k, 2500000 -> 2.5M."""
    for size, unit in ((1_000_000, 'M'), (1_000, 'k')):
        if n >= size:
            short = n / size
            text = f'{short:.0f}' if short >= 100 else f'{short:.1f}'.rstrip('0').rstrip('.')
            return text + unit
    return str(n)


def key(version):
    return [int(p) if p.isdigit() else 0 for p in re.split(r'[.\-+]', version)]


def own_version(version):
    """The mod's own part of a version: '8.2.0+26.1.2' -> '8.2.0', the older '26.1.2-6' -> '6', '1.2' -> '1.2'."""
    first, _, last = version.partition('+')
    if last and MINECRAFT.match(last):
        return first
    m = re.match(r'^(\d+(?:\.\d+)+)-(.+)$', version)
    return m.group(2) if m and MINECRAFT.match(m.group(1)) else version


def releases(modid):
    """What updates/ says of a mod: its newest version, and the Minecraft versions it's kept up on: those whose latest
    release is of the same major version as the newest (a version left behind years ago, like 1.18.2, isn't)."""
    latest = {}
    for loader in LOADERS:
        path = os.path.join(UPDATES, loader, modid + '.json')
        if not os.path.exists(path):
            continue
        for name, version in json.load(open(path, encoding='utf-8')).get('promos', {}).items():
            mc, _, kind = name.rpartition('-')
            if kind == 'latest' and MINECRAFT.match(mc):
                own = own_version(version)
                if mc not in latest or key(own) > key(latest[mc]):
                    latest[mc] = own
    if not latest:
        return None, []
    newest = max(latest.values(), key=key)
    major = key(newest)[0]
    return newest, sorted((mc for mc, own in latest.items() if key(own)[0] == major), key=key)


def span(versions):
    """The Minecraft versions as a range: oldest to newest (or the one)."""
    if not versions:
        return None
    return versions[0] if len(versions) == 1 else f'{versions[0]} – {versions[-1]}'


def label_of(svg):
    found = re.search(r'aria-label="([^"]*)"', svg)
    return html.unescape(found.group(1)) if found else ''


def draw(specs):
    """Draws the badges with badge.mjs, in one run of Node."""
    with tempfile.TemporaryDirectory() as temp:
        given, made = os.path.join(temp, 'specs.json'), os.path.join(temp, 'svgs.json')
        with open(given, 'w', encoding='utf-8') as f:
            json.dump(specs, f)
        subprocess.run(['node', os.path.join(HERE, 'render.mjs'), given, made], check=True)
        return json.load(open(made, encoding='utf-8'))


def path_of(folder, name, style):
    """Where a badge is published, under badges/: the default style beside the static badges, the others a folder in."""
    parts = [folder] if folder else []
    if style != 'glass':
        parts.append(style)
    return '/'.join(parts + [name + '.svg'])


def endpoint(e):
    """A badge as a shields.io endpoint (https://shields.io/badges/endpoint-badge): its label, its value (or, a static
    badge, its label as the message), its colors and its icon, for img.shields.io/endpoint?url=<this file>, where any
    of shields.io's options (style, color, label, labelColor, logoColor...) can be added to the address."""
    color = lambda c, default: (c if re.fullmatch(r'#[0-9a-fA-F]{6}', c or '') else default).lstrip('#')
    label_color = color(e['labelColor'], '#3a3f58')
    data = {'schemaVersion': 1, 'cacheSeconds': 3600}
    if e['value']:
        data.update(label=e['label'], message=e['value'], color=color(e['valueColor'], '#3a3f58'), labelColor=label_color)
    else:
        data.update(label='', message=e['label'], color=label_color)
    image = e.get('image') or ''
    if image.startswith('data:image/svg+xml;base64,'):
        data['logoSvg'] = base64.b64decode(image.split(',', 1)[1]).decode('utf-8', 'replace')
    return data


def build(out):
    """Copies the static badges, draws the live ones and every badge's other styles, and writes the badges page and the
    builder's data. Returns how many badges it drew."""
    target = os.path.join(out, BADGES)
    shutil.copytree(BADGES, target, dirs_exist_ok=True)
    mods = {name: spec for name, spec in json.load(open(os.path.join(HERE, 'badges.json'), encoding='utf-8')).items() if not name.startswith('_')}
    entries = []       # every badge: where it is, what it says and its colors (what badge.mjs takes, but its style)

    def entry(folder, name, live, label, value, look, image, spec=None):
        defs, fill, accent = look
        spec = spec or {}
        entries.append({'folder': folder, 'name': name, 'live': live, 'label': label, 'value': value, 'image': image,
                        'logoDefs': defs, 'logoFill': fill, 'labelColor': spec.get('label_color'),
                        'valueColor': spec.get('value_color') or accent})

    def statics_in(folder):
        where = os.path.join(BADGES, folder) if folder else BADGES
        return {name[:-4]: open(os.path.join(where, name), encoding='utf-8').read()
                for name in sorted(os.listdir(where)) if name.endswith('.svg')}

    for folder in [''] + sorted(name for name in os.listdir(BADGES) if os.path.isdir(os.path.join(BADGES, name))):
        statics = statics_in(folder)
        spec = mods.get(folder)
        if spec:
            base = statics.get('modrinth') or statics.get('curseforge') or next(iter(statics.values()))
            look = look_of(base)
            mr, cf = modrinth_downloads(spec.get('modrinth')), curseforge_downloads(spec.get('curseforge'))
            if spec.get('modrinth') and 'modrinth' in statics:
                entry(folder, 'modrinth-downloads', True, 'Modrinth', count(mr) if mr is not None else None, look_of(statics['modrinth']), image_of(statics['modrinth']), spec)
            if spec.get('curseforge') and 'curseforge' in statics:
                entry(folder, 'curseforge-downloads', True, 'CurseForge', count(cf) if cf is not None else None, look_of(statics['curseforge']), image_of(statics['curseforge']), spec)
            known = [n for n in (mr, cf) if n is not None]
            entry(folder, 'downloads', True, 'Downloads', count(sum(known)) if known else None, look, DOWNLOADS_ICON, spec)
            newest, minecraft = releases(spec['modid'])
            entry(folder, 'version', True, 'Version', newest, look, VERSION_ICON, spec)
            entry(folder, 'minecraft', True, 'Minecraft', span(minecraft), look, MINECRAFT_ICON, spec)
            print(f'badges/{folder}: Modrinth {mr}, CurseForge {cf}, version {newest}, Minecraft {span(minecraft)}')
        for name, svg in statics.items():
            entry(folder, name, False, label_of(svg), None, look_of(svg), image_of(svg), spec)

    # The live ones in every style; the static ones in the styles besides their own (their default is the file itself).
    jobs = [(e, style) for e in entries for style in STYLES if e['live'] or style != 'glass']
    svgs = draw([{**{k: v for k, v in e.items() if k not in ('folder', 'name', 'live')}, 'style': style} for e, style in jobs])
    for (e, style), svg in zip(jobs, svgs):
        path = os.path.join(target, *path_of(e['folder'], e['name'], style).split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg)

    # Every badge as a shields.io endpoint too, for addresses that take shields.io's options.
    for e in entries:
        path = os.path.join(target, *path_of(e['folder'], e['name'], 'glass')[:-4].split('/')) + '.json'
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(endpoint(e), f, separators=(',', ':'))

    # The builder draws in the browser with the same badge.mjs and widths.
    shutil.copy(os.path.join(HERE, 'badge.mjs'), os.path.join(target, 'badge.mjs'))
    shutil.copy(os.path.join(HERE, 'verdana.json'), os.path.join(target, 'verdana.json'))
    with open(os.path.join(target, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(entries, f)
    with open(os.path.join(target, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page(entries))
    return len(svgs)


def page(entries):
    """The badges page (badges.html): the gallery, drawn from data.json, and the builder."""
    worker = json.load(open(os.path.join(HERE, 'badges.json'), encoding='utf-8')).get('_worker_url', '')
    return open(os.path.join(HERE, 'badges.html'), encoding='utf-8').read().replace('{{SITE}}', SITE).replace('{{WORKER}}', worker)
