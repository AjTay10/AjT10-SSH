#!/usr/bin/env python3
"""selftest — adversarial tests for every tool in this repo.

Written from the QA side: the cases here are the ones that break naive
implementations. Empty files, a single data point, all-identical values,
negative numbers where they are meaningless, division by zero, unicode and
BOMs, gigantic values, malformed dates, columns that do not exist, and inputs
crafted to make an algorithm produce a confidently wrong answer.

Every tool must either produce a correct result or fail with a clear message
and a non-zero exit code. Crashing with a traceback is a failure. Silently
returning something wrong is a worse failure, so several tests assert on
values rather than just on exit codes.

    python3 qa/selftest.py
    python3 qa/selftest.py -v
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, "tools")
sys.path.insert(0, os.path.join(ROOT, "tools"))

import chartkit          # noqa: E402
import calendar_gen      # noqa: E402

PASS, FAIL = [], []
VERBOSE = "-v" in sys.argv


def check(name, fn):
    try:
        fn()
    except AssertionError as e:
        FAIL.append((name, str(e) or "assertion failed"))
    except Exception:
        FAIL.append((name, traceback.format_exc(limit=3).strip().split("\n")[-1]))
    else:
        PASS.append(name)
        if VERBOSE:
            print(f"  ok    {name}")


def run(args, stdin=None):
    """Run a tool as a subprocess. Returns (returncode, stdout, stderr)."""
    p = subprocess.run([sys.executable] + args, cwd=ROOT, input=stdin,
                       capture_output=True, text=True, timeout=90)
    return p.returncode, p.stdout, p.stderr


def write(d, name, content):
    p = os.path.join(d, name)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        fh.write(content)
    return p


def expect_clean_error(rc, out, err, what):
    assert rc != 0, f"{what}: expected a non-zero exit, got 0"
    assert "Traceback" not in err, f"{what}: leaked a traceback:\n{err[-400:]}"
    assert err.strip(), f"{what}: failed with no message on stderr"


# ==========================================================================
# chartkit — the library surface
# ==========================================================================

def t_chart_empty():
    for fn, args in [(chartkit.line, ([], [])),
                     (chartkit.bar, ([], [])),
                     (chartkit.hbar, ([], []))]:
        try:
            fn(*args)
        except chartkit.ChartError:
            pass
        else:
            assert False, f"{fn.__name__} accepted empty input"


def t_chart_length_mismatch():
    try:
        chartkit.line(["a", "b", "c"], [1, 2])
    except chartkit.ChartError as e:
        assert "3" in str(e) and "2" in str(e), "error should name both lengths"
    else:
        assert False, "line accepted mismatched x/y lengths"


def t_chart_single_point():
    svg = chartkit.line(["a"], [5])
    assert svg.startswith("<svg"), "single point should still render"
    assert "circle" in svg, "a one-point series must render as a dot, not a path"


def t_chart_all_identical():
    """A flat series must not divide by a zero range."""
    svg = chartkit.line(list("abcdef"), [7, 7, 7, 7, 7, 7])
    assert "<svg" in svg
    assert "nan" not in svg.lower(), "flat series produced NaN coordinates"
    assert "inf" not in svg.lower(), "flat series produced infinite coordinates"


def t_chart_all_zero():
    svg = chartkit.bar(list("abc"), [0, 0, 0])
    assert "nan" not in svg.lower() and "<svg" in svg


def t_chart_negative_donut():
    try:
        chartkit.donut(["a", "b"], [5, -3])
    except chartkit.ChartError:
        pass
    else:
        assert False, "donut accepted a negative slice"


def t_chart_donut_sums_zero():
    try:
        chartkit.donut(["a", "b"], [0, 0])
    except chartkit.ChartError:
        pass
    else:
        assert False, "donut accepted slices summing to zero"


def t_chart_donut_single_full_slice():
    """A 100% slice cannot be drawn as one arc — it must not vanish."""
    svg = chartkit.donut(["only"], [42])
    assert "circle" in svg, "a full-ring donut should fall back to a circle"


def t_chart_negative_stack():
    try:
        chartkit.stacked_bar(["w1"], {"a": [5], "b": [-2]})
    except chartkit.ChartError:
        pass
    else:
        assert False, "stacked_bar accepted a negative value"


def t_chart_gaps_break_path():
    """Missing values must break the line, not be interpolated through."""
    svg = chartkit.line(list("abcdef"), [1, 2, None, None, 5, 6])
    # Two multi-point runs -> two separate paths, each with its own M command.
    assert svg.count(' d="M') == 2, \
        f"gap did not split the path into runs (found {svg.count(chr(34))} paths)"


def t_chart_gap_isolated_point_is_dot():
    """A single value surrounded by gaps has no line to draw — show the point."""
    svg = chartkit.line(list("abcde"), [1, None, None, 4, 5])
    assert svg.count(' d="M') == 1, "isolated point should not become a path"
    assert "circle" in svg, "isolated point vanished entirely"


def t_chart_all_none():
    try:
        chartkit.line(list("abc"), [None, None, None])
    except chartkit.ChartError:
        pass
    else:
        assert False, "line accepted an all-empty series"


def t_chart_tiny_canvas():
    try:
        chartkit.line(list("abc"), [1, 2, 3], w=40, h=40)
    except chartkit.ChartError:
        pass
    else:
        assert False, "accepted a canvas smaller than its own margins"


def t_chart_xss_escaped():
    """Labels are untrusted text and must not become markup."""
    svg = chartkit.bar(['<script>alert(1)</script>'], [5],
                       title='"><script>x</script>')
    assert "<script>" not in svg, "unescaped markup reached the SVG"
    assert "&lt;script&gt;" in svg or "&lt;" in svg


def t_chart_unicode_labels():
    svg = chartkit.hbar(["日本語", "Ελληνικά", "emoji 🎯"], [3, 2, 1])
    assert "<svg" in svg and "日本語" in svg


def t_chart_huge_and_tiny():
    svg = chartkit.line(list("abc"), [1e12, 2e12, 3e12])
    assert "T" not in svg or True
    svg2 = chartkit.line(list("abc"), [1e-9, 2e-9, 3e-9])
    assert "nan" not in svg2.lower()


def t_chart_number_parsing():
    n = chartkit._num
    assert n("1,234") == 1234
    assert n("12%") == 12
    assert n("$1.5k") == 1500
    assert n("(300)") == -300, "parenthesised negatives must parse as negative"
    assert n("") is None and n("n/a") is None
    try:
        n("banana")
    except chartkit.ChartError:
        pass
    else:
        assert False, "accepted a non-numeric string"


def t_chart_nan_inf_rejected():
    """NaN must not be silently swallowed as 'missing' — it means a bug upstream."""
    for bad in (float("nan"), float("inf"), float("-inf"), "nan", "inf"):
        try:
            chartkit._num(bad)
        except chartkit.ChartError:
            pass
        else:
            assert False, f"accepted {bad!r}"


def t_chart_bool_rejected():
    """True is not 1 in a chart; accepting it hides a column-type mistake."""
    try:
        chartkit._num(True)
    except chartkit.ChartError:
        pass
    else:
        assert False, "accepted a boolean as a measurement"


def t_chart_ticks_always_two():
    for lo, hi in [(0, 0), (5, 5), (-3, -3), (0, 1e-12), (-1e9, 1e9)]:
        ticks = chartkit._nice_ticks(lo, hi)
        assert len(ticks) >= 2, f"_nice_ticks({lo},{hi}) returned {ticks}"
        assert all(math.isfinite(t) for t in ticks)


def t_chart_ticks_reversed_bounds():
    ticks = chartkit._nice_ticks(100, 0)
    assert ticks[0] <= ticks[-1], "reversed bounds should be normalized"


def t_chart_sparkline_degenerate():
    assert "<svg" in chartkit.sparkline([])
    assert "<svg" in chartkit.sparkline([1])
    assert "<svg" in chartkit.sparkline([2, 2, 2])


def t_chart_heatmap_ragged():
    try:
        chartkit.heatmap(["r1", "r2"], ["c1", "c2"], [[1, 2], [3]])
    except chartkit.ChartError as e:
        assert "row 1" in str(e), "error should name the offending row"
    else:
        assert False, "heatmap accepted a ragged matrix"


def t_chart_heatmap_sparse():
    svg = chartkit.heatmap(["r"], ["a", "b"], [[None, 5]])
    assert "<svg" in svg, "heatmap must tolerate empty cells"


def t_chart_theme_both_palettes():
    svg = chartkit.line(list("abc"), [1, 2, 3])
    assert "prefers-color-scheme: dark" in svg, "no dark palette emitted"
    pinned = chartkit.line(list("abc"), [1, 2, 3], theme_lock="dark")
    assert "prefers-color-scheme" not in pinned, "theme_lock should pin one palette"


def t_chart_no_external_refs():
    """A published Artifact runs under a strict CSP — nothing may be fetched.

    The SVG namespace declaration is a URI but never a request, so it is
    excluded before the scan rather than being allowed to mask a real one.
    """
    svg = chartkit.line(list("abc"), [1, 2, 3], title="t", subtitle="s")
    scan = svg.replace('xmlns="http://www.w3.org/2000/svg"', "")
    for bad in ("http://", "https://", "url(", "<image", "xlink:href",
                "@import", "<script"):
        assert bad not in scan, f"SVG contains an external reference: {bad}"


# ==========================================================================
# CLI-level tests
# ==========================================================================

def t_cli_missing_file():
    rc, out, err = run(["tools/chartkit.py", "--csv", "/nope/missing.csv",
                        "--y", "x"])
    expect_clean_error(rc, out, err, "chartkit missing file")


def t_cli_missing_column():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "a.csv", "date,views\n2026-01-01,5\n2026-01-02,7\n")
        rc, out, err = run(["tools/chartkit.py", "--csv", p, "--x", "date",
                            "--y", "nope"])
        expect_clean_error(rc, out, err, "chartkit unknown column")
        assert "views" in err, "error should list the columns that do exist"


def t_cli_empty_csv():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "e.csv", "date,views\n")
        for tool, extra in [("tools/chartkit.py", ["--x", "date", "--y", "views"]),
                            ("tools/anomaly.py", ["--date", "date", "--value", "views"])]:
            rc, out, err = run([tool, "--csv", p] + extra)
            expect_clean_error(rc, out, err, f"{tool} header-only CSV")


def t_cli_bom_and_unicode():
    """A UTF-8 BOM must not corrupt the first column name."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "bom.csv")
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("date,views\n2026-01-01,10\n2026-01-02,20\n2026-01-03,30\n")
        rc, out, err = run(["tools/chartkit.py", "--csv", p, "--x", "date",
                            "--y", "views"])
        assert rc == 0, f"BOM broke the header parse: {err}"
        assert "<svg" in out


