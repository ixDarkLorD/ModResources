"""Badges the site keeps current, like shields.io's, in each mod's own colors: how many times it was downloaded (from
CurseForge, Modrinth and both), its newest version and the Minecraft versions it's for (from updates/). Each folder of
badges/ named in badges.json gets them beside its static badges, all published under the site's badges/; a page there
lists them, ready to copy. The site is rebuilt on a schedule (.github/workflows/pages.yml), so the numbers keep up.

A badge whose numbers can't be had (a project not public yet, a service down) is drawn without them: its label alone,
so a link to it never breaks.

Called by build.py: build(out)."""
import base64
import html
import json
import os
import re
import shutil
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BADGES = 'badges'
UPDATES = 'updates'
LOADERS = ('neoforge', 'fabric', 'forge')
AGENT = 'ixDarkLorD/ModResources badges (https://ixdarklord.github.io/ModResources/badges/)'
SITE = 'https://ixdarklord.github.io/ModResources/badges/'
WIDTHS = json.load(open(os.path.join(HERE, 'verdana.json'), encoding='utf-8'))['widths']
MINECRAFT = re.compile(r'^(1\.\d+(\.\d+)?|(2[5-9]|[3-9]\d)\.\d+(\.\d+)?)$')
DARK = '#3a3f58'                                   # the label's ground, as on the static badges


def icon(svg):
    return 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()


# White icons for the badges that have no store's: a tag, a block, an arrow into a tray.
VERSION_ICON = icon("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#fff'><path d='M2 12.6V3.4C2 2.6 2.6 2 3.4 2h9.2c.4 0 .7.1 1 .4l8 8c.5.5.5 1.4 0 2l-9.2 9.2c-.6.5-1.5.5-2 0l-8-8c-.3-.3-.4-.6-.4-1zM7.5 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z'/></svg>")
MINECRAFT_ICON = icon("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#fff'><path d='M12 1.5 21.5 7v10L12 22.5 2.5 17V7L12 1.5zm0 2.3L5 7.9l7 4 7-4-7-4.1zM4.5 9.6v6.3l6.5 3.8v-6.3L4.5 9.6zm15 0L13 13.4v6.3l6.5-3.8V9.6z'/></svg>")
DOWNLOADS_ICON = icon("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='#fff'><path d='M11 2h2v10.2l3.6-3.6 1.4 1.4-6 6-6-6 1.4-1.4 3.6 3.6V2zM3 15h2v4h14v-4h2v6H3v-6z'/></svg>")


def text_width(text):
    """How wide Verdana draws it at 11 pixels, in tenths of a pixel, rounded as the static badges are."""
    return round(sum(WIDTHS.get(c, 70) for c in text) / 10) * 10


def badge(label, value, look, image):
    """A badge: the mod's colors behind an icon, the label on the dark ground and, if there is one, the value on the
    mod's accent. look is (defs, logo fill, accent) from the mod's static badge."""
    defs, fill, accent = look
    label_w = text_width(label) // 10 + 10
    value_w = text_width(value) // 10 + 10 if value else 0
    width = 24 + label_w + value_w
    title = f'{label}: {value}' if value else label

    def words(text, middle):
        x, length = middle * 10 - 10, text_width(text)
        t = html.escape(text)
        return (f'<g aria-hidden="true" fill="#010101"><text x="{x}" y="150" fill-opacity=".8" filter="url(#blur)" textLength="{length}">{t}</text>'
                f'<text x="{x}" y="150" fill-opacity=".3" textLength="{length}">{t}</text></g><text x="{x}" y="140" textLength="{length}">{t}</text>')

    value_part = (f'<rect x="{24 + label_w}" width="{value_w}" height="20" fill="{accent}"/>' if value else '')
    value_words = words(value, 24 + label_w + value_w / 2) if value else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{round(width * 1.3)}" height="26" viewBox="0 0 {width} 20" role="img" aria-label="{html.escape(title)}">'
            f'{defs}<title>{html.escape(title)}</title><filter id="blur"><feGaussianBlur stdDeviation="16"/></filter>'
            f'<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>'
            f'<clipPath id="r"><rect width="{width}" height="20" rx="3"/></clipPath><g clip-path="url(#r)"><rect width="24" height="20" fill="{fill}"/>'
            f'<rect x="24" width="{label_w}" height="20" fill="{DARK}"/>{value_part}<rect width="{width}" height="20" fill="url(#s)"/></g>'
            f'<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">'
            f'<image x="5" y="3" width="14" height="14" href="{image}"/><g transform="scale(.1)">{words(label, 24 + label_w / 2)}{value_words}</g></g></svg>')


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


