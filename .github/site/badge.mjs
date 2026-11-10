// Draws a badge as an SVG: an icon square in the mod's colors, a label and, if it has one, a value. The site's build
// (badges.py, through render.mjs) and the badge builder page draw with this one function, so what the builder shows is
// what the site publishes.
//
// spec: {label, value, style, image, logoDefs, logoFill, labelColor, valueColor, height}
//   style: 'glass' (the default: a soft gloss, shadowed text), 'flat', 'square' (flat, no rounded corners) or 'big'
//          (taller, the words in capitals, like shields.io's "for the badge")
//   height: how tall it's shown, in pixels (the default: 26, or 28 for 'big'); it's drawn at any size, sharp
// widths: Verdana's character widths at 110 (verdana.json)

export const STYLES = ['glass', 'flat', 'square', 'big'];
export const LABEL = '#3a3f58';

const escape = (text) => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

/** How wide Verdana draws the text at 11 pixels, in tenths of a pixel, rounded as the badges have always been. */
export function textWidth(text, widths) {
  let sum = 0;
  for (const c of String(text)) sum += widths[c] ?? 70;
  return Math.round(sum / 10) * 10;
}

/** The same text in capitals at 10 pixels, letters spaced 1.25 pixels apart, in tenths of a pixel ('big'). */
function bigWidth(text, widths) {
  const upper = String(text).toUpperCase();
  let sum = 0;
  for (const c of upper) sum += widths[c] ?? 70;
  return Math.round(sum * 10 / 11 + 12.5 * Math.max(0, [...upper].length - 1));
}

export function badge(spec, widths) {
  const style = STYLES.includes(spec.style) ? spec.style : 'glass';
  const label = String(spec.label ?? '');
  const value = spec.value === undefined || spec.value === null || spec.value === '' ? null : String(spec.value);
  const labelColor = spec.labelColor || LABEL;
  const fill = spec.logoFill || labelColor;
  const accent = spec.valueColor || fill;
  const title = value ? `${label}: ${value}` : label;
  const defs = spec.logoDefs || '';
  const image = spec.image ? `<image x="${style === 'big' ? 8 : 5}" y="${style === 'big' ? 6 : 3}" width="${style === 'big' ? 16 : 14}" height="${style === 'big' ? 16 : 14}" href="${spec.image}"/>` : '';

  if (style === 'big') {
    const icon = 32, pad = 12, h = 28;
    const lw = bigWidth(label, widths), vw = value ? bigWidth(value, widths) : 0;
    const labelW = Math.round(lw / 10) + 2 * pad, valueW = value ? Math.round(vw / 10) + 2 * pad : 0;
    const width = icon + labelW + valueW;
    const shown = spec.height || h;
    const words = (text, middle, length, bold) =>
      `<text x="${Math.round(middle * 10)}" y="175" textLength="${length}"${bold ? ' font-weight="bold"' : ''}>${escape(String(text).toUpperCase())}</text>`;
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.round(width * shown / h)}" height="${shown}" viewBox="0 0 ${width} ${h}" role="img" aria-label="${escape(title)}">`
      + `${defs}<title>${escape(title)}</title><clipPath id="r"><rect width="${width}" height="${h}" rx="4"/></clipPath>`
      + `<g clip-path="url(#r)"><rect width="${icon}" height="${h}" fill="${fill}"/><rect x="${icon}" width="${labelW}" height="${h}" fill="${labelColor}"/>`
      + (value ? `<rect x="${icon + labelW}" width="${valueW}" height="${h}" fill="${accent}"/>` : '') + `</g>`
      + `<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="100">`
      + `${image}<g transform="scale(.1)">${words(label, icon + labelW / 2, lw, false)}${value ? words(value, icon + labelW + valueW / 2, vw, true) : ''}</g></g></svg>`;
  }

  const h = 20, shown = spec.height || 26;
  const labelW = textWidth(label, widths) / 10 + 10;
  const valueW = value ? textWidth(value, widths) / 10 + 10 : 0;
  const width = 24 + labelW + valueW;
  const glass = style === 'glass';
  const words = (text, middle) => {
    const x = middle * 10 - 10, length = textWidth(text, widths), t = escape(text);
    const shadow = glass
      ? `<g aria-hidden="true" fill="#010101"><text x="${x}" y="150" fill-opacity=".8" filter="url(#blur)" textLength="${length}">${t}</text>`
        + `<text x="${x}" y="150" fill-opacity=".3" textLength="${length}">${t}</text></g>`
      : `<text aria-hidden="true" x="${x}" y="150" fill="#010101" fill-opacity=".3" textLength="${length}">${t}</text>`;
    return `${shadow}<text x="${x}" y="140" textLength="${length}">${t}</text>`;
  };
  const rx = style === 'square' ? 0 : 3;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${Math.round(width * shown / h)}" height="${shown}" viewBox="0 0 ${width} ${h}" role="img" aria-label="${escape(title)}">`
    + `${defs}<title>${escape(title)}</title>`
    + (glass ? `<filter id="blur"><feGaussianBlur stdDeviation="16"/></filter><linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>` : '')
    + `<clipPath id="r"><rect width="${width}" height="${h}" rx="${rx}"/></clipPath><g clip-path="url(#r)"><rect width="24" height="${h}" fill="${fill}"/>`
    + `<rect x="24" width="${labelW}" height="${h}" fill="${labelColor}"/>`
    + (value ? `<rect x="${24 + labelW}" width="${valueW}" height="${h}" fill="${accent}"/>` : '')
    + (glass ? `<rect width="${width}" height="${h}" fill="url(#s)"/>` : '') + `</g>`
    + `<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">`
    + `${image}<g transform="scale(.1)">${words(label, 24 + labelW / 2)}${value ? words(value, 24 + labelW + valueW / 2) : ''}</g></g></svg>`;
}