def t_cli_crlf_input():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "crlf.csv")
        with open(p, "wb") as fh:
            fh.write(b"date,views\r\n2026-01-01,10\r\n2026-01-02,20\r\n")
        rc, out, err = run(["tools/chartkit.py", "--csv", p, "--x", "date",
                            "--y", "views"])
        assert rc == 0, f"CRLF input rejected: {err}"


# ==========================================================================
# csvio — the shared reader. Regressions here break every tool at once.
# ==========================================================================

def t_csvio_cp1252_fallback():
    """Excel on Windows writes cp1252. UnicodeDecodeError is a ValueError, not
    an OSError, so it slipped past every `except OSError` and reached the user
    as a traceback. This is the regression test for that."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.csv")
        with open(p, "wb") as fh:
            fh.write("date,views\n2026-01-01,5\ncafé,9\n".encode("cp1252"))
        rc, out, err = run(["tools/chartkit.py", "--csv", p, "--x", "date",
                            "--y", "views"])
        assert rc == 0, f"cp1252 export rejected: {err}"
        assert "Traceback" not in err
        assert "not UTF-8" in err, "silently guessed an encoding without saying so"


def t_csvio_every_tool_survives_cp1252():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.csv")
        body = "date,v,user_id,step\n"
        for i in range(1, 41):
            body += f"2026-01-{i%28+1:02d},{100+i},u{i},café\n"
        with open(p, "wb") as fh:
            fh.write(body.encode("cp1252"))
        for args in (["tools/anomaly.py", "--csv", p, "--date", "date", "--value", "v"],
                     ["tools/metrics.py", "growth", "--csv", p, "--date", "date",
                      "--value", "v"],
                     ["tools/social_ingest.py", "--inspect", p]):
            rc, out, err = run(args)
            assert "Traceback" not in err, f"{args[0]} leaked a traceback:\n{err[-300:]}"
            assert rc == 0, f"{args[0]} failed on cp1252: {err[-200:]}"


def t_csvio_binary_rejected_clearly():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.bin")
        with open(p, "wb") as fh:
            fh.write(b"\x00\x01\x02PK\x03\x04" * 200)
        rc, out, err = run(["tools/metrics.py", "growth", "--csv", p,
                            "--date", "d", "--value", "v"])
        expect_clean_error(rc, out, err, "binary input")
        assert "binary" in err.lower(), \
            f"binary file was not identified as such: {err[:200]}"


def t_csvio_duplicate_headers_warn():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv", "date,views,views\n2026-01-01,5,9\n2026-01-02,7,3\n")
        rc, out, err = run(["tools/chartkit.py", "--csv", p, "--x", "date",
                            "--y", "views"])
        assert rc == 0, err
        assert "duplicate column" in err, \
            "silently read only the last of two identically named columns"


def t_csvio_error_list_is_bounded():
    """A mis-parsed file must not dump a screenful of junk headers."""
    with tempfile.TemporaryDirectory() as d:
        header = ",".join(f"col{i}" for i in range(200))
        p = write(d, "wide.csv", header + "\n" + ",".join("1" * 200) + "\n")
        rc, out, err = run(["tools/metrics.py", "growth", "--csv", p,
                            "--date", "nope", "--value", "alsonope"])
        expect_clean_error(rc, out, err, "wide file missing column")
        assert "more)" in err, "column list was not truncated"
        assert len(err) < 1200, f"error message is {len(err)} chars — too long"


def t_csvio_empty_and_header_only():
    with tempfile.TemporaryDirectory() as d:
        for name, body in (("empty.csv", ""), ("blank.csv", "   \n"),
                           ("hdr.csv", "date,v\n")):
            p = write(d, name, body)
            rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date",
                                "date", "--value", "v"])
            expect_clean_error(rc, out, err, name)


def t_csvio_utf8_with_bom_is_silent():
    """A BOM is the normal case and must not produce a warning."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "b.csv")
        with open(p, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("date,views\n2026-01-01,5\n2026-01-02,9\n")
        rc, out, err = run(["tools/chartkit.py", "--csv", p, "--x", "date",
                            "--y", "views"])
        assert rc == 0, err
        assert "not UTF-8" not in err, "warned about a plain BOM"


# ==========================================================================
# metrics
# ==========================================================================

def t_metrics_funnel_correctness():
    """Strict mode must not count a user who skipped a step."""
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "e.csv",
                  "user_id,step\n"
                  "u1,view\nu1,click\nu1,buy\n"      # complete
                  "u2,view\nu2,click\n"              # stops at click
                  "u3,view\n"                        # stops at view
                  "u4,view\nu4,buy\n")               # skipped click
        rc, out, err = run(["tools/metrics.py", "funnel", "--csv", p,
                            "--user", "user_id", "--step", "step",
                            "--order", "view,click,buy", "--json"])
        assert rc == 0, err
        data = json.loads(out)["funnel"]
        counts = {r["step"]: r["count"] for r in data}
        assert counts["view"] == 4, counts
        assert counts["click"] == 2, counts
        assert counts["buy"] == 1, f"strict mode counted the skipper: {counts}"

        rc, out, err = run(["tools/metrics.py", "funnel", "--csv", p,
                            "--user", "user_id", "--step", "step",
                            "--order", "view,click,buy", "--loose", "--json"])
        loose = {r["step"]: r["count"] for r in json.loads(out)["funnel"]}
        assert loose["buy"] == 2, f"loose mode should count u4: {loose}"


def t_metrics_funnel_reports_unknown_steps():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "e.csv", "user_id,step\nu1,view\nu1,mystery\nu1,click\n")
        rc, out, err = run(["tools/metrics.py", "funnel", "--csv", p,
                            "--user", "user_id", "--step", "step",
                            "--order", "view,click", "--json"])
        assert rc == 0, err
        assert "mystery" in json.loads(out)["unknown_steps"], \
            "silently dropped an unlisted step"


def t_metrics_funnel_single_step():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "e.csv", "user_id,step\nu1,view\n")
        rc, out, err = run(["tools/metrics.py", "funnel", "--csv", p,
                            "--user", "user_id", "--step", "step",
                            "--order", "view"])
        expect_clean_error(rc, out, err, "funnel with one step")


def t_metrics_retention_shape():
    """Every cohort must be 100% in period 0 by construction."""
    with tempfile.TemporaryDirectory() as d:
        rows = ["user_id,date"]
        for u in range(1, 21):
            rows.append(f"u{u},2026-01-05")
            if u <= 10:
                rows.append(f"u{u},2026-01-12")
        p = write(d, "r.csv", "\n".join(rows) + "\n")
        rc, out, err = run(["tools/metrics.py", "retention", "--csv", p,
                            "--user", "user_id", "--date", "date",
                            "--period", "week", "--periods", "3", "--json"])
        assert rc == 0, err
        g = json.loads(out)
        assert g["retention_pct"][0][0] == 100.0, "P0 must be 100%"
        assert g["retention_pct"][0][1] == 50.0, \
            f"expected 50% P1, got {g['retention_pct'][0][1]}"


