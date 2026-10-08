"""Accessibility checks run in the page (Section 11). No axe-core: CLAUDE.md
keeps JS libraries out without an ADR, and these cover the rules the spec
names (WCAG 2.2 AA):

- text contrast 4.5:1 (3:1 for large text), measured on the real background;
- every control has an accessible name; images have alt text;
- one h1, no skipped heading levels, a lang on <html>;
- no positive tabindex (focus order follows the page);
- status is never colour alone: coloured pills and notes carry an icon and a word;
- tap targets 48 px or more.

`AUDIT_JS` returns a list of problems; [] means the page passes.
`FOCUS_JS` checks the element that has keyboard focus.
"""

COLOUR_JS = r"""
const parse = c => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
  const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1}; };
const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
const blend = (top, under) => ({r: top.r * top.a + under.r * (1 - top.a), g: top.g * top.a + under.g * (1 - top.a),
                                b: top.b * top.a + under.b * (1 - top.a), a: 1});
const background = el => {
  const layers = [];
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    const c = parse(getComputedStyle(n).backgroundColor);
    if (c && c.a > 0) { layers.push(c); if (c.a >= 1) break; }
  }
  let bg = {r: 255, g: 255, b: 255, a: 1};
  for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg);
  return bg;
};
const visible = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
  return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) > 0; };
const describe = el => (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + ' "' +
  (el.innerText || el.getAttribute('aria-label') || el.name || '').trim().replace(/\s+/g, ' ').slice(0, 40) + '"');
"""

AUDIT_JS = "() => {" + COLOUR_JS + r"""
  const problems = [];
  const skip = el => el.closest('.leaflet-container, template, [hidden], .sr-only');

  // Text contrast, on every element that directly holds visible text.
  for (const el of document.body.querySelectorAll('*')) {
    if (skip(el) || !visible(el)) continue;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const s = getComputedStyle(el);
    const fg = parse(s.color); if (!fg) continue;
    const bg = background(el);
    const size = parseFloat(s.fontSize), bold = Number(s.fontWeight) >= 700;
    const need = (size >= 24 || (bold && size >= 18.66)) ? 3 : 4.5;
    const got = ratio(blend(fg, bg), bg);
    if (got < need) problems.push(`contrast ${got.toFixed(2)} < ${need}: ${describe(el)}`);
  }

  // Names for controls, alt text for images.
  for (const el of document.querySelectorAll('input:not([type=hidden]), select, textarea, button, a[href]')) {
    if (skip(el)) continue;
    const named = (el.labels && el.labels.length) || el.getAttribute('aria-label') ||
                  el.getAttribute('aria-labelledby') || (el.innerText || '').trim() || el.getAttribute('title');
    if (!named) problems.push(`no accessible name: ${describe(el)}`);
  }
  for (const img of document.querySelectorAll('img')) {
    if (!skip(img) && !img.hasAttribute('alt')) problems.push(`img without alt: ${img.src}`);
  }
  for (const el of document.querySelectorAll('[role=img]')) {
    if (!skip(el) && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby'))
      problems.push(`role=img without a label: ${describe(el)}`);
  }

  // Page structure.
  if (!document.documentElement.lang) problems.push('no lang on <html>');
  const h1s = [...document.querySelectorAll('h1')].filter(h => !skip(h));
  if (h1s.length !== 1) problems.push(`${h1s.length} h1 elements`);
  let last = 0;
  for (const h of document.querySelectorAll('h1, h2, h3, h4, h5, h6')) {
    if (skip(h)) continue;
    const level = Number(h.tagName[1]);
    if (last && level > last + 1) problems.push(`heading jumps h${last} -> h${level}: ${describe(h)}`);
    last = level;
  }
  for (const el of document.querySelectorAll('[tabindex]')) {
    if (Number(el.getAttribute('tabindex')) > 0) problems.push(`positive tabindex: ${describe(el)}`);
  }

  // Status never colour alone: anything painted good/warn/crit has an icon and words.
  for (const el of document.querySelectorAll('[class*="bg-good-bg"], [class*="bg-warn-bg"], [class*="bg-crit-bg"]')) {
    if (skip(el) || !visible(el)) continue;
    if (!el.querySelector('svg') || !(el.innerText || '').trim()) problems.push(`status by colour only: ${describe(el)}`);
  }

  // 48 px tap targets (radio/checkbox rows are measured by their label).
  for (const el of document.querySelectorAll('a[href], button, select, input:not([type=hidden]):not([type=radio]):not([type=checkbox]), label:has(input[type=radio]), label:has(input[type=checkbox])')) {
    if (skip(el) || !visible(el) || el.closest('.leaflet-control-attribution')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 48 || r.height < 48) problems.push(`tap target ${Math.round(r.width)}x${Math.round(r.height)}: ${describe(el)}`);
  }
  return problems;
}"""

# The focused element must show a ring that stands out 3:1 from what's around it (WCAG 1.4.11, 2.4.7).
FOCUS_JS = "() => {" + COLOUR_JS + r"""
  const el = document.activeElement;
  if (!el || el === document.body) return null;
  const s = getComputedStyle(el);
  const width = parseFloat(s.outlineWidth) || 0;
  if (s.outlineStyle === 'none' || width < 2) return `no visible focus ring: ${describe(el)}`;
  const ring = parse(s.outlineColor), around = background(el.parentElement || el);
  const got = ratio(ring, around);
  return got < 3 ? `focus ring contrast ${got.toFixed(2)} < 3: ${describe(el)}` : null;
}"""
