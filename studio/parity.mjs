/* parity — prove studio/engine.js agrees with the Python tools.
 *
 *   python3 studio/parity_expected.py     # freeze Python's answers
 *   node studio/parity.mjs                # check the JS port against them
 *
 * Exits non-zero on any disagreement beyond tolerance. A silent numeric drift
 * between the browser tool and the CLI is the worst failure this project can
 * have, because both would look confident and only one would be right.
 */

import { readFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);
const SAMPLE = join(ROOT, "business", "sample");
const require = createRequire(import.meta.url);
const Engine = require(join(HERE, "engine.js"));

const EXPECTED_PATH = join(HERE, "parity_expected.json");
if (!existsSync(EXPECTED_PATH)) {
  console.error("parity: parity_expected.json missing — run " +
                "python3 studio/parity_expected.py first");
  process.exit(2);
}
const expected = JSON.parse(readFileSync(EXPECTED_PATH, "utf8"));

const TOL = 1e-9;          // these are the same arithmetic; near-exact is fair
let checks = 0, failures = [];

function close(name, got, want, tol = TOL) {
  checks++;
  if (got === null && want === null) return;
  if (typeof got !== "number" || typeof want !== "number") {
    if (got !== want) failures.push(`${name}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
    return;
  }
  const scale = Math.max(1, Math.abs(want));
  if (Math.abs(got - want) > tol * scale) {
    failures.push(`${name}: got ${got}, want ${want} (delta ${Math.abs(got - want)})`);
  }
}

function same(name, got, want) {
  checks++;
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    failures.push(`${name}:\n    got  ${JSON.stringify(got)}\n    want ${JSON.stringify(want)}`);
  }
}

function loadItems(file, itemCol, valueCol, dateCol) {
  const { rows } = Engine.parseCSV(readFileSync(join(SAMPLE, file), "utf8"));
  const items = [], dated = [];
  for (const r of rows) {
    const v = Engine.num(r[valueCol], valueCol);
    if (v === null || v <= 0) continue;
    const name = String(r[itemCol]).trim() || "(unnamed)";
    items.push({ name, value: v });
    if (dateCol) {
      const d = Engine.parseDate(r[dateCol], dateCol);
      if (d) dated.push({ name, value: v, date: d });
    }
  }
  return { items, dated };
}

// ---------- primitives ------------------------------------------------------
{
  const p = expected.primitives;
  close("median even", Engine.median([1, 2, 3, 4]), p.median_even);
  close("median odd", Engine.median([5, 1, 3]), p.median_odd);
  close("mad flat", Engine.mad([7, 7, 7, 7]), p.mad_flat);
  close("mad mixed", Engine.mad([1, 2, 3, 4, 100]), p.mad_mixed);
  close("gini equal", Engine.gini([10, 10, 10, 10]), p.gini_equal);
  close("gini extreme", Engine.gini([100, 1, 1, 1]), p.gini_extreme);
  close("hhi equal", Engine.hhi([10, 10, 10, 10]), p.hhi_equal);

  const xs = [...Array(20).keys()];
  close("theil-sen clean", Engine.theilSen(xs, xs.map(x => 2 * x + 1)),
        p.theil_sen_clean);
  close("theil-sen outlier",
        Engine.theilSen(xs, xs.map(x => (x === 10 ? 10000 : 2 * x + 1))),
        p.theil_sen_outlier);
}

// ---------- concentration on pages -----------------------------------------
{
  const { items, dated } = loadItems("pages.csv", "url", "pageviews", "published");
  const res = Engine.analyze(items, 10);
  const e = expected.pages;

  close("pages.items", res.items, e.items);
  close("pages.total", res.total, e.total);
  close("pages.hhi", res.hhi, e.hhi);
  close("pages.hhiNormalized", res.hhiNormalized, e.hhi_normalized);
  close("pages.effectiveN", res.effectiveN, e.effective_n);
  close("pages.effectivePct", res.effectivePct, e.effective_pct);
  close("pages.top1xEvenShare", res.top1xEvenShare, e.top1_x_even_share);
  close("pages.gini", res.gini, e.gini);
  same("pages.band", res.band, e.band);
  for (const k of Object.keys(e.shares)) {
    const jsKey = k === "top10pct" ? "top10pct" : k;
    close(`pages.shares.${k}`, res.shares[jsKey], e.shares[k]);
  }
  close("pages.fragility.drop_top1", res.fragility.dropTop1.pctLost,
        e.fragility.drop_top1);
  close("pages.fragility.drop_top3", res.fragility.dropTop3.pctLost,
        e.fragility.drop_top3);
  // Ordering matters: ties are broken by name in both implementations.
  same("pages.top order", res.top.map(t => t.name), e.top_names);
  res.top.forEach((t, i) => close(`pages.top[${i}].value`, t.value, e.top_values[i]));

  const vints = Engine.vintages(dated, "year");
  same("vintage periods", vints.map(v => v.period),
       expected.vintages.map(v => v.period));
  vints.forEach((v, i) => {
    const w = expected.vintages[i];
    close(`vintage[${i}].items`, v.items, w.items);
    close(`vintage[${i}].total`, v.total, w.total);
    close(`vintage[${i}].share`, v.share, w.share);
    close(`vintage[${i}].medianPerItem`, v.medianPerItem, w.median_per_item);
  });

  const repl = Engine.replacement(vints);
  close("replacement.ratio", repl.ratio, expected.replacement.ratio);
  close("replacement.oldMedian", repl.oldMedian, expected.replacement.old_median);
  close("replacement.newMedian", repl.newMedian, expected.replacement.new_median);
}

// ---------- concentration on revenue ---------------------------------------
{
  const { items } = loadItems("revenue.csv", "source", "amount");
  const res = Engine.analyze(items, 10);
  const e = expected.revenue;
  close("revenue.items", res.items, e.items);
  close("revenue.total", res.total, e.total);
  close("revenue.gini", res.gini, e.gini);
  close("revenue.effectiveN", res.effectiveN, e.effective_n);
  close("revenue.shares.top1", res.shares.top1, e.shares.top1);
  same("revenue.top order", res.top.map(t => t.name), e.top_names);
}

// ---------- trend ------------------------------------------------------------
{
  const { rows } = Engine.parseCSV(readFileSync(join(SAMPLE, "traffic.csv"), "utf8"));
  const pts = [];
  for (const r of rows) {
    const v = Engine.num(r.sessions, "sessions");
    if (v !== null) pts.push({ date: Engine.parseDate(r.month, "month"), value: v });
  }
  pts.sort((a, b) => a.date - b.date);

  const diag = Engine.detect(pts, 12, 3.0, null);
  const e = expected.trend.points;
  same("trend length", diag.length, e.length);
  diag.forEach((d, i) => {
    same(`trend[${i}].date`, d.date, e[i].date);
    close(`trend[${i}].z`, d.z, e[i].z, 1e-6);
    close(`trend[${i}].baseline`, d.baseline, e[i].baseline, 1e-6);
    same(`trend[${i}].flag`, d.flag, e[i].flag);
  });

  const shifts = Engine.cusum(diag);
  same("changepoint count", shifts.length, expected.trend.changepoints.length);
  shifts.forEach((s, i) => {
    const w = expected.trend.changepoints[i];
    same(`changepoint[${i}].date`, s.date, w.date);
    same(`changepoint[${i}].until`, s.until, w.until);
    same(`changepoint[${i}].direction`, s.direction, w.direction);
    same(`changepoint[${i}].points`, s.points, w.points);
    close(`changepoint[${i}].stat`, s.stat, w.stat, 1e-6);
  });
}

// ---------- report ------------------------------------------------------------
console.log(`${checks} value(s) compared against the Python implementation`);
if (failures.length) {
  console.error(`\n${failures.length} disagreement(s):\n`);
  for (const f of failures.slice(0, 25)) console.error("  " + f);
  if (failures.length > 25) console.error(`  … and ${failures.length - 25} more`);
  process.exit(1);
}
console.log("engine.js agrees with tools/ on every checked value");
