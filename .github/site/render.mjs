// Draws a batch of badges for badges.py: node render.mjs <specs.json> <out.json>, where specs.json is a list of badge
// specs (badge.mjs) and out.json gets the SVGs, in the same order.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { badge } from './badge.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const widths = JSON.parse(readFileSync(join(here, 'verdana.json'), 'utf8')).widths;
const specs = JSON.parse(readFileSync(process.argv[2], 'utf8'));
writeFileSync(process.argv[3], JSON.stringify(specs.map((spec) => badge(spec, widths))));