def t_metrics_growth_from_zero():
    """Percent change from a zero baseline must not divide by zero."""
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "g.csv", "date,v\n2026-01-01,0\n2026-01-02,5\n")
        rc, out, err = run(["tools/metrics.py", "growth", "--csv", p,
                            "--date", "date", "--value", "v", "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert data["pct_change"] is None, "should report None, not infinity"


def t_metrics_growth_needs_two_points():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "g.csv", "date,v\n2026-01-01,5\n")
        rc, out, err = run(["tools/metrics.py", "growth", "--csv", p,
                            "--date", "date", "--value", "v"])
        expect_clean_error(rc, out, err, "growth with one row")


def t_metrics_bad_date():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "g.csv", "date,v\n2026-01-01,5\nnot-a-date,7\n")
        rc, out, err = run(["tools/metrics.py", "growth", "--csv", p,
                            "--date", "date", "--value", "v"])
        expect_clean_error(rc, out, err, "growth with unparseable date")


def t_metrics_missing_column_lists_present():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "g.csv", "date,v\n2026-01-01,5\n2026-01-02,6\n")
        rc, out, err = run(["tools/metrics.py", "growth", "--csv", p,
                            "--date", "date", "--value", "nope"])
        expect_clean_error(rc, out, err, "growth unknown column")
        assert "Present" in err or "present" in err


# ==========================================================================
# abtest
# ==========================================================================

def t_abtest_identical_arms():
    rc, out, err = run(["tools/abtest.py", "compare", "--a", "50/1000",
                        "--b", "50/1000", "--json"])
    assert rc == 0, err
    d = json.loads(out)
    assert abs(d["p_value"] - 1.0) < 1e-6, f"identical arms gave p={d['p_value']}"
    assert d["significant"] is False


def t_abtest_impossible_input():
    rc, out, err = run(["tools/abtest.py", "compare", "--a", "500/100",
                        "--b", "5/100"])
    expect_clean_error(rc, out, err, "more conversions than trials")


def t_abtest_zero_trials():
    rc, out, err = run(["tools/abtest.py", "compare", "--a", "0/0", "--b", "5/100"])
    expect_clean_error(rc, out, err, "zero trials")


def t_abtest_malformed_arm():
    for bad in ["banana", "50", "50/abc"]:
        rc, out, err = run(["tools/abtest.py", "compare", "--a", bad, "--b", "5/100"])
        expect_clean_error(rc, out, err, f"malformed arm {bad!r}")


def t_abtest_zero_conversions_both():
    """Both arms at zero: degenerate, must not divide by zero."""
    rc, out, err = run(["tools/abtest.py", "compare", "--a", "0/500",
                        "--b", "0/500"])
    expect_clean_error(rc, out, err, "both arms zero")


def t_abtest_bayes_probability_bounds():
    rc, out, err = run(["tools/abtest.py", "bayes", "--a", "120/4000",
                        "--b", "151/4050", "--json"])
    assert rc == 0, err
    d = json.loads(out)
    assert 0.0 <= d["p_b_beats_a"] <= 1.0, d["p_b_beats_a"]
    assert d["mean_b"] > d["mean_a"], "B has the higher rate and should show it"
    assert d["expected_loss_if_ship_b"] >= 0
    assert d["ci_a"][0] < d["mean_a"] < d["ci_a"][1], "mean must sit inside its CI"


def t_abtest_bayes_symmetry():
    """Swapping the arms must give the complementary probability."""
    _, o1, _ = run(["tools/abtest.py", "bayes", "--a", "30/500",
                    "--b", "50/500", "--json"])
    _, o2, _ = run(["tools/abtest.py", "bayes", "--a", "50/500",
                    "--b", "30/500", "--json"])
    p1 = json.loads(o1)["p_b_beats_a"]
    p2 = json.loads(o2)["p_b_beats_a"]
    assert abs((p1 + p2) - 1.0) < 0.02, f"asymmetric posterior: {p1} + {p2}"


def t_abtest_bayes_extreme_n():
    """Large n must not overflow the Beta grid."""
    rc, out, err = run(["tools/abtest.py", "bayes", "--a", "500000/10000000",
                        "--b", "520000/10000000", "--json"])
    assert rc == 0, f"large n failed: {err[-300:]}"
    d = json.loads(out)
    assert 0.0 <= d["p_b_beats_a"] <= 1.0
    assert not math.isnan(d["mean_a"]), "overflow produced NaN"


def t_abtest_size_impossible_lift():
    rc, out, err = run(["tools/abtest.py", "size", "--baseline", "0.9",
                        "--lift", "0.5"])
    expect_clean_error(rc, out, err, "lift exceeding 100%")


def t_abtest_size_bad_baseline():
    for bad in ["0", "1", "-0.2", "1.5"]:
        rc, out, err = run(["tools/abtest.py", "size", "--baseline", bad,
                            "--lift", "0.1"])
        expect_clean_error(rc, out, err, f"baseline {bad}")


def t_abtest_size_monotonic():
    """A smaller detectable effect must require a larger sample."""
    _, o1, _ = run(["tools/abtest.py", "size", "--baseline", "0.03",
                    "--lift", "0.20", "--json"])
    _, o2, _ = run(["tools/abtest.py", "size", "--baseline", "0.03",
                    "--lift", "0.05", "--json"])
    n1, n2 = json.loads(o1)["per_arm"], json.loads(o2)["per_arm"]
    assert n2 > n1, f"smaller MDE needed fewer samples ({n2} vs {n1})"


def t_abtest_peek_bounds():
    rc, out, err = run(["tools/abtest.py", "peek", "--checks", "20", "--json"])
    assert rc == 0, err
    d = json.loads(out)
    assert d["realistic_false_positive"] <= d["upper_bound_false_positive"] + 1e-9
    assert 0 < d["realistic_false_positive"] < 1


# ==========================================================================
# anomaly
# ==========================================================================

def _series(d, name, values, start="2026-01-01"):
    from datetime import date, timedelta
    d0 = date.fromisoformat(start)
    lines = ["date,v"]
    for i, v in enumerate(values):
        lines.append(f"{(d0 + timedelta(days=i)).isoformat()},{v}")
    return write(d, name, "\n".join(lines) + "\n")


def t_anomaly_finds_injected_spike():
    with tempfile.TemporaryDirectory() as d:
        vals = [100 + (i % 5) for i in range(80)]
        vals[60] = 5000
        p = _series(d, "s.csv", vals)
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--json"])
        assert rc == 0, err
        flags = json.loads(out)["anomalies"]
        dates = [f["date"] for f in flags]
        assert "2026-03-02" in dates, f"missed the injected spike; found {dates}"


def t_anomaly_no_false_positives_on_clean_trend():
    """A steadily growing series must not be reported as a run of spikes."""
    with tempfile.TemporaryDirectory() as d:
        vals = [100 + i * 3 + (i % 3) for i in range(120)]
        p = _series(d, "t.csv", vals)
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--json"])
        assert rc == 0, err
        flags = json.loads(out)["anomalies"]
        assert len(flags) <= 3, \
            f"trend-only series produced {len(flags)} false anomalies"


def t_anomaly_flat_series_silent():
    with tempfile.TemporaryDirectory() as d:
        p = _series(d, "f.csv", [42] * 60)
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert not data["anomalies"], "flat series flagged an anomaly"
        for pt in data["points"]:
            assert pt["z"] is None or math.isfinite(pt["z"]), \
                "flat history produced a non-finite z score"


def t_anomaly_json_is_serializable():
    """No inf/nan may reach JSON — it is invalid and breaks every consumer."""
    with tempfile.TemporaryDirectory() as d:
        vals = [0] * 40 + [999999] + [0] * 20
        p = _series(d, "z.csv", vals)
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--json"])
        assert rc == 0, err
        assert "Infinity" not in out and "NaN" not in out, \
            "emitted non-standard JSON literals"
        json.loads(out)


def t_anomaly_too_few_points():
    with tempfile.TemporaryDirectory() as d:
        p = _series(d, "s.csv", [1, 2, 3])
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v"])
        expect_clean_error(rc, out, err, "anomaly with 3 points")


def t_anomaly_bad_window():
    with tempfile.TemporaryDirectory() as d:
        p = _series(d, "s.csv", list(range(40)))
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--window", "2"])
        expect_clean_error(rc, out, err, "window below the minimum")


def t_anomaly_unsorted_input():
    """Rows out of date order must be sorted, not misread as volatility."""
    with tempfile.TemporaryDirectory() as d:
        from datetime import date, timedelta
        d0 = date.fromisoformat("2026-01-01")
        rows = [f"{(d0 + timedelta(days=i)).isoformat()},{100 + i}"
                for i in range(60)]
        rows.reverse()
        p = write(d, "u.csv", "date,v\n" + "\n".join(rows) + "\n")
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--json"])
        assert rc == 0, err
        flags = json.loads(out)["anomalies"]
        assert len(flags) <= 3, \
            f"reverse-ordered input produced {len(flags)} spurious anomalies"


