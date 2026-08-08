/* browsertest — drive the real tool in a real browser.
 *
 *   node studio/browsertest.mjs [--screenshot out.png]
 *
 * Parity proves the arithmetic is right; this proves a person can actually use
 * it. It loads studio/index.html from disk, feeds it the committed sample
 * exports, builds a report, and checks the findings and the download path.
 *
 * Playwright is a dev-time dependency only — the product itself has none.
 * Skips with exit 0 when Playwright is absent so the rest of QA still runs.
 */

import { existsSync, readFileSync, mkdtempSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);
const SAMPLE = join(ROOT, "business", "sample");
const INDEX = join(HERE, "index.html");

let chromium;
try {
  const require = createRequire(import.meta.url);
  ({ chromium } = require(process.env.PLAYWRIGHT_PATH || "playwright"));
} catch {
  console.log("browsertest: playwright not installed — skipping (not a failure)");
  process.exit(0);
}

const shotIdx = process.argv.indexOf("--screenshot");
const shot = shotIdx !== -1 ? process.argv[shotIdx + 1] : null;

/** Find versioned browser installs without hard-coding a build number. */
function glob(base, dirRe, tail) {
  try {
    return readdirSync(base).filter(d => dirRe.test(d)).sort().reverse()
      .map(d => join(base, d, tail));
  } catch { return []; }
}

const fail = (msg) => { console.error("browsertest: " + msg); process.exit(1); };

if (!existsSync(INDEX)) fail("studio/index.html missing — run python3 studio/build.py");
for (const f of ["pages.csv", "revenue.csv", "traffic.csv"]) {
  if (!existsSync(join(SAMPLE, f))) {
    fail(`business/sample/${f} missing — run python3 business/sample.py`);
  }
}

// The pinned Playwright build may not match the Chromium already on the
// machine, so try known locations before falling back to a managed download.
const CANDIDATES = [
  process.env.CHROMIUM_PATH,
  "/opt/pw-browsers/chromium/chrome-linux/chrome",
  ...glob("/opt/pw-browsers", /^chromium-\d+$/, "chrome-linux/chrome"),
  "/usr/bin/chromium", "/usr/bin/google-chrome",
].filter(Boolean).filter(existsSync);

let browser = null, launchErr = null;
for (const executablePath of CANDIDATES) {
  try { browser = await chromium.launch({ executablePath }); break; }
  catch (e) { launchErr = e; }
}
if (!browser) {
  try { browser = await chromium.launch(); }
  catch (e) {
    console.log("browsertest: no usable Chromium — skipping (not a failure)");
    console.log("  " + String(launchErr || e).split("\n")[0]);
    process.exit(0);
  }
}

const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });

