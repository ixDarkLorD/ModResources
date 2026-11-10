// The badge service: draws any of the site's badges on request, changed by its address, with the same badge.mjs the site
// and its builder draw with. Live numbers come from the site's data.json (redrawn every six hours).
//
//   /<mod>/<badge>.svg       a mod's badge (e.g. /trophypedestals/downloads.svg)
//   /<badge>.svg             a badge of the site's own (e.g. /fabric.svg)
//   /custom.svg              a badge from nothing but its address (label, value, colors; icon=<mod>/<badge> borrows one)
//
// Options: style (glass, flat, square, big), label, value, color (the value's ground), labelColor, logo (the icon's
// square), height (in pixels). A color is hex (with or without its #) or a CSS name; several, comma-separated, make a
// gradient: color=f2c94c,9a6a1a.
import { badge, STYLES } from '../.github/site/badge.mjs';
import verdana from '../.github/site/verdana.json' with { type: 'json' };

const SITE = 'https://ixdarklord.github.io/ModResources/badges/';
const AGE = 1800;                       // how long a drawn badge is kept by browsers, GitHub's image proxy and Cloudflare
let data = null, fetched = 0;

async function entries() {
  if (data && Date.now() - fetched < 10 * 60 * 1000) return data;
  const response = await fetch(SITE + 'data.json', { cf: { cacheTtl: 600, cacheEverything: true } });
  if (!response.ok) throw new Error('data.json: ' + response.status);
  data = await response.json();
  fetched = Date.now();
  return data;
}

function svg(body, status = 200, age = AGE) {
  return new Response(body, {
    status,
    headers: {
      'content-type': 'image/svg+xml; charset=utf-8',
      'cache-control': `public, max-age=${age}, s-maxage=${age}`,
      'access-control-allow-origin': '*',
    },
  });
}

const missing = (what) => svg(badge({ label: 'badge', value: what, valueColor: '#9b2c2c', style: 'flat' }, verdana.widths), 404, 60);

export async function draw(url) {
  const path = url.pathname.replace(/\/+$/, '');
  const found = path.match(/^\/(?:([a-z0-9-]+)\/)?([a-z0-9-]+)\.svg$/i);
  if (!found) return null;
  const [, folder = '', name] = found;
  const q = url.searchParams;
  const list = await entries();
  let spec;
  if (!folder && name === 'custom') {
    spec = { label: '', value: null, image: '', logoDefs: '', logoFill: null, labelColor: null, valueColor: null };
  } else {
    const e = list.find((x) => x.folder === folder && x.name === name);
    if (!e) return missing('not found');
    spec = { ...e };
  }
  const icon = q.get('icon');
  if (icon !== null) {
    const [f, n] = icon.includes('/') ? icon.split('/') : ['', icon];
    const from = list.find((x) => x.folder === f && x.name === n);
    spec.image = from ? from.image : '';
    if (from && spec.logoFill == null) Object.assign(spec, { logoDefs: from.logoDefs, logoFill: from.logoFill });
  }
  if (q.has('label')) spec.label = q.get('label').slice(0, 80);
  if (q.has('value')) spec.value = q.get('value').slice(0, 80) || null;
  if (q.has('color')) spec.valueColor = q.get('color');
  if (q.has('labelColor')) spec.labelColor = q.get('labelColor');
  if (q.has('logo')) Object.assign(spec, { logoDefs: '', logoFill: q.get('logo') });
  spec.style = STYLES.includes(q.get('style')) ? q.get('style') : 'glass';
  const height = Number(q.get('height'));
  if (height >= 10 && height <= 128) spec.height = Math.round(height);
  return svg(badge(spec, verdana.widths));
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === '/' || url.pathname === '') return Response.redirect(SITE + '#builder', 302);
    try {
      return (await draw(url)) ?? missing('not found');
    } catch (error) {
      return svg(badge({ label: 'badge', value: 'unavailable', valueColor: '#9b2c2c', style: 'flat' }, verdana.widths), 503, 60);
    }
  },
};