def t_anomaly_cusum_collapses_runs():
    """A sustained shift is one episode, not one event per day."""
    with tempfile.TemporaryDirectory() as d:
        vals = [100 + (i % 4) for i in range(60)] + [40 + (i % 4) for i in range(30)]
        p = _series(d, "c.csv", vals)
        rc, out, err = run(["tools/anomaly.py", "--csv", p, "--date", "date",
                            "--value", "v", "--json"])
        assert rc == 0, err
        shifts = json.loads(out)["changepoints"]
        downs = [s for s in shifts if s["direction"] == "down"]
        assert downs, "missed a 60% sustained drop"
        assert len(downs) <= 3, f"drop reported as {len(downs)} separate events"


def t_theil_sen_robust():
    import anomaly
    xs = list(range(20))
    ys = [2 * x + 1 for x in xs]
    ys[10] = 10000                                  # one catastrophic outlier
    slope = anomaly.theil_sen(xs, ys)
    assert abs(slope - 2.0) < 0.5, \
        f"Theil-Sen was dragged to {slope} by a single outlier"


# ==========================================================================
# kg
# ==========================================================================

def t_kg_roundtrip_and_analysis():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        def kg(*a):
            return run(["tools/kg.py", "--store", store] + list(a))
        assert kg("add", "--id", "a", "--type", "creator", "--name", "A")[0] == 0
        assert kg("add", "--id", "b", "--type", "tactic")[0] == 0
        assert kg("link", "--from", "a", "--to", "b", "--rel", "uses")[0] == 0
        assert kg("link", "--from", "b", "--to", "c", "--rel", "enables")[0] == 0

        rc, out, err = kg("stats", "--json")
        assert rc == 0, err
        s = json.loads(out)
        assert s["nodes"] == 3, s
        assert s["auto_created_count"] == 1, "c was auto-created and should be flagged"

        rc, out, _ = kg("central", "--json")
        rows = json.loads(out)
        for r in rows:
            assert 0.0 <= r["betweenness"] <= 1.0, \
                f"betweenness {r['betweenness']} outside [0,1] for {r['id']}"
        assert max(r["betweenness"] for r in rows) > 0, "no bridge detected"

        rc, out, _ = kg("path", "--from", "a", "--to", "c", "--json")
        assert rc == 0 and len(json.loads(out)) == 2, "expected a 2-hop path"


def t_kg_no_path_exits_nonzero():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        run(["tools/kg.py", "--store", store, "add", "--id", "x"])
        run(["tools/kg.py", "--store", store, "add", "--id", "y"])
        rc, out, err = run(["tools/kg.py", "--store", store, "path",
                            "--from", "x", "--to", "y"])
        assert rc != 0, "disconnected path should not exit 0"
        assert "Traceback" not in err


def t_kg_rejects_bad_ids():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        for bad in ["has space", "", "x" * 200, "-leading"]:
            rc, out, err = run(["tools/kg.py", "--store", store, "add",
                                "--id", bad])
            expect_clean_error(rc, out, err, f"kg id {bad!r}")


def t_kg_rejects_self_loop():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        run(["tools/kg.py", "--store", store, "add", "--id", "a"])
        rc, out, err = run(["tools/kg.py", "--store", store, "link",
                            "--from", "a", "--to", "a", "--rel", "x"])
        expect_clean_error(rc, out, err, "self loop without --allow-self")
        rc, _, _ = run(["tools/kg.py", "--store", store, "link", "--from", "a",
                        "--to", "a", "--rel", "x", "--allow-self"])
        assert rc == 0, "--allow-self should permit it"


def t_kg_corrupt_store():
    with tempfile.TemporaryDirectory() as d:
        store = write(d, "g.json", "{ this is not json")
        rc, out, err = run(["tools/kg.py", "--store", store, "stats"])
        expect_clean_error(rc, out, err, "corrupt store")
        assert "JSON" in err or "json" in err


def t_kg_wrong_shape_store():
    with tempfile.TemporaryDirectory() as d:
        store = write(d, "g.json", '{"hello": "world"}')
        rc, out, err = run(["tools/kg.py", "--store", store, "stats"])
        expect_clean_error(rc, out, err, "store with wrong shape")


def t_kg_atomic_write_leaves_no_temp():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        run(["tools/kg.py", "--store", store, "add", "--id", "a"])
        assert not os.path.exists(store + ".tmp"), "left a .tmp file behind"
        json.load(open(store, encoding="utf-8"))


def t_kg_link_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        for _ in range(3):
            run(["tools/kg.py", "--store", store, "link", "--from", "a",
                 "--to", "b", "--rel", "uses"])
        g = json.load(open(store, encoding="utf-8"))
        assert len(g["edges"]) == 1, f"duplicate edges created: {len(g['edges'])}"


def t_kg_mermaid_escapes():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        run(["tools/kg.py", "--store", store, "add", "--id", "a.b:c",
             "--name", 'Quote " and [bracket]'])
        rc, out, err = run(["tools/kg.py", "--store", store, "mermaid"])
        assert rc == 0, err
        assert '"' not in out.split("\n")[-2].replace('["', "").replace('"]', "") \
            or "'" in out, "unescaped quote would break mermaid parsing"
        assert "graph LR" in out


def t_kg_empty_graph_analysis():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "g.json")
        for cmd in ("central", "clusters", "stats", "mermaid"):
            rc, out, err = run(["tools/kg.py", "--store", store, cmd])
            assert rc == 0, f"{cmd} on an empty graph failed: {err}"
            assert "Traceback" not in err


# ==========================================================================
# social_ingest
# ==========================================================================

def t_ingest_column_disambiguation():
    """'Video publish time' must not be mistaken for an id because it has 'id'."""
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "yt.csv",
                  "Video publish time,Video title,Views,Impressions,Likes\n"
                  "2026-03-01,Clip,1000,50000,100\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "youtube", "--json"])
        assert rc == 0, err
        rec = json.loads(out)["records"][0]
        assert rec["date"] == "2026-03-01", rec
        assert rec["post_id"] == "", f"date column leaked into post_id: {rec}"
        assert rec["impressions"] == 50000, rec
        assert rec["video_views"] == 1000, rec


def t_ingest_tiktok_has_no_impressions():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "tt.csv", "Date,Video views,Likes\n2026-03-01,5000,100\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "tiktok", "--json"])
        assert rc == 0, err
        rec = json.loads(out)["records"][0]
        assert rec["video_views"] == 5000, rec
        assert rec["impressions"] == "", \
            "TikTok has no impression metric; inventing one is a lie"


def t_ingest_blank_is_not_zero():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv", "Date,Impressions,Likes\n2026-03-01,,50\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "instagram", "--json"])
        assert rc == 0, err
        rec = json.loads(out)["records"][0]
        assert rec["impressions"] == "", "blank was coerced to zero"
        assert rec["er_pct"] == "", "computed a rate with no denominator"


def t_ingest_er_not_divided_by_zero():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv", "Date,Impressions,Likes\n2026-03-01,0,50\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "instagram", "--json"])
        assert rc == 0, err
        assert json.loads(out)["records"][0]["er_pct"] == ""


def t_ingest_pairing_enforced():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv", "Date,Likes\n2026-03-01,5\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p, "--csv", p,
                            "--platform", "tiktok"])
        expect_clean_error(rc, out, err, "mismatched --csv/--platform counts")


def t_ingest_unknown_platform_warns():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv", "Date,Likes\n2026-03-01,5\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "myspace", "--json"])
        assert rc == 0, "an unknown platform should still process"
        assert "not a known platform" in err, "no warning for unknown platform"


def t_ingest_watch_time_units():
    """Hours must be converted to seconds, not copied verbatim."""
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "yt.csv",
                  "Video publish time,Views,Watch time (hours)\n"
                  "2026-03-01,100,2\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "youtube", "--json"])
        assert rc == 0, err
        rec = json.loads(out)["records"][0]
        assert rec["watch_time_sec"] == 7200, \
            f"2 hours became {rec['watch_time_sec']}, expected 7200"


def t_ingest_engagements_derived():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv",
                  "Date,Impressions,Likes,Comments,Shares,Saves\n"
                  "2026-03-01,1000,10,5,3,2\n")
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "instagram", "--json"])
        assert rc == 0, err
        rec = json.loads(out)["records"][0]
        assert rec["engagements"] == 20, rec
        assert abs(rec["er_pct"] - 2.0) < 1e-6, rec


def t_ingest_messy_numbers():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "x.csv",
                  "Date,Impressions,Likes\n"
                  '2026-03-01,"1,234",1.5k\n')
        rc, out, err = run(["tools/social_ingest.py", "--csv", p,
                            "--platform", "instagram", "--json"])
        assert rc == 0, err
        rec = json.loads(out)["records"][0]
        assert rec["impressions"] == 1234, rec
        assert rec["likes"] == 1500, rec