def build(out):
    """Copies the static badges and draws the live ones; writes the badges page. Returns how many it drew."""
    target = os.path.join(out, BADGES)
    shutil.copytree(BADGES, target, dirs_exist_ok=True)
    mods = {name: spec for name, spec in json.load(open(os.path.join(HERE, 'badges.json'), encoding='utf-8')).items() if not name.startswith('_')}
    drawn, rows = 0, []
    for folder, spec in mods.items():
        statics = {name[:-4]: open(os.path.join(BADGES, folder, name), encoding='utf-8').read()
                   for name in sorted(os.listdir(os.path.join(BADGES, folder))) if name.endswith('.svg')}
        base = statics.get('modrinth') or statics.get('curseforge') or next(iter(statics.values()))
        look = look_of(base)
        made = {}
        mr, cf = modrinth_downloads(spec.get('modrinth')), curseforge_downloads(spec.get('curseforge'))
        if spec.get('modrinth') and 'modrinth' in statics:
            made['modrinth-downloads'] = badge('Modrinth', count(mr) if mr is not None else None, look_of(statics['modrinth']), image_of(statics['modrinth']))
        if spec.get('curseforge') and 'curseforge' in statics:
            made['curseforge-downloads'] = badge('CurseForge', count(cf) if cf is not None else None, look_of(statics['curseforge']), image_of(statics['curseforge']))
        known = [n for n in (mr, cf) if n is not None]
        made['downloads'] = badge('Downloads', count(sum(known)) if known else None, look, DOWNLOADS_ICON)
        newest, minecraft = releases(spec['modid'])
        made['version'] = badge('Version', newest, look, VERSION_ICON)
        made['minecraft'] = badge('Minecraft', span(minecraft), look, MINECRAFT_ICON)
        for name, svg in made.items():
            with open(os.path.join(target, folder, name + '.svg'), 'w', encoding='utf-8') as f:
                f.write(svg)
        drawn += len(made)
        rows.append((folder, list(made), [n for n in statics]))
        print(f'badges/{folder}: Modrinth {mr}, CurseForge {cf}, version {newest}, Minecraft {span(minecraft)}')
    with open(os.path.join(target, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page(rows))
    return drawn


def page(rows):
    """The badges page: each mod's badges, live ones first, with the Markdown and HTML to use each, ready to copy."""
    sections = []
    for folder, live, static in rows:
        items = []
        for name, kind in [(n, 'live') for n in live] + [(n, 'static') for n in static]:
            url = f'{SITE}{folder}/{name}.svg'
            md = f'![{name}]({url})'
            items.append(f'<li class="badge-row"><img src="{folder}/{name}.svg" alt="{html.escape(name)}" height="26">'
                         f'<span class="kind {kind}">{"live" if kind == "live" else "static"}</span>'
                         f'<code>{html.escape(md)}</code><button class="copy" type="button" data-copy="{html.escape(md)}">Copy</button></li>')
        sections.append(f'<section class="badge-mod"><h2>{html.escape(folder)}</h2><ul>{"".join(items)}</ul></section>')
    loaders = ''.join(f'<li class="badge-row"><img src="{n}" alt="{n[:-4]}" height="26"><span class="kind static">static</span>'
                      f'<code>{html.escape(f"![{n[:-4]}]({SITE}{n})")}</code><button class="copy" type="button" data-copy="{html.escape(f"![{n[:-4]}]({SITE}{n})")}">Copy</button></li>'
                      for n in sorted(os.listdir(BADGES)) if n.endswith('.svg'))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Badges · ModResources</title>
<link rel="stylesheet" href="../site.css">
<script>try {{ const t = localStorage.getItem('mr-theme'); if (t) document.documentElement.dataset.theme = t; }} catch (e) {{}}</script>
<style>
  .badge-mod {{ margin: 28px 0; }}
  .badge-mod ul, .loaders {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }}
  .badge-row {{ display: grid; grid-template-columns: 220px 52px 1fr auto; align-items: center; gap: 12px; }}
  .badge-row img {{ justify-self: start; }}
  .badge-row code {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; opacity: .8; }}
  .kind {{ font-size: 11px; text-transform: uppercase; letter-spacing: .5px; opacity: .7; }}
  .kind.live {{ color: #5fd38d; opacity: 1; }}
  @media (max-width: 720px) {{ .badge-row {{ grid-template-columns: 1fr auto; }} .badge-row .kind, .badge-row code {{ display: none; }} }}
</style>
</head>
<body>
<header class="bar"><div class="wrap bar-in">
  <a class="brand" href="../"><span class="mark" aria-hidden="true"></span>ModResources <span>Badges</span></a>
  <nav><a href="../">Maven</a><a href="https://github.com/ixDarkLorD/ModResources">GitHub</a></nav>
</div></header>
<main class="wrap">
  <h1>Badges</h1>
  <p>Each mod's badges, in its own colors. The live ones (downloads, newest version, Minecraft versions) are drawn again
    every few hours from CurseForge, Modrinth and this repository's update checks; a number that can't be had yet is left off.</p>
  {"".join(sections)}
  <section class="badge-mod"><h2>Loaders and more</h2><ul class="loaders">{loaders}</ul></section>
</main>
<script>
document.querySelectorAll('.copy').forEach(b => b.addEventListener('click', () => {{
  navigator.clipboard.writeText(b.dataset.copy).then(() => {{ b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy', 1200); }});
}}));
</script>
</body>
</html>
'''