const consoleErrors = [];
page.on("pageerror", (e) => consoleErrors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
// Nothing should ever leave the page. Fail loudly if anything tries.
page.on("request", (r) => {
  const u = r.url();
  if (!u.startsWith("file://") && !u.startsWith("data:") && !u.startsWith("about:")) {
    fail(`the tool attempted a network request to ${u}`);
  }
});

await page.goto(pathToFileURL(INDEX).href);

// ---- load the three fixtures -------------------------------------------
await page.setInputFiles("#pages-input", join(SAMPLE, "pages.csv"));
await page.setInputFiles("#revenue-input", join(SAMPLE, "revenue.csv"));
await page.setInputFiles("#traffic-input", join(SAMPLE, "traffic.csv"));
await page.waitForSelector("#pages-fields:not([hidden])");

// ---- column auto-detection ---------------------------------------------
const guessed = await page.evaluate(() => ({
  pagesItem: document.getElementById("pages-item").value,
  pagesValue: document.getElementById("pages-value").value,
  pagesDate: document.getElementById("pages-date").value,
  revItem: document.getElementById("revenue-item").value,
  revValue: document.getElementById("revenue-value").value,
  trafDate: document.getElementById("traffic-date").value,
  trafValue: document.getElementById("traffic-value").value,
}));
const want = { pagesItem: "url", pagesValue: "pageviews", pagesDate: "published",
               revItem: "source", revValue: "amount",
               trafDate: "month", trafValue: "sessions" };
for (const [k, v] of Object.entries(want)) {
  if (guessed[k] !== v) fail(`column guess ${k}: got "${guessed[k]}", expected "${v}"`);
}
console.log("  ok    all 7 columns auto-detected");

// ---- build ---------------------------------------------------------------
await page.fill("#client", "Coffee content site — listing #A-2291");
await page.fill("#prepared", "a prospective buyer");
await page.click("#build");
await page.waitForSelector("#report-wrap:not([hidden])");

const report = await page.evaluate(() => {
  const findings = [...document.querySelectorAll("#report .f")].map(f => ({
    sev: f.querySelector(".sev").textContent.trim(),
    title: f.querySelector(".t").textContent.trim(),
  }));
  return {
    findings,
    sections: [...document.querySelectorAll("#report section h2")].map(h => h.textContent.trim()),
    svgCount: document.querySelectorAll("#report svg").length,
    gaps: [...document.querySelectorAll("#report .gaps li")].map(li => li.textContent.trim()),
    footer: document.querySelector("#report .rep-foot").textContent,
    downloadEnabled: !document.getElementById("download").disabled,
  };
});

if (consoleErrors.length) fail("page errors:\n  " + consoleErrors.join("\n  "));

const titles = report.findings.map(f => f.title);
const required = ["Revenue concentration", "Production up, yield down",
                  "Sustained decline detected"];
for (const r of required) {
  if (!titles.includes(r)) fail(`missing expected finding "${r}" (got: ${titles.join(", ")})`);
}
const rank = { critical: 0, major: 1, note: 2, clear: 3 };
const order = report.findings.map(f => rank[f.sev]);
if (order.some((v, i) => i && v < order[i - 1])) {
  fail("findings are not ranked most-severe first: " +
       report.findings.map(f => f.sev).join(", "));
}
if (report.svgCount < 3) fail(`expected at least 3 charts, got ${report.svgCount}`);
if (!report.gaps.length) fail("report did not state what it fails to establish");
if (!/not a valuation/i.test(report.footer)) fail("footer is missing the disclaimer");
if (!/Built with Reportcraft/.test(report.footer)) fail("footer is missing attribution");
if (!report.downloadEnabled) fail("download stayed disabled after a successful build");

console.log(`  ok    ${report.findings.length} findings, ranked, ` +
            `${report.svgCount} charts, ${report.gaps.length} stated limits`);
console.log(`  ok    sections: ${report.sections.join(" · ")}`);

// ---- download produces a standalone file ---------------------------------
const dir = mkdtempSync(join(tmpdir(), "rc-"));
const [download] = await Promise.all([
  page.waitForEvent("download"),
  page.click("#download"),
]);
const saved = join(dir, "report.html");
await download.saveAs(saved);
const html = readFileSync(saved, "utf8");
if (!html.startsWith("<!doctype html>")) fail("downloaded file is not a document");
const scan = html.replace(/xmlns="http:\/\/www\.w3\.org\/2000\/svg"/g, "");
for (const bad of ["http://", "https://", "<script", "fetch(", "@import"]) {
  if (scan.includes(bad)) fail(`downloaded report is not self-contained: ${bad}`);
}
if (!html.includes("Built with Reportcraft")) fail("attribution missing from the download");
if (!html.includes("prefers-color-scheme")) fail("downloaded report has no dark theme");
console.log(`  ok    download is standalone (${html.length.toLocaleString()} bytes, ` +
            `no scripts, no network)`);

// ---- a bad file must fail cleanly, not silently ---------------------------
const badDir = mkdtempSync(join(tmpdir(), "rc-bad-"));
const badFile = join(badDir, "tiny.csv");
const { writeFileSync } = await import("node:fs");
writeFileSync(badFile, "url,views\nonly,5\n");
await page.setInputFiles("#pages-input", badFile);
await page.waitForTimeout(150);
await page.click("#build");
await page.waitForSelector("#notes .note.error", { timeout: 3000 })
  .catch(() => fail("a 1-row file did not produce a visible error"));
const err = await page.textContent("#notes .note.error");
if (!/below 3/.test(err)) fail(`error message is unhelpful: ${err}`);
console.log("  ok    a too-small file fails with a message that names the fix");

if (shot) {
  await page.setInputFiles("#pages-input", join(SAMPLE, "pages.csv"));
  await page.waitForTimeout(200);
  await page.click("#build");
  await page.waitForSelector("#report-wrap:not([hidden])");
  await page.screenshot({ path: shot, fullPage: true });
  console.log(`  ok    screenshot → ${shot}`);
}

await browser.close();
console.log("browsertest: the tool works end to end");