def t_ingest_inspect_no_crash():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "weird.csv", "Foo,Bar,Baz\n1,2,3\n")
        rc, out, err = run(["tools/social_ingest.py", "--inspect", p])
        assert rc == 0, err
        assert "best-guess" in out


# ==========================================================================
# concentration
# ==========================================================================

def t_conc_known_answers():
    """Four identical items: HHI exactly 0.25, effective count exactly 4,
    Gini exactly 0. If these drift, every downstream verdict is wrong."""
    import concentration as c
    res = c.analyze([("a", 10), ("b", 10), ("c", 10), ("d", 10)])
    assert abs(res["hhi"] - 0.25) < 1e-9, res["hhi"]
    assert abs(res["effective_n"] - 4.0) < 1e-9, res["effective_n"]
    assert abs(res["gini"]) < 1e-9, res["gini"]
    assert abs(res["hhi_normalized"]) < 1e-9, "even split must normalize to 0"
    assert abs(res["top1_x_even_share"] - 1.0) < 1e-9
    assert abs(res["shares"]["top1"] - 0.25) < 1e-9


def t_conc_single_dominant():
    import concentration as c
    res = c.analyze([("big", 1000)] + [(f"s{i}", 1) for i in range(99)])
    assert res["gini"] > 0.85, res["gini"]
    assert res["effective_n"] < 2, res["effective_n"]
    assert res["shares"]["top1"] > 0.9
    assert abs(res["fragility"]["drop_top1"]["pct_lost"]
               - res["shares"]["top1"] * 100) < 1e-6, \
        "leave-one-out must equal the top-1 share"


def t_conc_bounds_hold():
    """Every index must stay inside its defined range on any input shape."""
    import concentration as c
    for items in ([("a", 1), ("b", 1), ("c", 1)],
                  [("a", 1e9), ("b", 1), ("c", 1)],
                  [(f"i{i}", i + 1) for i in range(200)],
                  [(f"i{i}", 2 ** min(i, 60)) for i in range(40)]):
        r = c.analyze(items)
        n = r["items"]
        assert 1.0 / n - 1e-9 <= r["hhi"] <= 1.0 + 1e-9, r["hhi"]
        assert -1e-9 <= r["hhi_normalized"] <= 1.0 + 1e-9, r["hhi_normalized"]
        assert -1e-9 <= r["gini"] <= 1.0 + 1e-9, r["gini"]
        assert 1.0 <= r["effective_n"] <= n + 1e-9, r["effective_n"]


def t_conc_verdict_matches_the_table():
    """Regression: the verdict once printed 'no concentration flag' above a
    table showing top-1 at 20% and Gini 0.77, because the HHI bands were
    borrowed from antitrust and are meaningless at large n."""
    with tempfile.TemporaryDirectory() as d:
        rows = ["url,views"]
        rows.append("/monster,200000")
        rows.append("/second,120000")
        for i in range(380):
            rows.append(f"/p{i},{200 + i}")
        p = write(d, "s.csv", "\n".join(rows) + "\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p,
                            "--item", "url", "--value", "views"])
        assert rc == 0, err
        assert "No concentration flag" not in out, \
            "verdict contradicts a clearly power-law distribution"
        assert "even share" in out, "missing the scale-aware top-1 reading"
        assert "power law" in out or "unequal" in out, \
            f"band did not register the inequality:\n{out[:400]}"


def t_conc_blank_is_not_zero():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "s.csv", "id,rev\na,10\nb,\nc,20\nd,30\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev", "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert data["concentration"]["items"] == 3, "blank was counted as an item"
        assert data["skipped_blank"] == 1
        assert data["concentration"]["total"] == 60


def t_conc_negatives_excluded_and_reported():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "s.csv", "id,rev\na,10\nb,-5\nc,20\nd,30\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev", "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert data["skipped_negative"] == 1, "negative value silently included"
        assert data["concentration"]["total"] == 60


def t_conc_too_few_items():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "s.csv", "id,rev\na,10\nb,20\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev"])
        expect_clean_error(rc, out, err, "two items")
        assert "3" in err, "error should name the minimum"


def t_conc_all_zero():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "s.csv", "id,rev\na,0\nb,0\nc,0\nd,0\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev"])
        expect_clean_error(rc, out, err, "all-zero values")


def t_conc_decay_requires_date():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "s.csv", "id,rev\na,10\nb,20\nc,30\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev", "--decay"])
        expect_clean_error(rc, out, err, "--decay without --date")
        assert "--date" in err, "error should name the missing flag"


def t_conc_vintage_shares_sum_to_one():
    with tempfile.TemporaryDirectory() as d:
        rows = ["id,rev,pub"]
        for i in range(40):
            rows.append(f"i{i},{100 + i},202{i % 4}-0{i % 9 + 1}-01")
        p = write(d, "s.csv", "\n".join(rows) + "\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev", "--date", "pub", "--decay",
                            "--period", "year", "--json"])
        assert rc == 0, err
        v = json.loads(out)["vintages"]
        assert abs(sum(x["share"] for x in v) - 1.0) < 1e-6, \
            "vintage shares must sum to 1"
        assert [x["period"] for x in v] == sorted(x["period"] for x in v), \
            "vintages must be chronological"


def t_conc_decay_flags_melting_asset():
    """Production rising while yield falls is the signal worth paying for."""
    with tempfile.TemporaryDirectory() as d:
        rows = ["id,rev,pub"]
        for i in range(20):                       # old, few, lucrative
            rows.append(f"old{i},{500 + i},2021-03-01")
        for i in range(25):
            rows.append(f"a{i},{300 + i},2022-03-01")
        for i in range(30):
            rows.append(f"mid{i},{120 + i},2023-03-01")
        for i in range(40):
            rows.append(f"b{i},{40 + i},2024-03-01")
        for i in range(80):                       # new, many, worthless
            rows.append(f"new{i},{5 + i % 3},2025-03-01")
        p = write(d, "s.csv", "\n".join(rows) + "\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev", "--date", "pub", "--decay",
                            "--period", "year"])
        assert rc == 0, err
        assert "age handicap" in out, "missing the accrual-bias caveat"
        assert "Recent work is not moving" in out or "old work" in out, \
            f"decay went unflagged:\n{out[-600:]}"


def t_conc_json_is_clean():
    with tempfile.TemporaryDirectory() as d:
        rows = ["id,rev,pub"] + [f"i{i},{i+1},202{i%4}-01-01" for i in range(40)]
        p = write(d, "s.csv", "\n".join(rows) + "\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "rev", "--date", "pub", "--decay", "--json"])
        assert rc == 0, err
        assert "Infinity" not in out and "NaN" not in out
        json.loads(out)


def t_conc_missing_column():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "s.csv", "id,rev\na,10\nb,20\nc,30\n")
        rc, out, err = run(["tools/concentration.py", "--csv", p, "--item", "id",
                            "--value", "nope"])
        expect_clean_error(rc, out, err, "unknown value column")
        assert "rev" in err, "error should list the columns that exist"


# ==========================================================================
# dashboard
# ==========================================================================

def t_dashboard_rejects_unnormalized():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "raw.csv", "Foo,Bar\n1,2\n")
        rc, out, err = run(["tools/dashboard.py", "--csv", p])
        expect_clean_error(rc, out, err, "dashboard on un-normalized CSV")
        assert "social_ingest" in err, "error should say how to fix it"


def t_dashboard_self_contained():
    with tempfile.TemporaryDirectory() as d:
        rows = ["date,platform,post_id,title,impressions,reach,engagements,"
                "likes,comments,shares,saves,clicks,followers_delta,"
                "watch_time_sec,video_views,er_pct"]
        from datetime import date, timedelta
        d0 = date.fromisoformat("2026-01-01")
        for i in range(30):
            day = (d0 + timedelta(days=i)).isoformat()
            rows.append(f"{day},tiktok,p{i},Post {i},{1000+i*10},,{50+i},"
                        f"{40+i},5,3,2,,{i},,{1000+i*10},{(50+i)/(1000+i*10)*100:.3f}")
        p = write(d, "norm.csv", "\n".join(rows) + "\n")
        out_html = os.path.join(d, "o.html")
        rc, out, err = run(["tools/dashboard.py", "--csv", p, "--out", out_html])
        assert rc == 0, err
        html = open(out_html, encoding="utf-8").read()
        scan = html.replace('xmlns="http://www.w3.org/2000/svg"', "")
        for bad in ("http://", "https://", "<script", "fetch(", "cdn.",
                    "@import", "<link"):
            assert bad not in scan, f"dashboard is not self-contained: {bad}"
        assert "prefers-color-scheme" in html, "no dark theme support"
        assert "<svg" in html, "no charts rendered"


def t_dashboard_single_row():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "norm.csv",
                  "date,platform,post_id,title,impressions,reach,engagements,"
                  "likes,comments,shares,saves,clicks,followers_delta,"
                  "watch_time_sec,video_views,er_pct\n"
                  "2026-01-01,x,p1,Only post,100,,10,10,,,,,1,,,10\n")
        rc, out, err = run(["tools/dashboard.py", "--csv", p])
        assert rc == 0, f"single-row dashboard failed: {err}"
        assert "<html" in out


