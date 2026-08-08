/* engine — the analysis, ported from tools/ to run in a browser.
 *
 * Pure functions only: no DOM, no globals, no I/O. That is what lets
 * studio/parity.mjs run this under node and compare every number against the
 * Python implementation on identical fixtures. A port nobody checks is a
 * second implementation of the same bugs, plus new ones.
 *
 * Where behaviour looks odd here, it is deliberately matching Python:
 * statistics.median averages the middle pair on even counts, theil_sen strides
 * its pairs rather than sampling, and blank is never zero.
 */

const Engine = (() => {
  "use strict";

  // ---------- parsing -----------------------------------------------------

  /** RFC4180-ish CSV: quoted fields, embedded commas/newlines, doubled quotes. */
  function parseCSV(text) {
    if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);   // strip BOM
    const rows = [];
    let row = [], field = "", inQuotes = false;

    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQuotes) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else inQuotes = false;
        } else field += c;
      } else if (c === '"') {
        inQuotes = true;
      } else if (c === ",") {
        row.push(field); field = "";
      } else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(field); field = "";
        if (row.length > 1 || row[0] !== "") rows.push(row);
        row = [];
      } else field += c;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    if (!rows.length) throw new EngineError("The file has no rows.");

    const header = rows[0].map(h => h.trim());
    const dupes = header.filter((h, i) => header.indexOf(h) !== i);
    const out = [];
    for (let r = 1; r < rows.length; r++) {
      if (rows[r].length === 1 && rows[r][0].trim() === "") continue;
      const rec = {};
      header.forEach((h, i) => { rec[h] = rows[r][i] === undefined ? "" : rows[r][i]; });
      out.push(rec);
    }
    if (!out.length) throw new EngineError("The file has a header but no data rows.");
    return { header, rows: out, duplicateColumns: [...new Set(dupes)] };
  }

  class EngineError extends Error {}

  const BLANKS = new Set(["", "n/a", "na", "-", "--", "null", "none"]);

  /** Matches tools/concentration.py:num — blank is "not reported", never zero. */
  function num(v, field) {
    if (v === null || v === undefined) return null;
    let s = String(v).trim().replace(/,/g, "").replace(/\$/g, "").replace(/%/g, "");
    if (BLANKS.has(s.toLowerCase())) return null;
    let mult = 1;
    const last = s.slice(-1).toLowerCase();
    if ("kmb".includes(last) && s.length > 1) {
      mult = { k: 1e3, m: 1e6, b: 1e9 }[last];
      s = s.slice(0, -1);
    }
    const n = Number(s);
    if (!Number.isFinite(n)) {
      throw new EngineError(`${field}: "${v}" is not a number.`);
    }
    return n * mult;
  }

  const DATE_RE = [
    [/^(\d{4})-(\d{2})-(\d{2})/, (m) => [+m[1], +m[2], +m[3]]],
    [/^(\d{4})\/(\d{2})\/(\d{2})/, (m) => [+m[1], +m[2], +m[3]]],
    [/^(\d{1,2})\/(\d{1,2})\/(\d{4})/, (m) => [+m[3], +m[1], +m[2]]],  // US
    [/^(\d{4})-(\d{2})$/, (m) => [+m[1], +m[2], 1]],
  ];

  function parseDate(v, field) {
    const s = String(v).trim();
    if (!s) return null;
    for (const [re, pick] of DATE_RE) {
      const m = s.match(re);
      if (m) {
        const [y, mo, d] = pick(m);
        if (mo >= 1 && mo <= 12 && d >= 1 && d <= 31) return new Date(Date.UTC(y, mo - 1, d));
      }
    }
    const t = Date.parse(s);
    if (!Number.isNaN(t)) return new Date(t);
    throw new EngineError(`${field}: cannot read "${v}" as a date.`);
  }

  const iso = (d) => d.toISOString().slice(0, 10);

  // ---------- statistics --------------------------------------------------

  /** Python statistics.median: averages the middle pair on even counts. */
  function median(xs) {
    if (!xs.length) return 0;
    const s = [...xs].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  }

  function mad(xs) {
    if (!xs.length) return 0;
    const m = median(xs);
    return 1.4826 * median(xs.map(x => Math.abs(x - m)));
  }

  function hhi(values) {
    const total = values.reduce((a, b) => a + b, 0);
    if (total <= 0) throw new EngineError("Values sum to zero — nothing to measure.");
    return values.reduce((a, v) => a + (v / total) ** 2, 0);
  }

  function gini(values) {
    const xs = [...values].sort((a, b) => a - b);
    const n = xs.length;
    const total = xs.reduce((a, b) => a + b, 0);
    if (n <= 1 || total <= 0) return 0;
    let weighted = 0;
    for (let i = 0; i < n; i++) weighted += (i + 1) * xs[i];
    return (2 * weighted) / (n * total) - (n + 1) / n;
  }

  const GINI_BANDS = [[0.40, "evenly spread"], [0.60, "unequal"],
                      [1.01, "steeply unequal — a power law"]];
  function band(g) {
    for (const [edge, label] of GINI_BANDS) if (g < edge) return label;
    return "steeply unequal — a power law";
  }

  /** Robust slope. Strided, not sampled, so it is deterministic. */
  function theilSen(xs, ys, maxPairs = 1200) {
    const n = xs.length;
    if (n < 2) return 0;
    const total = (n * (n - 1)) / 2;
    const stride = Math.max(1, Math.floor(total / maxPairs));
    const slopes = [];
    let k = 0;
    for (let i = 0; i < n - 1; i++) {
      for (let j = i + 1; j < n; j++) {
        if (k % stride === 0) {
          const dx = xs[j] - xs[i];
          if (dx) slopes.push((ys[j] - ys[i]) / dx);
        }
        k++;
      }
    }
    return slopes.length ? median(slopes) : 0;
  }

  // ---------- concentration ----------------------------------------------

  function analyze(items, topN = 10) {
    const total = items.reduce((a, it) => a + it.value, 0);
    if (total <= 0) throw new EngineError("Every value is zero or blank.");

    const ranked = [...items].sort((a, b) =>
      b.value - a.value || String(a.name).localeCompare(String(b.name)));
    const desc = ranked.map(r => r.value);
    const n = desc.length;
    const h = hhi(desc);
    const g = gini(desc);

    const out = {
      items: n,
      total,
      hhi: h,
      hhiNormalized: n > 1 ? (h - 1 / n) / (1 - 1 / n) : 1,
      effectiveN: 1 / h,
      effectivePct: 1 / h / n,
      top1xEvenShare: (desc[0] / total) / (1 / n),
      gini: g,
      band: band(g),
      top: ranked.slice(0, topN).map(r => ({
        name: String(r.name), value: r.value, share: r.value / total })),
      shares: {},
      fragility: {},
    };
    for (const k of [1, 3, 5, 10]) {
      if (k <= n) out.shares["top" + k] = desc.slice(0, k).reduce((a, b) => a + b, 0) / total;
    }
    if (n >= 20) {
      const k = Math.max(1, Math.floor(n / 10));
      out.shares.top10pct = desc.slice(0, k).reduce((a, b) => a + b, 0) / total;
    }
    for (const k of [1, 3]) {
      if (k < n) {
        const lost = desc.slice(0, k).reduce((a, b) => a + b, 0);
        out.fragility["dropTop" + k] = { remaining: total - lost, pctLost: (lost / total) * 100 };
      }
    }
    return out;
  }

  // ---------- vintages ----------------------------------------------------

  function bucketKey(d, period) {
    const y = d.getUTCFullYear(), m = d.getUTCMonth() + 1;
    if (period === "year") return String(y).padStart(4, "0");
    if (period === "quarter") return `${y}-Q${Math.floor((m - 1) / 3) + 1}`;
    if (period === "month") return `${y}-${String(m).padStart(2, "0")}`;
    throw new EngineError(`Unknown period "${period}".`);
  }

  function vintages(dated, period) {
    const buckets = new Map();
    for (const { value, date } of dated) {
      const key = bucketKey(date, period);
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(value);
    }
    const grand = [...buckets.values()].flat().reduce((a, b) => a + b, 0);
    return [...buckets.keys()].sort().map(period_ => {
      const vals = buckets.get(period_);
      const total = vals.reduce((a, b) => a + b, 0);
      const sorted = [...vals].sort((a, b) => a - b);
      return {
        period: period_,
        items: vals.length,
        total,
        share: grand ? total / grand : 0,
        // Python indexes the midpoint here rather than averaging the pair.
        medianPerItem: sorted[Math.floor(sorted.length / 2)],
      };
    });
  }

  function replacement(vints) {
    if (vints.length < 4) return null;
    const k = Math.max(1, Math.floor(vints.length / 4));
    const pick = (arr) => {
      const s = arr.map(v => v.medianPerItem).sort((a, b) => a - b);
      return s[Math.floor(s.length / 2)];
    };
    const oldMedian = pick(vints.slice(0, k));
    const newMedian = pick(vints.slice(-k));
    if (oldMedian <= 0) return null;
    return {
      oldMedian, newMedian, ratio: newMedian / oldMedian,
      oldPeriods: vints.slice(0, k).map(v => v.period),
      newPeriods: vints.slice(-k).map(v => v.period),
    };
  }

  // ---------- trend -------------------------------------------------------

  function fit(hist, seasonal) {
    const xs = hist.map((_, i) => i);
    const ys = hist.map(p => p.value);
    const slope = theilSen(xs, ys);
    const intercept = median(xs.map((x, i) => ys[i] - slope * x));

    const offsets = {};
    if (seasonal === "weekly" && hist.length >= 14) {
      const b = {};
      hist.forEach((p, x) => {
        const wd = (p.date.getUTCDay() + 6) % 7;            // Monday = 0, as Python
        (b[wd] = b[wd] || []).push(p.value - (intercept + slope * x));
      });
      for (const wd of Object.keys(b)) {
        if (b[wd].length >= 3) offsets[wd] = median(b[wd]);
      }
    }
    const predict = (x, wd) => intercept + slope * x + (offsets[wd] || 0);
    const resid = hist.map((p, x) => p.value - predict(x, (p.date.getUTCDay() + 6) % 7));
    return { predict, resid };
  }

  function detect(points, window = 12, z = 3.0, seasonal = null) {
    const out = [];
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const hist = points.slice(Math.max(0, i - window), i);
      if (hist.length < Math.max(6, Math.floor(window / 3))) {
        out.push({ date: iso(p.date), value: p.value, z: null, baseline: null, flag: null });
        continue;
      }
      const { predict, resid } = fit(hist, seasonal);
      const wd = (p.date.getUTCDay() + 6) % 7;
      const expected = predict(hist.length, wd);
      const spread = mad(resid);
      let score;
      if (!spread) score = p.value === expected ? 0 : (p.value > expected ? 8 : -8);
      else score = (p.value - expected) / spread;
      out.push({
        date: iso(p.date), value: p.value,
        z: Math.round(score * 1000) / 1000,
        baseline: Math.round(expected * 10000) / 10000,
        flag: score >= z ? "spike" : (score <= -z ? "drop" : null),
      });
    }
    return out;
  }

  function cusum(diag, k = 0.5, h = 5.0, gap = 3) {
    const scored = diag.filter(d => d.z !== null);
    if (scored.length < 8) return [];
    let hi = 0, lo = 0;
    const raw = [];
    scored.forEach((r, idx) => {
      const s = Math.max(-10, Math.min(10, r.z));
      hi = Math.max(0, hi + s - k);
      lo = Math.min(0, lo + s + k);
      if (hi > h) { raw.push({ idx, date: r.date, direction: "up", stat: hi }); hi = lo = 0; }
      else if (lo < -h) { raw.push({ idx, date: r.date, direction: "down", stat: lo }); hi = lo = 0; }
    });
    const episodes = [];
    for (const e of raw) {
      const last = episodes[episodes.length - 1];
      if (last && last.direction === e.direction && e.idx - last._idx <= gap) {
        last._idx = e.idx; last.until = e.date; last.points++;
        if (Math.abs(e.stat) > Math.abs(last.stat)) last.stat = Math.round(e.stat * 100) / 100;
      } else {
        episodes.push({ _idx: e.idx, date: e.date, until: e.date,
                        direction: e.direction, stat: Math.round(e.stat * 100) / 100,
                        points: 1 });
      }
    }
    episodes.forEach(e => delete e._idx);
    return episodes;
  }

  // ---------- findings ----------------------------------------------------

  const fmt = (v) => {
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(2).replace(/\.?0+$/, "") + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
    if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
    return a % 1 ? v.toFixed(2).replace(/\.?0+$/, "") : String(Math.round(v));
  };

  function findings({ pageRes, vints, repl, revRes, trend }) {
    const out = [];
    const push = (sev, title, body) => out.push({ sev, title, body });

    if (revRes) {
      const t1 = revRes.shares.top1 || 0;
      if (t1 > 0.30) push("critical", "Revenue concentration",
        `One source is ${(t1 * 100).toFixed(0)}% of revenue. A renegotiation or ` +
        `non-renewal there halves the business. Establish contract length and ` +
        `history before anything else.`);
      else if (t1 > 0.15) push("major", "Revenue concentration",
        `The largest revenue source is ${(t1 * 100).toFixed(0)}% of the total. ` +
        `Material, not yet existential.`);
    }

    if (pageRes) {
      const t1 = pageRes.shares.top1 || 0;
      const mult = pageRes.top1xEvenShare;
      if (t1 > 0.10 || mult >= 10) {
        const d3 = pageRes.fragility.dropTop3 ? pageRes.fragility.dropTop3.pctLost : 0;
        push(t1 > 0.20 ? "critical" : "major", "Traffic concentration",
          `One item is ${(t1 * 100).toFixed(0)}% of the total — ${mult.toFixed(0)}x ` +
          `an even share. Removing the top 3 costs ${d3.toFixed(0)}%. This asset ` +
          `is its top items.`);
      }
      if (pageRes.effectivePct < 0.25 && pageRes.items >= 10) {
        push("major", "Effective inventory",
          `${pageRes.items.toLocaleString()} items behave like ` +
          `${pageRes.effectiveN.toFixed(0)}. The item count overstates what is ` +
          `actually working.`);
      }
    }

    if (vints && vints.length >= 3) {
      const newest = vints[vints.length - 1];
      if (newest.share < 0.05) push("major", "Recent output is not landing",
        `The newest cohort (${newest.period}) contributes ` +
        `${(newest.share * 100).toFixed(1)}% of the total across ` +
        `${newest.items.toLocaleString()} items.`);
      const counts = vints.map(v => v.items), meds = vints.map(v => v.medianPerItem);
      if (counts[counts.length - 1] > counts[0] &&
          meds[meds.length - 1] < meds[0] * 0.6) {
        push("critical", "Production up, yield down",
          `Output rose from ${counts[0].toLocaleString()} to ` +
          `${counts[counts.length - 1].toLocaleString()} items per period while ` +
          `median value per item fell from ${fmt(meds[0])} to ` +
          `${fmt(meds[meds.length - 1])}. The business is working harder to ` +
          `stand still — a pattern no total reveals.`);
      }
    }

    if (repl && repl.ratio < 0.5) {
      push("note", "Replacement ratio",
        `New work is at ${repl.ratio.toFixed(2)}x the median of old work. Older ` +
        `items have had longer to accumulate, so this is biased in their favour ` +
        `and is suggestive rather than conclusive.`);
    }

    if (trend) {
      const downs = trend.shifts.filter(s => s.direction === "down");
      if (downs.length) {
        const last = downs[downs.length - 1];
        const span = last.until === last.date ? "" : ` through ${last.until}`;
        push("critical", "Sustained decline detected",
          `A level shift down begins ${last.date}${span} and is not explained by ` +
          `normal variation. Any average spanning that date understates the ` +
          `current run rate.`);
      }
      if (!downs.length && !trend.flags.length) {
        push("clear", "Trend",
          `No sustained level shift and no point anomalies at the tested ` +
          `threshold. The series is stable — which is a finding, not an ` +
          `absence of one.`);
      }
    }

    if (!out.length) push("clear", "No material flag",
      `Nothing in the supplied data meets the thresholds used here. That is not ` +
      `the same as a clean business — see what was not examined.`);

    const rank = { critical: 0, major: 1, note: 2, clear: 3 };
    out.sort((a, b) => rank[a.sev] - rank[b.sev]);
    return out;
  }

  return { EngineError, parseCSV, num, parseDate, iso, median, mad, hhi, gini,
           band, theilSen, analyze, vintages, replacement, bucketKey, fit,
           detect, cusum, findings, fmt };
})();

if (typeof module !== "undefined" && module.exports) module.exports = Engine;
