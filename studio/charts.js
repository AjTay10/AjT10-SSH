/* charts — the drawing half, kept out of engine.js so the statistics stay
 * pure and parity-testable.
 *
 * Same rules as tools/chartkit.py: theme-aware via CSS custom properties, no
 * external references of any kind so a saved report opens offline forever,
 * bars start at zero, gaps stay gaps, and every label is escaped because it
 * came from someone else's spreadsheet.
 */

const Charts = (() => {
  "use strict";

  const esc = (s) => String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const fmt = (v) => {
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(2).replace(/\.?0+$/, "") + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
    if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
    if (a === 0) return "0";
    return a % 1 ? Number(v.toFixed(4)).toString() : String(Math.round(v));
  };

  /** Ticks on 1/2/2.5/5 x 10^n boundaries. Always at least two. */
  function ticks(lo, hi, target = 5) {
    if (hi === lo) { const pad = Math.abs(hi) * 0.1 || 1; lo -= pad; hi += pad; }
    if (hi < lo) [lo, hi] = [hi, lo];
    const raw = (hi - lo) / Math.max(1, target);
    const mag = raw > 0 ? Math.pow(10, Math.floor(Math.log10(raw))) : 1;
    let step = 10 * mag;
    for (const m of [1, 2, 2.5, 5, 10]) if (raw <= m * mag) { step = m * mag; break; }
    const out = [];
    let t = Math.floor(lo / step) * step;
    for (let guard = 0; t <= hi + step * 0.5 && guard < 500; guard++, t += step) {
      out.push(Math.round(t * 1e10) / 1e10);
    }
    return out.length >= 2 ? out : [lo, hi];
  }

  const open = (w, h, label) =>
    `<svg class="ck" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" ` +
    `width="100%" height="${h}" role="img" aria-label="${esc(label || "chart")}">`;

  const title = (t, s) =>
    (t ? `<text class="ck-t" x="16" y="24">${esc(t)}</text>` : "") +
    (s ? `<text class="ck-s" x="16" y="${t ? 42 : 24}">${esc(s)}</text>` : "");

  const topPad = (t, s) => 20 + (t ? 22 : 0) + (s ? 20 : 0);

  /** Time or ordered series. Missing values break the path rather than lying. */
  function line(xs, ys, opts = {}) {
    const { w = 1000, h = 340, title: t = "", subtitle: s = "", unit = "" } = opts;
    const top = topPad(t, s), left = 62, right = 20, bottom = 42;
    const pw = w - left - right, ph = h - top - bottom;
    const present = ys.filter(v => v !== null && v !== undefined);
    if (!present.length || pw <= 20 || ph <= 20) return "";

    const tk = ticks(Math.min(...present), Math.max(...present));
    const lo = tk[0], hi = tk[tk.length - 1], span = (hi - lo) || 1;
    const px = (i) => left + (xs.length > 1 ? (pw * i) / (xs.length - 1) : pw / 2);
    const py = (v) => top + ph - ((v - lo) / span) * ph;

    const b = [];
    for (const v of tk) {
      const y = py(v).toFixed(1);
      b.push(`<line class="ck-g" x1="${left}" y1="${y}" x2="${left + pw}" y2="${y}"/>`);
      b.push(`<text class="ck-l" x="${left - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${esc(fmt(v) + unit)}</text>`);
    }
    const step = Math.max(1, Math.ceil(xs.length / 8));
    for (let i = 0; i < xs.length; i += step) {
      b.push(`<text class="ck-l" x="${px(i).toFixed(1)}" y="${top + ph + 18}" text-anchor="middle">${esc(xs[i])}</text>`);
    }

    let run = [];
    const runs = [];
    ys.forEach((v, i) => {
      if (v === null || v === undefined) { if (run.length) runs.push(run); run = []; }
      else run.push([px(i), py(v)]);
    });
    if (run.length) runs.push(run);

    for (const r of runs) {
      if (r.length === 1) {
        b.push(`<circle cx="${r[0][0].toFixed(1)}" cy="${r[0][1].toFixed(1)}" r="3" fill="var(--ck-c0)"/>`);
        continue;
      }
      const d = "M" + r.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L");
      const base = py(Math.max(lo, 0) <= hi ? Math.max(lo, 0) : lo);
      b.push(`<path d="${d} L${r[r.length - 1][0].toFixed(1)},${base.toFixed(1)} L${r[0][0].toFixed(1)},${base.toFixed(1)} Z" fill="var(--ck-c0)" opacity="0.12"/>`);
      b.push(`<path class="ck-ln" d="${d}" stroke="var(--ck-c0)"/>`);
    }
    const last = runs.length ? runs[runs.length - 1].slice(-1)[0] : null;
    if (last) b.push(`<circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3.6" fill="var(--ck-c0)"/>`);
    b.push(`<line class="ck-a" x1="${left}" y1="${top + ph}" x2="${left + pw}" y2="${top + ph}"/>`);
    return open(w, h, t) + title(t, s) + b.join("") + "</svg>";
  }

  /** Horizontal bars — the right choice whenever the labels are words. */
  function hbar(labels, values, opts = {}) {
    const { w = 1000, title: t = "", subtitle: s = "" } = opts;
    if (!labels.length) return "";
    const top = topPad(t, s);
    const longest = Math.max(...labels.map(l => String(l).length));
    const left = 8 + Math.max(110, Math.min(280, longest * 7));
    const right = 84, rowh = 26, gap = 8;
    const h = top + labels.length * (rowh + gap) + 16;
    const pw = w - left - right;
    if (pw <= 20) return "";
    const mx = Math.max(...values.map(Math.abs)) || 1;

    const b = [];
    labels.forEach((lab, i) => {
      const y = top + i * (rowh + gap);
      const bw = Math.max((Math.abs(values[i]) / mx) * pw, 2);
      const label = String(lab).length > 46 ? String(lab).slice(0, 45) + "…" : String(lab);
      b.push(`<text class="ck-l" x="${left - 10}" y="${y + rowh / 2 + 4}" text-anchor="end">${esc(label)}</text>`);
      b.push(`<rect x="${left}" y="${y}" width="${pw}" height="${rowh}" rx="4" fill="var(--ck-surface)"/>`);
      b.push(`<rect x="${left}" y="${y}" width="${bw.toFixed(1)}" height="${rowh}" rx="4" fill="var(--ck-c${i % 8})"/>`);
      b.push(`<text class="ck-v" x="${left + pw + 8}" y="${y + rowh / 2 + 4}">${esc(fmt(values[i]))}</text>`);
    });
    return open(w, h, t) + title(t, s) + b.join("") + "</svg>";
  }

  /** Vertical bars, always zero-based — that is the whole encoding. */
  function bar(labels, values, opts = {}) {
    const { w = 1000, h = 320, title: t = "", subtitle: s = "" } = opts;
    if (!labels.length) return "";
    const top = topPad(t, s), left = 62, right = 20, bottom = 46;
    const pw = w - left - right, ph = h - top - bottom;
    if (pw <= 20 || ph <= 20) return "";

    const tk = ticks(Math.min(0, ...values), Math.max(0, ...values));
    const lo = tk[0], hi = tk[tk.length - 1], span = (hi - lo) || 1;
    const py = (v) => top + ph - ((v - lo) / span) * ph;
    const slot = pw / labels.length, bw = Math.min(72, slot * 0.66);

    const b = [];
    for (const v of tk) {
      const y = py(v).toFixed(1);
      b.push(`<line class="ck-g" x1="${left}" y1="${y}" x2="${left + pw}" y2="${y}"/>`);
      b.push(`<text class="ck-l" x="${left - 8}" y="${(+y + 4).toFixed(1)}" text-anchor="end">${esc(fmt(v))}</text>`);
    }
    const zero = py(0);
    values.forEach((v, i) => {
      const cx = left + slot * i + slot / 2;
      const y0 = py(v), y = Math.min(y0, zero), hgt = Math.abs(zero - y0);
      b.push(`<rect x="${(cx - bw / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(hgt, 1).toFixed(1)}" rx="3" fill="var(--ck-c0)"/>`);
      b.push(`<text class="ck-v" x="${cx.toFixed(1)}" y="${(y - 6).toFixed(1)}" text-anchor="middle">${esc(fmt(v))}</text>`);
      b.push(`<text class="ck-l" x="${cx.toFixed(1)}" y="${top + ph + 20}" text-anchor="middle">${esc(labels[i])}</text>`);
    });
    b.push(`<line class="ck-a" x1="${left}" y1="${zero.toFixed(1)}" x2="${left + pw}" y2="${zero.toFixed(1)}"/>`);
    return open(w, h, t) + title(t, s) + b.join("") + "</svg>";
  }

  return { esc, fmt, ticks, line, hbar, bar };
})();

if (typeof module !== "undefined" && module.exports) module.exports = Charts;