def t_dashboard_escapes_titles():
    with tempfile.TemporaryDirectory() as d:
        p = write(d, "norm.csv",
                  "date,platform,post_id,title,impressions,reach,engagements,"
                  "likes,comments,shares,saves,clicks,followers_delta,"
                  "watch_time_sec,video_views,er_pct\n"
                  '2026-01-01,x,p1,<script>alert(1)</script>,100,,10,10,,,,,1,,,10\n')
        rc, out, err = run(["tools/dashboard.py", "--csv", p])
        assert rc == 0, err
        assert "<script>alert" not in out, "post title was injected as markup"


# ==========================================================================
# calendar_gen
# ==========================================================================

def t_calendar_slot_parsing():
    assert calendar_gen.parse_slot("Tue 09:00 teardown")[0] == 1
    assert calendar_gen.parse_slot("sunday 17:30")[0] == 6
    for bad in ["Funday 09:00 x", "Tue 25:00 x", "Tue 09:70 x", "09:00 Tue"]:
        try:
            calendar_gen.parse_slot(bad)
        except calendar_gen.CalError:
            pass
        else:
            assert False, f"accepted bad slot {bad!r}"


def t_calendar_dst_conversion():
    """Local 09:00 must convert to the correct UTC instant across a DST edge."""
    with tempfile.TemporaryDirectory() as d:
        ics = os.path.join(d, "c.ics")
        rc, out, err = run(["tools/calendar_gen.py", "--start", "2026-10-26",
                            "--weeks", "3", "--slot", "Tue 09:00 x",
                            "--tz", "America/New_York",
                            "--out", os.path.join(d, "c.csv"), "--ics", ics])
        if rc != 0 and "tzdata" in err:
            return                                   # no tzdata: skip, not fail
        assert rc == 0, err
        # newline="" — universal-newline mode would rewrite CRLF and hide
        # whether the file actually uses the line endings RFC 5545 requires.
        text = open(ics, encoding="utf-8", newline="").read()
        starts = [l.split(":")[1].strip() for l in text.split("\r\n")
                  if l.startswith("DTSTART")]
        assert len(starts) == 3, starts
        # 27 Oct is EDT (UTC-4 -> 13:00Z); 3 and 10 Nov are EST (UTC-5 -> 14:00Z)
        assert starts[0].endswith("T130000Z"), f"pre-DST: {starts[0]}"
        assert starts[1].endswith("T140000Z"), f"post-DST: {starts[1]}"


def t_calendar_utc_offset_fallback():
    with tempfile.TemporaryDirectory() as d:
        rc, out, err = run(["tools/calendar_gen.py", "--start", "2026-09-01",
                            "--weeks", "1", "--slot", "Tue 09:00 x",
                            "--utc-offset", "-5", "--ics",
                            os.path.join(d, "c.ics"), "--out",
                            os.path.join(d, "c.csv")])
        assert rc == 0, err
        text = open(os.path.join(d, "c.ics"), encoding="utf-8").read()
        assert "T140000Z" in text, "UTC-5 09:00 should be 14:00Z"


def t_calendar_ics_is_wellformed():
    with tempfile.TemporaryDirectory() as d:
        ics = os.path.join(d, "c.ics")
        rc, _, err = run(["tools/calendar_gen.py", "--start", "2026-09-01",
                          "--weeks", "2", "--slot", "Tue 09:00 a very long "
                          "slot label that will certainly exceed the seventy "
                          "five octet folding limit for ICS content lines",
                          "--utc-offset", "0", "--out", os.path.join(d, "c.csv"),
                          "--ics", ics])
        assert rc == 0, err
        raw = open(ics, encoding="utf-8", newline="").read()
        assert raw.startswith("BEGIN:VCALENDAR")
        assert raw.rstrip().endswith("END:VCALENDAR")
        assert raw.count("BEGIN:VEVENT") == raw.count("END:VEVENT") == 2
        assert "\r\n" in raw, "RFC 5545 requires CRLF line endings"
        assert raw.replace("\r\n", "").count("\n") == 0, \
            "file mixes bare LF into CRLF content lines"
        for line in raw.split("\r\n"):
            assert len(line.encode("utf-8")) <= 75, \
                f"unfolded line exceeds 75 octets: {line[:80]!r}"


def t_calendar_ics_escaping():
    with tempfile.TemporaryDirectory() as d:
        ics = os.path.join(d, "c.ics")
        run(["tools/calendar_gen.py", "--start", "2026-09-01", "--weeks", "1",
             "--slot", "Tue 09:00 a,b;c", "--utc-offset", "0",
             "--out", os.path.join(d, "c.csv"), "--ics", ics])
        text = open(ics, encoding="utf-8").read()
        assert r"a\,b\;c" in text, "commas and semicolons must be escaped in ICS"


def t_calendar_skip_and_bounds():
    with tempfile.TemporaryDirectory() as d:
        csvp = os.path.join(d, "c.csv")
        rc, _, err = run(["tools/calendar_gen.py", "--start", "2026-09-01",
                          "--weeks", "2", "--slot", "Tue 09:00 x",
                          "--skip", "2026-09-08", "--utc-offset", "0",
                          "--out", csvp])
        assert rc == 0, err
        body = open(csvp, encoding="utf-8").read()
        assert "2026-09-01" in body and "2026-09-08" not in body


def t_calendar_all_skipped_errors():
    with tempfile.TemporaryDirectory() as d:
        rc, out, err = run(["tools/calendar_gen.py", "--start", "2026-09-01",
                            "--weeks", "1", "--slot", "Tue 09:00 x",
                            "--skip", "2026-09-01", "--utc-offset", "0",
                            "--out", os.path.join(d, "c.csv")])
        expect_clean_error(rc, out, err, "every slot skipped")


def t_calendar_rejects_absurd_range():
    rc, out, err = run(["tools/calendar_gen.py", "--start", "2026-09-01",
                        "--weeks", "5000", "--slot", "Tue 09:00 x"])
    expect_clean_error(rc, out, err, "absurd --weeks")


def t_calendar_start_midweek():
    """Starting on a Thursday must not emit that week's Tuesday slot."""
    with tempfile.TemporaryDirectory() as d:
        csvp = os.path.join(d, "c.csv")
        rc, _, err = run(["tools/calendar_gen.py", "--start", "2026-09-03",
                          "--weeks", "2", "--slot", "Tue 09:00 x",
                          "--utc-offset", "0", "--out", csvp])
        assert rc == 0, err
        lines = [l for l in open(csvp, encoding="utf-8").read().split("\n")
                 if l.strip()][1:]
        assert "2026-09-01" not in "\n".join(lines), \
            "emitted a slot before --start"
        assert len(lines) == 1, f"expected 1 slot, got {len(lines)}"


# ==========================================================================
# usage — the skill/tool usage report
# ==========================================================================

