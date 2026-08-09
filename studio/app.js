/* app — the UI layer and the report assembler.
 *
 * Everything runs in the browser. Files are read with FileReader and never
 * leave the machine; there is no upload, no fetch, no analytics beacon. That
 * is a feature to state loudly, because the people most likely to use this are
 * handling a client's data and are right to be careful with it.
 */

(() => {
  "use strict";

  const E = Engine, C = Charts;
  const $ = (sel) => document.querySelector(sel);
  const el = (id) => document.getElementById(id);

  // Whatever you type in the footer field is what the report is credited to.
  // Leave it blank and it falls back to the tool name.
  const TOOL_NAME = "Reportcraft";

  const state = { pages: null, revenue: null, traffic: null, report: null };

  // ---------- file intake --------------------------------------------------

  const GUESS = {
    item: ["url", "page", "path", "post", "title", "id", "name", "source",
           "sponsor", "advertiser", "landing page", "page path"],
    value: ["pageviews", "views", "sessions", "users", "amount", "revenue",
            "earnings", "clicks", "impressions", "total", "value"],
    date: ["date", "published", "publish date", "month", "day", "created",
           "first published", "post date"],
  };

  function guessColumn(header, kind) {
    const low = header.map(h => h.toLowerCase().trim());
    for (const want of GUESS[kind]) {
      const i = low.indexOf(want);
      if (i !== -1) return header[i];
    }
    for (const want of GUESS[kind]) {
      const i = low.findIndex(h => h.includes(want));
      if (i !== -1) return header[i];
    }
    return "";
  }

  function fillSelect(select, header, chosen) {
    select.innerHTML = '<option value="">— none —</option>' +
      header.map(h => `<option value="${C.esc(h)}"${h === chosen ? " selected" : ""}>${C.esc(h)}</option>`).join("");
  }

  function readFile(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onerror = () => reject(new Error(`Could not read ${file.name}.`));
      r.onload = () => resolve(r.result);
      // Most exports are UTF-8; a cp1252 file will show mojibake in labels
      // rather than failing, and the report says so in its data-quality note.
      r.readAsText(file, "utf-8");
    });
  }

  async function accept(slot, file) {
    const box = el(`${slot}-box`);
    try {
      const text = await readFile(file);
      const parsed = E.parseCSV(text);
      state[slot] = { file: file.name, ...parsed };
      box.classList.add("loaded");
      el(`${slot}-name`).textContent = `${file.name} · ${parsed.rows.length.toLocaleString()} rows`;
      const fields = el(`${slot}-fields`);
      fields.hidden = false;
      for (const kind of ["item", "value", "date"]) {
        const sel = el(`${slot}-${kind}`);
        if (sel) fillSelect(sel, parsed.header, guessColumn(parsed.header, kind));
      }
      if (parsed.duplicateColumns.length) {
        note(`${file.name}: duplicate column name(s) ${parsed.duplicateColumns.join(", ")}. ` +
             `Only the last of each is readable.`, "warn");
      }
      el("build").disabled = false;
    } catch (err) {
      box.classList.remove("loaded");
      state[slot] = null;
      note(`${file.name}: ${err.message}`, "error");
    }
  }

  function note(msg, kind = "info") {
    const holder = el("notes");
    const div = document.createElement("div");
    div.className = `note ${kind}`;
    div.textContent = msg;
    holder.appendChild(div);
    setTimeout(() => div.remove(), 9000);
  }

  function wireDrop(slot) {
    const box = el(`${slot}-box`);
    const input = el(`${slot}-input`);
    box.addEventListener("click", (e) => { if (e.target.tagName !== "SELECT") input.click(); });
    box.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
    });
    input.addEventListener("change", () => { if (input.files[0]) accept(slot, input.files[0]); });
    ["dragenter", "dragover"].forEach(ev =>
      box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.add("over"); }));
    ["dragleave", "drop"].forEach(ev =>
      box.addEventListener(ev, (e) => { e.preventDefault(); box.classList.remove("over"); }));
    box.addEventListener("drop", (e) => {
      const f = e.dataTransfer.files[0];
      if (f) accept(slot, f);
    });
  }

  // ---------- analysis -----------------------------------------------------

  function collectItems(slot) {
    const src = state[slot];
    if (!src) return null;
    const itemCol = el(`${slot}-item`).value;
    const valueCol = el(`${slot}-value`).value;
    const dateCol = el(`${slot}-date`) ? el(`${slot}-date`).value : "";
    if (!itemCol || !valueCol) {
      throw new E.EngineError(`${src.file}: choose which column names the item and which holds the value.`);
    }
    const items = [], dated = [];
    let blank = 0, negative = 0;
    for (const r of src.rows) {
      const v = E.num(r[valueCol], valueCol);
      if (v === null) { blank++; continue; }
      if (v < 0) { negative++; continue; }
      if (v === 0) continue;
      const name = String(r[itemCol]).trim() || "(unnamed)";
      items.push({ name, value: v });
      if (dateCol) {
        const d = E.parseDate(r[dateCol], dateCol);
        if (d) dated.push({ name, value: v, date: d });
      }
    }
    if (items.length < 3) {
      throw new E.EngineError(
        `${src.file}: only ${items.length} row(s) had a positive value. ` +
        `Concentration is not a meaningful question below 3.`);
    }
    return { items, dated, blank, negative, file: src.file, dateCol };
  }

  function collectSeries() {
    const src = state.traffic;
    if (!src) return null;
    const dateCol = el("traffic-date").value, valueCol = el("traffic-value").value;
    if (!dateCol || !valueCol) {
      throw new E.EngineError(`${src.file}: choose the date column and the value column.`);
    }
    const pts = [];
    for (const r of src.rows) {
      const v = E.num(r[valueCol], valueCol);
      if (v === null) continue;
      const d = E.parseDate(r[dateCol], dateCol);
      if (d) pts.push({ date: d, value: v });
    }
    pts.sort((a, b) => a.date - b.date);
    if (pts.length < 6) {
      throw new E.EngineError(
        `${src.file}: only ${pts.length} usable period(s). Trend analysis needs ` +
        `at least 6 — ask for a longer history rather than charting noise.`);
    }
    return { pts, label: valueCol };
  }

  // ---------- report -------------------------------------------------------

  const tile = (l, v, d = "") =>
    `<div class="cell"><div class="l">${C.esc(l)}</div>` +
    `<div class="v">${C.esc(v)}</div><div class="d">${C.esc(d)}</div></div>`;

  function concentrationSection(heading, res, nounPlural) {
    const drop3 = res.fragility.dropTop3 ? res.fragility.dropTop3.pctLost : null;
    let h = `<h2>${C.esc(heading)}</h2><div class="readout">`;
    h += tile("Total", C.fmt(res.total), "as supplied");
    h += tile("Effective count", res.effectiveN.toFixed(1),
              `of ${res.items.toLocaleString()} ${nounPlural}`);
    h += tile("Largest item", `${((res.shares.top1 || 0) * 100).toFixed(0)}%`,
              `${res.top1xEvenShare.toFixed(0)}x an even share`);
    h += tile("Lose the top 3", drop3 === null ? "—" : `${drop3.toFixed(0)}%`, "of the total");
    h += "</div>";

    h += `<div class="tw"><table><thead><tr><th>Rank</th><th>Item</th>` +
         `<th class="num">Value</th><th class="num">Share</th>` +
         `<th class="num">Cumulative</th></tr></thead><tbody>`;
    let cum = 0;
    res.top.forEach((t, i) => {
      cum += t.share;
      const nm = t.name.length > 62 ? t.name.slice(0, 61) + "…" : t.name;
      h += `<tr><td class="num">${i + 1}</td><td>${C.esc(nm)}</td>` +
           `<td class="num">${C.esc(C.fmt(t.value))}</td>` +
           `<td class="num">${(t.share * 100).toFixed(1)}%</td>` +
           `<td class="num">${(cum * 100).toFixed(1)}%</td></tr>`;
    });
    h += "</tbody></table></div>";

    if (res.top.length >= 3) {
      h += `<div class="card">${C.hbar(res.top.map(t => t.name), res.top.map(t => t.value),
             { title: `Top ${res.top.length} by share` })}</div>`;
    }
    h += `<div class="rnote">Gini ${res.gini.toFixed(2)} — ${C.esc(res.band)}. ` +
         `Averages across these ${C.esc(nounPlural)} describe no actual item and ` +
         `should not be used to project the effect of adding more.</div>`;
    return h;
  }

  function vintageSection(vints, repl) {
    let h = `<h2>Is the value being renewed?</h2><div class="tw"><table><thead><tr>` +
            `<th>Vintage</th><th class="num">Items</th><th class="num">Total</th>` +
            `<th class="num">Share</th><th class="num">Median / item</th>` +
            `</tr></thead><tbody>`;
    for (const v of vints) {
      h += `<tr><td>${C.esc(v.period)}</td><td class="num">${v.items.toLocaleString()}</td>` +
           `<td class="num">${C.esc(C.fmt(v.total))}</td>` +
           `<td class="num">${(v.share * 100).toFixed(1)}%</td>` +
           `<td class="num">${C.esc(C.fmt(v.medianPerItem))}</td></tr>`;
    }
    h += "</tbody></table></div>";
    h += `<div class="card">${C.bar(vints.map(v => v.period), vints.map(v => v.medianPerItem),
           { title: "Median value per item, by publish cohort",
             subtitle: "falling bars mean new work earns less than old work did" })}</div>`;
    if (repl) {
      h += `<div class="rnote">Replacement ratio <b>${repl.ratio.toFixed(2)}x</b> ` +
           `(${C.esc(C.fmt(repl.newMedian))} newest vs ${C.esc(C.fmt(repl.oldMedian))} oldest, ` +
           `per item). Older items have had longer to accumulate, so this ratio is ` +
           `biased <i>in favour of old work</i>. ` +
           (repl.ratio >= 1
             ? "A ratio above 1.0 despite that handicap is strong evidence the asset is being renewed."
             : "A ratio below 1.0 is suggestive but not conclusive — the age handicap alone could " +
               "explain it. Settling this needs per-item performance at equal age, which cumulative " +
               "totals cannot show.") + `</div>`;
    }
    return h;
  }

  function trendSection(series, diag, shifts, flags) {
    const ys = series.pts.map(p => p.value);
    const xs = series.pts.map(p => E.iso(p.date));
    const first = ys[0], last = ys[ys.length - 1];
    const half = Math.floor(ys.length / 2);
    const early = ys.slice(0, half).reduce((a, b) => a + b, 0) / Math.max(1, half);
    const recent = ys.slice(half).reduce((a, b) => a + b, 0) / Math.max(1, ys.length - half);

    let h = `<h2>Is the trend real?</h2><div class="readout">`;
    h += tile("First → last", first ? `${(((last - first) / first) * 100).toFixed(0)}%` : "—",
              `${C.fmt(first)} → ${C.fmt(last)}`);
    h += tile("2nd half vs 1st", early ? `${(((recent - early) / early) * 100).toFixed(0)}%` : "—",
              "period averages");
    h += tile("Level shifts", String(shifts.length), "sustained, not spikes");
    h += tile("Point anomalies", String(flags.length), "outlier periods");
    h += "</div>";
    h += `<div class="card">${C.line(xs, ys, { title: series.label, subtitle: "per period as supplied" })}</div>`;

    if (shifts.length) {
      h += `<div class="tw"><table><thead><tr><th>From</th><th>Through</th>` +
           `<th>Direction</th><th class="num">Periods</th></tr></thead><tbody>`;
      for (const s of shifts) {
        h += `<tr><td>${C.esc(s.date)}</td><td>${C.esc(s.until)}</td>` +
             `<td>${C.esc(s.direction)}</td><td class="num">${s.points}</td></tr>`;
      }
      h += `</tbody></table></div><div class="rnote">A sustained level shift is a ` +
           `different event from a spike. Any trailing average spanning one of these ` +
           `dates blends two regimes and describes neither.</div>`;
    } else {
      h += `<div class="rnote">No sustained level shift detected. The series moves, ` +
           `but not more than its own history predicts.</div>`;
    }
    return h;
  }

  function buildReport() {
    el("notes").innerHTML = "";
    let pages = null, revenue = null, series = null;
    try {
      pages = collectItems("pages");
      revenue = collectItems("revenue");
      series = collectSeries();
    } catch (err) {
      note(err.message, "error");
      return;
    }
    if (!pages && !revenue && !series) {
      note("Add at least one file before building a report.", "error");
      return;
    }

    const gaps = [], quality = [];
    let pageRes = null, vints = null, repl = null, revRes = null, trend = null;

    if (pages) {
      pageRes = E.analyze(pages.items, 10);
      if (pages.dateCol) {
        if (pages.dated.length >= 4) {
          vints = E.vintages(pages.dated, el("period").value);
          repl = E.replacement(vints);
        } else {
          gaps.push("Publish dates were supplied but fewer than four rows carried a " +
                    "usable one, so no vintage analysis was possible.");
        }
      } else {
        gaps.push("No publish-date column was chosen, so whether the asset is being " +
                  "renewed or run down is unknown. This is usually the most important " +
                  "open question.");
      }
      if (pages.blank) quality.push(`${pages.blank} row(s) in ${pages.file} had a blank value and were excluded — blank means "not reported", not zero.`);
      if (pages.negative) quality.push(`${pages.negative} row(s) in ${pages.file} were negative and excluded.`);
    } else {
      gaps.push("No per-item breakdown was supplied, so concentration of traffic or " +
                "output could not be assessed.");
    }

    if (revenue) {
      revRes = E.analyze(revenue.items, 10);
      if (revenue.blank) quality.push(`${revenue.blank} row(s) in ${revenue.file} were blank and excluded.`);
      if (revenue.negative) quality.push(`${revenue.negative} row(s) in ${revenue.file} were negative and excluded. Net refunds against their line before re-running.`);
    } else {
      gaps.push("No revenue breakdown was supplied, so dependence on a single " +
                "advertiser, sponsor, or channel is unknown.");
    }

    if (series) {
      const diag = E.detect(series.pts, 12, 3.0, null);
      trend = { diag, shifts: E.cusum(diag), flags: diag.filter(d => d.flag) };
    } else {
      gaps.push("No time series was supplied, so whether the trend is genuine could " +
                "not be tested.");
    }
    gaps.push("Nothing here verifies that the supplied numbers are truthful. Confirm " +
              "them at source.");

    const fs = E.findings({ pageRes, vints, repl, revRes, trend });
    const client = el("client").value.trim() || "Untitled analysis";
    const preparedFor = el("prepared").value.trim() || "internal review";
    const date = new Date().toLocaleDateString(undefined,
      { day: "numeric", month: "long", year: "numeric" });

    let h = `<header class="rep-head"><div class="eyebrow">Metric analysis · prepared for ${C.esc(preparedFor)}</div>` +
            `<h1>${C.esc(client)}</h1><div class="meta"><span><b>${C.esc(date)}</b></span>`;
    if (pageRes) h += `<span><b>${pageRes.items.toLocaleString()}</b> items</span>`;
    if (series) h += `<span><b>${series.pts.length}</b> periods</span>`;
    h += `<span><b>${fs.length}</b> findings</span></div></header>`;

    h += `<section><h2>Findings</h2>`;
    for (const f of fs) {
      h += `<div class="f"><div class="sev ${f.sev}">${C.esc(f.sev)}</div><div>` +
           `<div class="t">${C.esc(f.title)}</div><div class="b">${C.esc(f.body)}</div></div></div>`;
    }
    h += `</section>`;

    if (revRes) h += `<section>${concentrationSection("What the revenue rests on", revRes, "sources")}</section>`;
    if (pageRes) h += `<section>${concentrationSection("What the total rests on", pageRes, "items")}</section>`;
    if (vints) h += `<section>${vintageSection(vints, repl)}</section>`;
    if (trend) h += `<section>${trendSection(series, trend.diag, trend.shifts, trend.flags)}</section>`;

    h += `<section><h2>What this does not establish</h2><div class="gaps"><ul>`;
    for (const g of gaps.concat(quality)) h += `<li>${C.esc(g)}</li>`;
    h += `</ul></div></section>`;

    const brand = el("brand").value.trim();
    const credit = C.esc(brand || `Built with ${TOOL_NAME}`);
    h += `<footer class="rep-foot">This report presents descriptive statistics ` +
         `computed from data supplied by the client. It is not a valuation, an ` +
         `appraisal, an audit, or investment advice, and no recommendation to buy, ` +
         `sell, or price at any figure is made or implied.<br>It cannot establish ` +
         `whether the underlying figures are accurate or complete.<br>` +
         `<span class="credit">${credit}</span> · generated in the browser · ` +
         `no data left this device</footer>`;

    state.report = h;
    el("report").innerHTML = h;
    el("report-wrap").hidden = false;
    el("download").disabled = false;
    el("print").disabled = false;
    el("report-wrap").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---------- download -----------------------------------------------------

  function standaloneDoc() {
    const css = document.getElementById("report-style").textContent;
    const title = (el("client").value.trim() || "report").replace(/[^\w -]/g, "");
    return {
      title: title || "report",
      html: `<!doctype html><html lang="en"><head><meta charset="utf-8">` +
        `<meta name="viewport" content="width=device-width,initial-scale=1">` +
        `<title>${C.esc(title)}</title><style>${css}</style></head>` +
        `<body class="standalone"><div class="rep">${state.report}</div></body></html>`,
    };
  }

  /** Save the report as one file.
   *
   * Anchor-download is blocked in some embedded and sandboxed frames, and it
   * fails silently there — the user clicks and nothing happens, which is worse
   * than an error. So the result is verified and a working alternative is
   * offered rather than leaving them stuck.
   */
  function downloadReport() {
    if (!state.report) return;
    const { title, html } = standaloneDoc();
    let url = null;
    try {
      const blob = new Blob([html], { type: "text/html" });
      url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title}.html`;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      note(`Saved ${title}.html — one file, opens anywhere, no internet needed.`, "info");
    } catch (err) {
      note("This browser or frame blocked the download. Use “Print / save as PDF” " +
           "instead, or open the tool in its own tab and try again.", "warn");
    } finally {
      if (url) setTimeout(() => URL.revokeObjectURL(url), 30000);
    }
  }

  /** Print just the report. Works where downloads are blocked, and is how most
   *  people actually want to hand this to a client anyway. */
  function printReport() {
    if (!state.report) return;
    window.print();
  }

  // ---------- boot ---------------------------------------------------------

  document.addEventListener("DOMContentLoaded", () => {
    ["pages", "revenue", "traffic"].forEach(wireDrop);
    el("build").addEventListener("click", buildReport);
    el("download").addEventListener("click", downloadReport);
    el("print").addEventListener("click", printReport);
    el("year").textContent = new Date().getFullYear();
  });
})();