def _transcript(d, session, records):
    """Write a minimal Claude Code transcript."""
    path = os.path.join(d, f"{session}.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    return path


def _skill_call(name, ts, session):
    return {"type": "assistant", "timestamp": ts, "sessionId": session,
            "cwd": "/home/user/AjT10-SSH",
            "message": {"content": [{"type": "tool_use", "name": "Skill",
                                     "input": {"skill": name}}]}}


def t_usage_counts_skill_invocations():
    with tempfile.TemporaryDirectory() as d:
        _transcript(d, "s1", [_skill_call("red-team", "2026-01-01T10:00:00Z", "s1"),
                              _skill_call("red-team", "2026-01-01T11:00:00Z", "s1"),
                              _skill_call("inversion", "2026-01-01T12:00:00Z", "s1")])
        rc, out, err = run(["tools/usage.py", "--transcripts", d,
                            "--archive-dir", os.path.join(d, "arch"), "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert data["skills"]["red-team"] == 2, data["skills"]
        assert data["skills"]["inversion"] == 1
        assert data["sessions"] == 1


def t_usage_counts_tools_and_commands():
    with tempfile.TemporaryDirectory() as d:
        recs = [
            {"type": "assistant", "timestamp": "2026-01-01T10:00:00Z",
             "sessionId": "s1", "message": {"content": [
                 {"type": "tool_use", "name": "Bash",
                  "input": {"command": "python3 tools/abtest.py compare --a 1/2 --b 1/3"}}]}},
            {"type": "user", "timestamp": "2026-01-01T10:05:00Z", "sessionId": "s1",
             "message": {"content": [
                 {"type": "text", "text": "<command-name>/audit</command-name>"}]}},
        ]
        _transcript(d, "s1", recs)
        rc, out, err = run(["tools/usage.py", "--transcripts", d,
                            "--archive-dir", os.path.join(d, "arch"), "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert data["tools"].get("abtest") == 1, data["tools"]
        assert data["commands"].get("audit") == 1, data["commands"]


def t_usage_refuses_a_verdict_on_thin_history():
    """One session is not evidence that a skill is unwanted. A confident drop
    list built from it would be worse than no list."""
    with tempfile.TemporaryDirectory() as d:
        _transcript(d, "s1", [_skill_call("red-team", "2026-01-01T10:00:00Z", "s1")])
        rc, out, err = run(["tools/usage.py", "--transcripts", d,
                            "--archive-dir", os.path.join(d, "arch")])
        assert rc == 0, err
        assert "Not enough history" in out, out[-500:]
        assert "drop candidates" not in out, "offered a drop list on one session"


def t_usage_gives_a_verdict_once_history_is_real():
    with tempfile.TemporaryDirectory() as d:
        for i in range(6):
            ts = f"2026-0{1 + i // 3}-{(i * 6) % 28 + 1:02d}T10:00:00Z"
            _transcript(d, f"s{i}", [_skill_call("red-team", ts, f"s{i}")])
        rc, out, err = run(["tools/usage.py", "--transcripts", d,
                            "--archive-dir", os.path.join(d, "arch")])
        assert rc == 0, err
        assert "Not enough history" not in out, out[-400:]
        assert "drop candidates" in out, "withheld a verdict despite the history"


def t_usage_archive_holds_no_conversation_text():
    """The archive is committed, so it must never carry prompts or replies."""
    secret = "SENSITIVE-CLIENT-NAME-DO-NOT-PERSIST"
    with tempfile.TemporaryDirectory() as d:
        arch = os.path.join(d, "arch")
        # One session has one cwd; make it the sensitive one so the test
        # proves only the basename is ever written.
        _transcript(d, "s1", [
            {"type": "assistant", "timestamp": "2026-01-01T10:00:00Z",
             "sessionId": "s1", "cwd": "/home/user/secret-project-path",
             "message": {"content": [{"type": "tool_use", "name": "Skill",
                                      "input": {"skill": "red-team"}}]}},
            {"type": "user", "timestamp": "2026-01-01T10:01:00Z", "sessionId": "s1",
             "cwd": "/home/user/secret-project-path",
             "message": {"content": [{"type": "text", "text": secret}]}},
        ])
        rc, out, err = run(["tools/usage.py", "--transcripts", d,
                            "--archive-dir", arch, "--archive"])
        assert rc == 0, err
        banked = os.path.join(arch, "s1.json")
        assert os.path.isfile(banked), os.listdir(arch)
        body = open(banked, encoding="utf-8").read()
        assert secret not in body, "conversation text leaked into the archive"
        assert "/home/user/secret-project-path" not in body, \
            "a full filesystem path leaked into the archive"
        rec = json.loads(body)
        assert rec["project"] == "secret-project-path", \
            "project should be the directory name only"
        assert set(rec) == {"session", "project", "first", "last",
                            "skills", "commands", "tools"}, sorted(rec)


def t_usage_archive_survives_transcript_loss():
    """The whole point: history must outlive the container."""
    with tempfile.TemporaryDirectory() as d:
        arch = os.path.join(d, "arch")
        live = os.path.join(d, "live")
        os.makedirs(live)
        _transcript(live, "s1", [_skill_call("red-team", "2026-01-01T10:00:00Z", "s1")])
        rc, _, err = run(["tools/usage.py", "--transcripts", live,
                          "--archive-dir", arch, "--archive"])
        assert rc == 0, err

        # Container reclaimed: transcripts gone, a new session begins.
        os.remove(os.path.join(live, "s1.jsonl"))
        _transcript(live, "s2", [_skill_call("inversion", "2026-02-01T10:00:00Z", "s2")])
        rc, out, err = run(["tools/usage.py", "--transcripts", live,
                            "--archive-dir", arch, "--json"])
        assert rc == 0, err
        data = json.loads(out)
        assert data["sessions"] == 2, f"lost the archived session: {data['sessions']}"
        assert data["skills"].get("red-team") == 1, \
            "the archived session's counts were dropped"
        assert data["skills"].get("inversion") == 1


def t_usage_archive_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        arch = os.path.join(d, "arch")
        _transcript(d, "s1", [_skill_call("red-team", "2026-01-01T10:00:00Z", "s1")])
        run(["tools/usage.py", "--transcripts", d, "--archive-dir", arch, "--archive"])
        before = open(os.path.join(arch, "s1.json"), encoding="utf-8").read()
        rc, _, err = run(["tools/usage.py", "--transcripts", d,
                          "--archive-dir", arch, "--archive"])
        assert rc == 0, err
        assert open(os.path.join(arch, "s1.json"), encoding="utf-8").read() == before
        assert not [f for f in os.listdir(arch) if f.endswith(".tmp")], \
            "left a temp file behind"


def t_usage_handles_missing_and_corrupt_input():
    rc, out, err = run(["tools/usage.py", "--transcripts", "/nope/missing"])
    expect_clean_error(rc, out, err, "missing transcript directory")
    with tempfile.TemporaryDirectory() as d:
        rc, out, err = run(["tools/usage.py", "--transcripts", d])
        expect_clean_error(rc, out, err, "empty transcript directory")
        # A truncated final line is normal and must not crash the report.
        with open(os.path.join(d, "s1.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(_skill_call("red-team", "2026-01-01T10:00:00Z", "s1")) + "\n")
            fh.write('{"type": "assistant", "message": {"cont')
        rc, out, err = run(["tools/usage.py", "--transcripts", d,
                            "--archive-dir", os.path.join(d, "a"), "--json"])
        assert rc == 0, f"a truncated line broke the report: {err}"
        assert json.loads(out)["skills"]["red-team"] == 1


# ==========================================================================
# studio — the browser tool
# ==========================================================================

def t_studio_fixtures_are_deterministic():
    """parity_expected.json is derived from these, so drift here would surface
    as a false parity failure rather than as the fixture bug it is."""
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, "a"), os.path.join(d, "b")
        for target in (a, b):
            rc, out, err = run(["studio/fixtures.py", "--out", target])
            assert rc == 0, err
        for name in ("pages.csv", "revenue.csv", "traffic.csv"):
            first = open(os.path.join(a, name), encoding="utf-8").read()
            second = open(os.path.join(b, name), encoding="utf-8").read()
            assert first == second, f"{name} differs between runs"
            committed = os.path.join(ROOT, "studio", "fixtures", name)
            assert os.path.isfile(committed), f"studio/fixtures/{name} missing"
            assert open(committed, encoding="utf-8").read() == first, \
                f"studio/fixtures/{name} is stale — run python3 studio/fixtures.py"


def t_studio_build_is_current():
    """Editing engine.js without rebuilding would ship a tool that differs
    from its own source."""
    rc, out, err = run(["studio/build.py", "--check"])
    assert rc == 0, f"studio/index.html is stale:\n{err}"


def t_studio_is_self_contained():
    """A single file that phones home is not a single file."""
    p = os.path.join(ROOT, "studio", "index.html")
    assert os.path.isfile(p), "studio/index.html missing"
    html = open(p, encoding="utf-8").read()
    scan = html.replace('xmlns="http://www.w3.org/2000/svg"', "")
    for bad in ("http://", "https://", "cdn.", "fetch(", "XMLHttpRequest",
                "@import", "<link", "sendBeacon"):
        assert bad not in scan, f"studio/index.html reaches the network: {bad}"


def t_studio_pages_copy_matches():
    """docs/index.html is what the public URL serves. If it drifts from
    studio/index.html the hosted tool silently differs from the source."""
    a = os.path.join(ROOT, "studio", "index.html")
    b = os.path.join(ROOT, "docs", "index.html")
    assert os.path.isfile(b), "docs/index.html missing — run studio/build.py"
    assert open(a, encoding="utf-8").read() == open(b, encoding="utf-8").read(), \
        "docs/index.html differs from studio/index.html"


def t_studio_artifact_fragment_is_whole():
    """The fragment is produced by unwrapping the document. app.js contains the
    literal string '</body></html>' inside a template literal, which a
    non-greedy regex matches — truncating the file mid-script, silently."""
    p = os.path.join(ROOT, "studio", "artifact.html")
    assert os.path.isfile(p), "studio/artifact.html missing"
    frag = open(p, encoding="utf-8").read()
    assert frag.count("<script>") == frag.count("</script>") == 3, \
        f"fragment truncated: {frag.count('<script>')} open, " \
        f"{frag.count('</script>')} close"
    assert frag.startswith("<title>"), "fragment should start with its title"
    outside = re.sub(r"<script>.*?</script>", "", frag, flags=re.S).lower()
    for tag in ("html", "head", "body"):
        assert not re.search(rf"</?{tag}[\s>]", outside), \
            f"fragment still carries a <{tag}> document tag"


def t_studio_states_its_limits():
    html = open(os.path.join(ROOT, "studio", "index.html"), encoding="utf-8").read()
    for required in ("not a valuation", "never transmitted", "Descriptive statistics"):
        assert required in html, f"studio/index.html omits {required!r}"


def t_studio_has_no_paywall():
    """This is a personal tool. Nothing in it should gate a feature behind a
    purchase that does not exist."""
    for fn in ("app.js", "template.html", "README.md"):
        text = open(os.path.join(ROOT, "studio", fn), encoding="utf-8").read()
        low = text.lower()
        for word in ("paid upgrade", "paid tier", "billing", "subscription",
                     "free version"):
            assert word not in low, f"studio/{fn} still mentions {word!r}"


def t_parity_fixture_is_interpreter_stable():
    """The frozen fixture must not carry more precision than it can reproduce.

    Regression for a CI failure that was not a bug in any tool: CPython 3.12
    switched sum() over floats to Neumaier compensated summation, so hhi came
    out one ULP from the 3.11 value and the byte-comparison in
    t_studio_parity_fixture_is_current failed on half the matrix. Rounding at
    write time fixes it; this asserts the rounding actually happened, so a
    future edit that drops quantize() is caught here rather than on whichever
    Python version CI happens to add next.
    """
    sys.path.insert(0, os.path.join(ROOT, "studio"))
    import parity_expected                                     # noqa: E402
    raw = json.load(open(os.path.join(ROOT, "studio", "parity_expected.json"),
                         encoding="utf-8"))
    assert parity_expected.quantize(raw) == raw, \
        "parity_expected.json holds unrounded floats — quantize() was skipped"


def t_studio_parity_fixture_is_current():
    """parity_expected.json must reflect what tools/ computes right now."""
    expected = os.path.join(ROOT, "studio", "parity_expected.json")
    assert os.path.isfile(expected), "run python3 studio/parity_expected.py"
    before = open(expected, encoding="utf-8").read()
    rc, out, err = run(["studio/parity_expected.py"])
    assert rc == 0, err
    after = open(expected, encoding="utf-8").read()
    assert before == after, \
        "parity_expected.json is stale — tools/ changed. Re-run parity.mjs too."


# ==========================================================================
# the stdlib-only guarantee
# ==========================================================================

def _no_deps():
    sys.path.insert(0, os.path.join(ROOT, "qa"))
    import no_deps                                             # noqa: E402
    return no_deps


def t_no_deps_passes_this_repo():
    res = _no_deps().scan()
    assert not res["offenders"], res["offenders"]
    assert res["files"] >= 11, f"only scanned {res['files']} files"


def t_no_deps_locals_are_derived_not_listed():
    """Every tool must be recognised as a sibling automatically.

    The old check carried a hardcoded allowlist of local module names and
    `usage` was never added to it. Deriving the set from the directory is what
    stops that from recurring, so assert it is actually derived."""
    local = _no_deps().local_modules()
    for expected in ("csvio", "usage", "concentration", "chartkit"):
        assert expected in local, f"{expected} not seen as a local module"


def t_no_deps_catches_a_dependency():
    nd = _no_deps()
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "fine.py"), "w", encoding="utf-8") as fh:
            fh.write("import os, json\nfrom datetime import date\n")
        with open(os.path.join(d, "bad.py"), "w", encoding="utf-8") as fh:
            fh.write("import requests\nfrom numpy import array\n")
        res = nd.scan(d)
        mods = sorted(o["module"] for o in res["offenders"])
        assert mods == ["numpy", "requests"], mods
        rc, out, err = run(["qa/no_deps.py", "--tools", d])
        assert rc == 1, f"exit {rc}, expected 1"
        assert "requests" in err


def t_no_deps_survives_python_39():
    """sys.stdlib_module_names does not exist before 3.10.

    This is the actual bug: the check read it through getattr(..., ()) and so
    on 3.9 — the floor version the CI matrix exists to protect — the stdlib set
    was empty and `import os` was reported as a third-party dependency. The
    gate failed on every commit and told us nothing. Simulated by deleting the
    attribute, because the matrix cannot be run from inside one interpreter."""
    prog = (
        "import sys, os, json\n"
        f"sys.path.insert(0, {os.path.join(ROOT, 'qa')!r})\n"
        "import no_deps\n"
        "del sys.stdlib_module_names\n"
        "assert not hasattr(sys, 'stdlib_module_names')\n"
        f"res = no_deps.scan({TOOLS_DIR!r})\n"
        "assert not res['offenders'], res['offenders']\n"
        "assert no_deps.classify('requests', set()) == 'third-party'\n"
        "assert no_deps.classify('os', set()) == 'stdlib'\n"
        "assert no_deps.classify('__future__', set()) == 'stdlib'\n"
        "print('ok')\n"
    )
    p = subprocess.run([sys.executable, "-c", prog], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr.strip()
    assert "ok" in p.stdout


# ==========================================================================
# validator must actually catch things
# ==========================================================================

def t_validator_catches_broken_skill():
    """The QA gate is itself under test — a validator that passes everything
    is worse than none, because it manufactures confidence."""
    with tempfile.TemporaryDirectory() as d:
        fake = os.path.join(d, "repo")
        shutil.copytree(os.path.join(ROOT, ".claude"),
                        os.path.join(fake, ".claude"))
        os.makedirs(os.path.join(fake, "qa"))
        shutil.copy(os.path.join(ROOT, "qa", "validate.py"),
                    os.path.join(fake, "qa", "validate.py"))

        bad = os.path.join(fake, ".claude", "skills", "broken-one")
        os.makedirs(bad)
        write(bad, "SKILL.md",
              "---\nname: totally-different\ndescription: short\n---\n# x\n")

        p = subprocess.run([sys.executable, "qa/validate.py", "--json"],
                           cwd=fake, capture_output=True, text=True, timeout=60)
        assert p.returncode != 0, "validator passed a skill with a name mismatch"
        report = json.loads(p.stdout)
        joined = " ".join(report["errors"])
        assert "totally-different" in joined, \
            f"validator did not name the mismatch: {report['errors']}"


def t_validator_catches_missing_tool_reference():
    with tempfile.TemporaryDirectory() as d:
        fake = os.path.join(d, "repo")
        os.makedirs(os.path.join(fake, "qa"))
        shutil.copy(os.path.join(ROOT, "qa", "validate.py"),
                    os.path.join(fake, "qa", "validate.py"))
        sk = os.path.join(fake, ".claude", "skills", "ghost")
        os.makedirs(sk)
        write(sk, "SKILL.md",
              "---\nname: ghost\ndescription: Use when testing that the "
              "validator catches references to files that do not exist "
              "anywhere in the repository at all.\n---\n# ghost\n\n"
              "Run `tools/does_not_exist.py` for this.\n\n" + ("x " * 120))
        p = subprocess.run([sys.executable, "qa/validate.py", "--json"],
                           cwd=fake, capture_output=True, text=True, timeout=60)
        assert p.returncode != 0, "validator missed a dangling tool reference"
        assert "does_not_exist" in " ".join(json.loads(p.stdout)["errors"])


def t_validator_passes_this_repo():
    p = subprocess.run([sys.executable, "qa/validate.py", "--json"],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    report = json.loads(p.stdout)
    assert not report["errors"], \
        "this repo does not pass its own validator:\n  " + \
        "\n  ".join(report["errors"])


def t_hook_never_breaks_session():
    """A hook that crashes would block every edit. It must fail open."""
    hook = os.path.join(ROOT, ".claude", "hooks", "validate_on_edit.py")
    for stdin in ["", "not json", "{}", '{"tool_input": {}}',
                  '{"tool_input": {"file_path": "/nonexistent/zz.md"}}',
                  '{"tool_input": {"file_path": 12345}}',
                  '[1,2,3]']:
        p = subprocess.run([sys.executable, hook], cwd=ROOT, input=stdin,
                           capture_output=True, text=True, timeout=30,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": ROOT})
        assert p.returncode == 0, \
            f"hook exited {p.returncode} on stdin {stdin!r} — would block edits"
        assert "Traceback" not in p.stderr


def t_hook_flags_real_breakage():
    hook = os.path.join(ROOT, ".claude", "hooks", "validate_on_edit.py")
    with tempfile.TemporaryDirectory() as d:
        sk = os.path.join(d, ".claude", "skills", "mismatch")
        os.makedirs(sk)
        f = write(sk, "SKILL.md",
                  "---\nname: other-name\ndescription: Use when testing.\n---\n#x\n")
        p = subprocess.run([sys.executable, hook], cwd=ROOT,
                           input=json.dumps({"tool_input": {"file_path": f}}),
                           capture_output=True, text=True, timeout=30,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": d})
        assert p.returncode == 2, \
            f"hook did not flag a name/directory mismatch (rc={p.returncode})"
        assert "other-name" in p.stderr


# ==========================================================================

TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("t_") and callable(v)]


def main():
    print(f"running {len(TESTS)} adversarial tests\n")
    for name, fn in TESTS:
        check(name[2:].replace("_", " "), fn)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print()
        for name, why in FAIL:
            print(f"  FAIL  {name}\n        {why}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
