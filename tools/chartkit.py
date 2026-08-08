#!/usr/bin/env python3
"""chartkit — dependency-free SVG charts that survive light and dark themes.

Why this exists: matplotlib/plotly are not always installed, and their default
output looks like a lab notebook. This emits a single self-contained SVG string
with no external fetches, so it drops straight into an Artifact, a README, a
dashboard, or a Slack upload.

CLI
    python3 tools/chartkit.py --type line --csv data.csv --x date --y views \\
        --title "Views" --out chart.svg

    python3 tools/chartkit.py --type bar --csv d.csv --x platform --y er \\
        --series-col platform --out chart.svg

Library
    from chartkit import line, bar, donut, heatmap, sparkline, scatter, area

Every function returns an SVG string. Nothing writes to disk unless you ask.

Colors are emitted as CSS custom properties on the root <svg>, redefined under
`prefers-color-scheme: dark`. Swap the two palettes in PALETTE for a brand.
"""

from __future__ import annotations

import argparse
import html
import math
import os
import sys
from typing import Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csvio  # noqa: E402

__all__ = [
    "line", "area", "bar", "hbar", "stacked_bar", "donut",
    "heatmap", "sparkline", "scatter", "render_csv",
]

# --------------------------------------------------------------------------
# Palette. Brand-neutral placeholders — replace the hex values, keep the roles.
# Categorical hues are ordered so the first four stay distinguishable under the
# most common forms of color vision deficiency and in grayscale print.
# --------------------------------------------------------------------------

PALETTE = {
    "light": {
        "bg": "#ffffff",
        "surface": "#f6f7f9",
        "ink": "#16181d",
        "muted": "#5c6370",
        "grid": "#e4e7ec",
        "axis": "#b6bcc7",
        "cat": ["#3b6ef2", "#e07b39", "#1f9d76", "#a855c9",
                "#d2455f", "#5a7183", "#8a7a1f", "#2ba3c4"],
        "pos": "#1f9d76",
        "neg": "#d2455f",
        "seq": ["#eef3fe", "#cfdefb", "#a7c1f6", "#7aa0ef", "#4f7de6", "#2f5bc9", "#1e3f96"],
    },
    "dark": {
        "bg": "#14161a",
        "surface": "#1c1f25",
        "ink": "#eef0f4",
        "muted": "#9aa3b0",
        "grid": "#2b3038",
        "axis": "#4a515c",
        "cat": ["#79a0ff", "#f5a05e", "#4fc9a1", "#c98ae0",
                "#f0778c", "#93a3b5", "#c9b64e", "#5ec8e6"],
        "pos": "#4fc9a1",
        "neg": "#f0778c",
        "seq": ["#1b2436", "#22304c", "#2b4068", "#365388", "#4568aa", "#5a80cb", "#7599e6"],
    },
}

FONT = ("ui-sans-serif, -apple-system, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, sans-serif")


class ChartError(ValueError):
    """Raised for input a chart cannot honestly represent."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _esc(s) -> str:
    return html.escape(str(s), quote=True)


def _num(v, field="value"):
    """Coerce to float. Accepts 1,234.5 / 12% / $1.2k / (300) as -300 / ''.

    NaN and infinity are rejected rather than treated as missing. A NaN
    arriving from a dataframe means an upstream computation went wrong, and
    silently plotting it as a gap hides the bug instead of surfacing it.
    """
    if v is None:
        return None
    if isinstance(v, bool):
        raise ChartError(f"{field}: {v!r} is a boolean, not a measurement")
    if isinstance(v, (int, float)):
        if isinstance(v, float) and not math.isfinite(v):
            raise ChartError(f"{field}: {v!r} is not a finite number")
        return float(v)
    s = str(v).strip()
    if s == "" or s.lower() in {"na", "n/a", "null", "none", "-", "--"}:
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace(",", "").replace("$", "").replace("£", "").replace("€", "")
    s = s.replace("%", "").strip()
    mult = 1.0
    if s and s[-1] in "kKmMbB":
        mult = {"k": 1e3, "m": 1e6, "b": 1e9}[s[-1].lower()]
        s = s[:-1]
    try:
        out = float(s) * mult
    except ValueError:
        raise ChartError(f"{field}: cannot read {v!r} as a number")
    if math.isnan(out) or math.isinf(out):
        raise ChartError(f"{field}: {v!r} is not finite")
    return -out if neg else out


def _fmt(v: float, unit: str = "") -> str:
    """Short human number. 1234 -> 1.2k, 0.043 -> 0.043, 12000000 -> 12M."""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e9:
        s = f"{v/1e9:.2f}".rstrip("0").rstrip(".") + "B"
    elif a >= 1e6:
        s = f"{v/1e6:.2f}".rstrip("0").rstrip(".") + "M"
    elif a >= 1e3:
        s = f"{v/1e3:.2f}".rstrip("0").rstrip(".") + "k"
    elif a >= 1:
        s = f"{v:.2f}".rstrip("0").rstrip(".")
    elif a == 0:
        s = "0"
    else:
        s = f"{v:.4g}"
    return s + unit


def _nice_ticks(lo: float, hi: float, target: int = 5):
    """Axis ticks on 1/2/5x10^n boundaries. Always returns >= 2 ticks."""
    if not all(map(math.isfinite, (lo, hi))):
        raise ChartError("axis bounds are not finite")
    if hi == lo:
        # A flat series still deserves a readable axis.
        pad = abs(hi) * 0.1 or 1.0
        lo, hi = lo - pad, hi + pad
    if hi < lo:
        lo, hi = hi, lo
    span = hi - lo
    raw = span / max(1, target)
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1.0
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            step = m * mag
            break
    else:
        step = 10 * mag
    start = math.floor(lo / step) * step
    ticks, t, guard = [], start, 0
    while t <= hi + step * 0.5 and guard < 500:
        ticks.append(round(t, 10))
        t += step
        guard += 1
    if len(ticks) < 2:
        ticks = [lo, hi]
    return ticks


def _style(theme_lock: str | None = None) -> str:
    """CSS vars for both themes. theme_lock pins one palette (for PNG export)."""
    def block(sel, pal):
        cat = "".join(f"--c{i}:{c};" for i, c in enumerate(pal["cat"]))
        seq = "".join(f"--s{i}:{c};" for i, c in enumerate(pal["seq"]))
        return (f"{sel}{{--bg:{pal['bg']};--surface:{pal['surface']};"
                f"--ink:{pal['ink']};--muted:{pal['muted']};--grid:{pal['grid']};"
                f"--axis:{pal['axis']};--pos:{pal['pos']};--neg:{pal['neg']};{cat}{seq}}}")

    if theme_lock in ("light", "dark"):
        css = block(".ck", PALETTE[theme_lock])
    else:
        css = block(".ck", PALETTE["light"])
        css += ("@media (prefers-color-scheme: dark){"
                + block(".ck", PALETTE["dark"]) + "}")
    css += (f".ck{{font-family:{FONT};}}"
            ".ck .bgr{fill:var(--bg)}"
            ".ck .ttl{fill:var(--ink);font-size:15px;font-weight:600}"
            ".ck .sub{fill:var(--muted);font-size:11.5px}"
            ".ck .lbl{fill:var(--muted);font-size:11px}"
            ".ck .vlbl{fill:var(--ink);font-size:11px;font-weight:600}"
            ".ck .gl{stroke:var(--grid);stroke-width:1}"
            ".ck .ax{stroke:var(--axis);stroke-width:1}"
            ".ck .ln{fill:none;stroke-width:2.25;stroke-linejoin:round;stroke-linecap:round}")
    return f"<style>{css}</style>"


def _frame(w, h, title, subtitle, body, theme_lock=None, legend="") -> str:
    t = (f'<text class="ttl" x="16" y="24">{_esc(title)}</text>' if title else "")
    st = (f'<text class="sub" x="16" y="{42 if title else 24}">{_esc(subtitle)}</text>'
          if subtitle else "")
    return (
        f'<svg class="ck" xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{_esc(title or "chart")}">'
        f'{_style(theme_lock)}<rect class="bgr" width="{w}" height="{h}" rx="10"/>'
        f'{t}{st}{legend}{body}</svg>'
    )


def _top_pad(title, subtitle) -> int:
    return 20 + (22 if title else 0) + (20 if subtitle else 0)


def _legend(names: Sequence[str], x=16, y=0) -> str:
    out, cx = [], x
    for i, n in enumerate(names):
        out.append(f'<rect x="{cx}" y="{y-8}" width="9" height="9" rx="2" '
                   f'fill="var(--c{i%8})"/>')
        out.append(f'<text class="lbl" x="{cx+13}" y="{y}">{_esc(n)}</text>')
        cx += 13 + max(28, int(len(str(n)) * 6.2)) + 14
    return "".join(out)


def _series_from(values, labels=None):
    """Normalize into [(name, [y...])]. Accepts list, dict, list-of-dicts."""
    if isinstance(values, dict):
        return [(k, [_num(v, k) for v in vs]) for k, vs in values.items()]
    if values and isinstance(values[0], (list, tuple)):
        return [(f"series {i+1}", [_num(v) for v in s]) for i, s in enumerate(values)]
    return [((labels or ["value"])[0] if labels else "value",
             [_num(v) for v in values])]


# --------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------

def line(x, values, title="", subtitle="", w=760, h=380, unit="",
         area_fill=False, theme_lock=None, y_zero=False):
    """Time or ordered-category series. `values` = list | dict{name: list}."""
    x = list(x)
    series = _series_from(values)
    if not x:
        raise ChartError("line: no x values")
    for name, ys in series:
        if len(ys) != len(x):
            raise ChartError(
                f"line: series '{name}' has {len(ys)} points but x has {len(x)}")
    flat = [v for _, ys in series for v in ys if v is not None]
    if not flat:
        raise ChartError("line: every value is empty")

    top = _top_pad(title, subtitle) + (18 if len(series) > 1 else 0)
    left, right, bottom = 58, 18, 40
    pw, ph = w - left - right, h - top - bottom
    if pw <= 20 or ph <= 20:
        raise ChartError("line: canvas too small for the margins")

    lo, hi = min(flat), max(flat)
    if y_zero:
        lo, hi = min(0, lo), max(0, hi)
    ticks = _nice_ticks(lo, hi)
    tlo, thi = ticks[0], ticks[-1]
    span = (thi - tlo) or 1.0

    def px(i):
        return left + (pw * i / max(1, len(x) - 1) if len(x) > 1 else pw / 2)

    def py(v):
        return top + ph - (v - tlo) / span * ph

    b = []
    for t in ticks:
        y = py(t)
        b.append(f'<line class="gl" x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}"/>')
        b.append(f'<text class="lbl" x="{left-8}" y="{y+4:.1f}" text-anchor="end">'
                 f'{_esc(_fmt(t, unit))}</text>')

    step = max(1, len(x) // 8)
    for i in range(0, len(x), step):
        b.append(f'<text class="lbl" x="{px(i):.1f}" y="{top+ph+18}" '
                 f'text-anchor="middle">{_esc(x[i])}</text>')

    for si, (name, ys) in enumerate(series):
        col = f"var(--c{si%8})"
        # Break the path at gaps instead of drawing a lie through them.
        runs, cur = [], []
        for i, v in enumerate(ys):
            if v is None:
                if cur:
                    runs.append(cur)
                cur = []
            else:
                cur.append((px(i), py(v)))
        if cur:
            runs.append(cur)
        for run in runs:
            if len(run) == 1:
                cx, cy = run[0]
                b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{col}"/>')
                continue
            d = "M" + " L".join(f"{cx:.1f},{cy:.1f}" for cx, cy in run)
            if area_fill and len(series) == 1:
                base = py(max(tlo, 0) if tlo <= 0 <= thi else tlo)
                b.append(f'<path d="{d} L{run[-1][0]:.1f},{base:.1f} '
                         f'L{run[0][0]:.1f},{base:.1f} Z" fill="{col}" opacity="0.13"/>')
            b.append(f'<path class="ln" d="{d}" stroke="{col}"/>')
        pts = [(px(i), py(v)) for i, v in enumerate(ys) if v is not None]
        if len(pts) <= 24:
            for cx, cy in pts:
                b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.6" fill="{col}"/>')

    b.append(f'<line class="ax" x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}"/>')
    lg = _legend([n for n, _ in series], 16, _top_pad(title, subtitle) + 4) if len(series) > 1 else ""
    return _frame(w, h, title, subtitle, "".join(b), theme_lock, lg)


def area(x, values, **kw):
    kw.setdefault("area_fill", True)
    return line(x, values, **kw)


def bar(labels, values, title="", subtitle="", w=760, h=380, unit="",
        theme_lock=None, color_by_label=False, show_values=True):
    """Vertical bars for a small number of categories."""
    labels = [str(v) for v in labels]
    vals = [_num(v, "bar") for v in values]
    if not labels:
        raise ChartError("bar: no categories")
    if len(labels) != len(vals):
        raise ChartError(f"bar: {len(labels)} labels vs {len(vals)} values")
    vals = [0.0 if v is None else v for v in vals]

    top = _top_pad(title, subtitle)
    left, right, bottom = 58, 18, 46
    pw, ph = w - left - right, h - top - bottom
    if pw <= 20 or ph <= 20:
        raise ChartError("bar: canvas too small for the margins")

    ticks = _nice_ticks(min(0, min(vals)), max(0, max(vals)))
    tlo, thi = ticks[0], ticks[-1]
    span = (thi - tlo) or 1.0

    def py(v):
        return top + ph - (v - tlo) / span * ph

    n = len(vals)
    slot = pw / n
    bw = min(64.0, slot * 0.68)

    b = []
    for t in ticks:
        y = py(t)
        b.append(f'<line class="gl" x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}"/>')
        b.append(f'<text class="lbl" x="{left-8}" y="{y+4:.1f}" text-anchor="end">'
                 f'{_esc(_fmt(t, unit))}</text>')

    zero = py(0)
    for i, v in enumerate(vals):
        cx = left + slot * i + slot / 2
        y0, y1 = py(v), zero
        y, hgt = min(y0, y1), abs(y1 - y0)
        col = (f"var(--c{i%8})" if color_by_label
               else ("var(--neg)" if v < 0 else "var(--c0)"))
        b.append(f'<rect x="{cx-bw/2:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                 f'height="{max(hgt,1):.1f}" rx="3" fill="{col}"/>')
        if show_values and n <= 20:
            ly = y - 6 if v >= 0 else y + hgt + 13
            b.append(f'<text class="vlbl" x="{cx:.1f}" y="{ly:.1f}" '
                     f'text-anchor="middle">{_esc(_fmt(v, unit))}</text>')
        lab = labels[i] if len(labels[i]) <= 14 else labels[i][:13] + "…"
        b.append(f'<text class="lbl" x="{cx:.1f}" y="{top+ph+20}" '
                 f'text-anchor="middle">{_esc(lab)}</text>')

    b.append(f'<line class="ax" x1="{left}" y1="{zero:.1f}" x2="{left+pw}" y2="{zero:.1f}"/>')
    return _frame(w, h, title, subtitle, "".join(b), theme_lock)


def hbar(labels, values, title="", subtitle="", w=680, unit="",
         theme_lock=None, sort_desc=True):
    """Horizontal bars — the right call whenever labels are words, not dates."""
    labels = [str(v) for v in labels]
    vals = [_num(v, "hbar") or 0.0 for v in values]
    if not labels:
        raise ChartError("hbar: no categories")
    if len(labels) != len(vals):
        raise ChartError(f"hbar: {len(labels)} labels vs {len(vals)} values")
    pairs = list(zip(labels, vals))
    if sort_desc:
        pairs.sort(key=lambda p: p[1], reverse=True)

    top = _top_pad(title, subtitle)
    left, right = 8 + max(90, min(220, max(len(l) for l in labels) * 7)), 74
    rowh, gap = 26, 8
    h = top + len(pairs) * (rowh + gap) + 18
    pw = w - left - right
    if pw <= 20:
        raise ChartError("hbar: labels leave no room for bars")

    mx = max((abs(v) for v in vals), default=1.0) or 1.0
    b = []
    for i, (lab, v) in enumerate(pairs):
        y = top + i * (rowh + gap)
        bw = abs(v) / mx * pw
        col = "var(--neg)" if v < 0 else f"var(--c{i%8})"
        b.append(f'<text class="lbl" x="{left-10}" y="{y+rowh/2+4:.1f}" '
                 f'text-anchor="end">{_esc(lab)}</text>')
        b.append(f'<rect x="{left}" y="{y}" width="{pw}" height="{rowh}" rx="4" '
                 f'fill="var(--surface)"/>')
        b.append(f'<rect x="{left}" y="{y}" width="{max(bw,2):.1f}" height="{rowh}" '
                 f'rx="4" fill="{col}"/>')
        b.append(f'<text class="vlbl" x="{left+pw+8}" y="{y+rowh/2+4:.1f}">'
                 f'{_esc(_fmt(v, unit))}</text>')
    return _frame(w, h, title, subtitle, "".join(b), theme_lock)


def stacked_bar(labels, series: dict, title="", subtitle="", w=760, h=400,
                unit="", theme_lock=None, percent=False):
    """Composition over categories. percent=True normalizes each column to 100."""
    labels = [str(v) for v in labels]
    names = list(series.keys())
    if not names:
        raise ChartError("stacked_bar: no series")
    cols = []
    for i in range(len(labels)):
        col = []
        for n in names:
            vs = series[n]
            if len(vs) != len(labels):
                raise ChartError(
                    f"stacked_bar: series '{n}' has {len(vs)} values, "
                    f"expected {len(labels)}")
            v = _num(vs[i], n) or 0.0
            if v < 0:
                raise ChartError("stacked_bar: negative values cannot stack; use grouped bars")
            col.append(v)
        cols.append(col)
    if percent:
        cols = [[(v / (sum(c) or 1.0)) * 100 for v in c] for c in cols]

    top = _top_pad(title, subtitle) + 18
    left, right, bottom = 58, 18, 46
    pw, ph = w - left - right, h - top - bottom
    totals = [sum(c) for c in cols]
    ticks = _nice_ticks(0, max(totals) if totals else 1)
    tlo, thi = ticks[0], ticks[-1]
    span = (thi - tlo) or 1.0

    def py(v):
        return top + ph - (v - tlo) / span * ph

    b = []
    for t in ticks:
        y = py(t)
        b.append(f'<line class="gl" x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}"/>')
        b.append(f'<text class="lbl" x="{left-8}" y="{y+4:.1f}" text-anchor="end">'
                 f'{_esc(_fmt(t, "%" if percent else unit))}</text>')

    slot = pw / max(1, len(labels))
    bw = min(70.0, slot * 0.66)
    for i, col in enumerate(cols):
        cx = left + slot * i + slot / 2
        acc = 0.0
        for si, v in enumerate(col):
            y0, y1 = py(acc), py(acc + v)
            b.append(f'<rect x="{cx-bw/2:.1f}" y="{y1:.1f}" width="{bw:.1f}" '
                     f'height="{max(y0-y1,0):.1f}" fill="var(--c{si%8})"/>')
            acc += v
        lab = labels[i] if len(labels[i]) <= 14 else labels[i][:13] + "…"
        b.append(f'<text class="lbl" x="{cx:.1f}" y="{top+ph+20}" '
                 f'text-anchor="middle">{_esc(lab)}</text>')
    b.append(f'<line class="ax" x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}"/>')
    return _frame(w, h, title, subtitle, "".join(b), theme_lock,
                  _legend(names, 16, _top_pad(title, subtitle) + 4))


def donut(labels, values, title="", subtitle="", w=420, h=340, unit="",
          theme_lock=None, center_label=""):
    """Use only for parts of one whole, <= 6 slices. Otherwise reach for hbar."""
    labels = [str(v) for v in labels]
    vals = [_num(v, "donut") or 0.0 for v in values]
    if len(labels) != len(vals):
        raise ChartError(f"donut: {len(labels)} labels vs {len(vals)} values")
    if any(v < 0 for v in vals):
        raise ChartError("donut: negative slices are meaningless")
    total = sum(vals)
    if total <= 0:
        raise ChartError("donut: slices sum to zero")

    top = _top_pad(title, subtitle)
    cy = top + (h - top) / 2 - 6
    cx = w / 2 - 40
    R, r = min(cx - 10, (h - top) / 2 - 24), 0.0
    r = R * 0.62

    b, ang = [], -math.pi / 2
    for i, v in enumerate(vals):
        frac = v / total
        if frac <= 0:
            continue
        sweep = frac * 2 * math.pi
        a0, a1 = ang, ang + sweep
        ang = a1
        large = 1 if sweep > math.pi else 0
        if frac >= 0.9999:  # a full ring cannot be drawn as one arc
            b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{(R+r)/2:.1f}" '
                     f'fill="none" stroke="var(--c{i%8})" stroke-width="{R-r:.1f}"/>')
            continue
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        xi, yi = cx + r * math.cos(a1), cy + r * math.sin(a1)
        xj, yj = cx + r * math.cos(a0), cy + r * math.sin(a0)
        b.append(
            f'<path d="M{x0:.1f},{y0:.1f} A{R:.1f},{R:.1f} 0 {large} 1 {x1:.1f},{y1:.1f} '
            f'L{xi:.1f},{yi:.1f} A{r:.1f},{r:.1f} 0 {large} 0 {xj:.1f},{yj:.1f} Z" '
            f'fill="var(--c{i%8})"/>')

    if center_label:
        b.append(f'<text class="ttl" x="{cx:.1f}" y="{cy+2:.1f}" '
                 f'text-anchor="middle">{_esc(center_label)}</text>')
    ly = top + 10
    for i, (lab, v) in enumerate(zip(labels, vals)):
        b.append(f'<rect x="{w-150}" y="{ly-9}" width="9" height="9" rx="2" '
                 f'fill="var(--c{i%8})"/>')
        pct = v / total * 100
        b.append(f'<text class="lbl" x="{w-135}" y="{ly}">'
                 f'{_esc(lab[:14])} · {pct:.0f}%</text>')
        ly += 20
    return _frame(w, h, title, subtitle, "".join(b), theme_lock)


def heatmap(row_labels, col_labels, matrix, title="", subtitle="", w=760,
            unit="", theme_lock=None, cell=30):
    """Density grid — hour-of-day x day-of-week posting performance, correlations."""
    rows, cols = [str(r) for r in row_labels], [str(c) for c in col_labels]
    if len(matrix) != len(rows):
        raise ChartError(f"heatmap: {len(matrix)} rows of data vs {len(rows)} labels")
    grid = []
    for ri, row in enumerate(matrix):
        if len(row) != len(cols):
            raise ChartError(
                f"heatmap: row {ri} has {len(row)} cells, expected {len(cols)}")
        grid.append([_num(v, "heatmap") for v in row])
    flat = [v for row in grid for v in row if v is not None]
    if not flat:
        raise ChartError("heatmap: every cell is empty")
    lo, hi = min(flat), max(flat)
    rng = (hi - lo) or 1.0

    top = _top_pad(title, subtitle) + 16
    left = 8 + max(56, min(150, max((len(r) for r in rows), default=6) * 7))
    cw = min(float(cell), (w - left - 16) / max(1, len(cols)))
    ch = float(cell)
    h = top + len(rows) * ch + 40

    b = []
    for ci, c in enumerate(cols):
        b.append(f'<text class="lbl" x="{left+cw*ci+cw/2:.1f}" y="{top-6}" '
                 f'text-anchor="middle">{_esc(c[:6])}</text>')
    for ri, r in enumerate(rows):
        y = top + ri * ch
        b.append(f'<text class="lbl" x="{left-8}" y="{y+ch/2+4:.1f}" '
                 f'text-anchor="end">{_esc(r[:20])}</text>')
        for ci in range(len(cols)):
            v = grid[ri][ci]
            x = left + ci * cw
            if v is None:
                b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw-1.5:.1f}" '
                         f'height="{ch-1.5:.1f}" rx="3" fill="var(--surface)"/>')
                continue
            bucket = int((v - lo) / rng * 6.999)
            b.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw-1.5:.1f}" '
                     f'height="{ch-1.5:.1f}" rx="3" fill="var(--s{bucket})"/>')
    b.append(f'<text class="lbl" x="{left}" y="{h-14}">low {_esc(_fmt(lo, unit))}</text>')
    b.append(f'<text class="lbl" x="{left+len(cols)*cw:.1f}" y="{h-14}" '
             f'text-anchor="end">high {_esc(_fmt(hi, unit))}</text>')
    return _frame(w, int(h), title, subtitle, "".join(b), theme_lock)


def sparkline(values, w=140, h=34, theme_lock=None, color="var(--c0)"):
    """Inline trend for a stat tile. No axes on purpose."""
    ys = [v for v in (_num(v, "spark") for v in values) if v is not None]
    if len(ys) < 2:
        return (f'<svg class="ck" xmlns="http://www.w3.org/2000/svg" width="{w}" '
                f'height="{h}" viewBox="0 0 {w} {h}">{_style(theme_lock)}</svg>')
    lo, hi = min(ys), max(ys)
    rng = (hi - lo) or 1.0
    pad = 3
    pts = [(pad + (w - 2 * pad) * i / (len(ys) - 1),
            h - pad - (v - lo) / rng * (h - 2 * pad)) for i, v in enumerate(ys)]
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    last = pts[-1]
    return (f'<svg class="ck" xmlns="http://www.w3.org/2000/svg" width="{w}" '
            f'height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="trend">'
            f'{_style(theme_lock)}<path class="ln" d="{d}" stroke="{color}" '
            f'stroke-width="1.8"/><circle cx="{last[0]:.1f}" cy="{last[1]:.1f}" '
            f'r="2.4" fill="{color}"/></svg>')


def scatter(xs, ys, labels=None, title="", subtitle="", w=680, h=420,
            xlabel="", ylabel="", theme_lock=None):
    """Two-variable relationships — e.g. post length vs engagement rate."""
    X = [_num(v, "scatter x") for v in xs]
    Y = [_num(v, "scatter y") for v in ys]
    if len(X) != len(Y):
        raise ChartError(f"scatter: {len(X)} x values vs {len(Y)} y values")
    pairs = [(a, b_, (labels[i] if labels and i < len(labels) else None))
             for i, (a, b_) in enumerate(zip(X, Y)) if a is not None and b_ is not None]
    if not pairs:
        raise ChartError("scatter: no complete x/y pairs")

    top = _top_pad(title, subtitle)
    left, right, bottom = 60, 20, 48
    pw, ph = w - left - right, h - top - bottom
    xt = _nice_ticks(min(p[0] for p in pairs), max(p[0] for p in pairs))
    yt = _nice_ticks(min(p[1] for p in pairs), max(p[1] for p in pairs))
    xs_, xe_ = xt[0], xt[-1]
    ys_, ye_ = yt[0], yt[-1]
    xspan, yspan = (xe_ - xs_) or 1.0, (ye_ - ys_) or 1.0

    b = []
    for t in yt:
        y = top + ph - (t - ys_) / yspan * ph
        b.append(f'<line class="gl" x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}"/>')
        b.append(f'<text class="lbl" x="{left-8}" y="{y+4:.1f}" text-anchor="end">'
                 f'{_esc(_fmt(t))}</text>')
    for t in xt:
        x = left + (t - xs_) / xspan * pw
        b.append(f'<text class="lbl" x="{x:.1f}" y="{top+ph+18}" '
                 f'text-anchor="middle">{_esc(_fmt(t))}</text>')
    for px_, py_, lab in pairs:
        cx = left + (px_ - xs_) / xspan * pw
        cy = top + ph - (py_ - ys_) / yspan * ph
        b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="var(--c0)" '
                 f'opacity="0.72"/>')
        if lab and len(pairs) <= 20:
            b.append(f'<text class="lbl" x="{cx+7:.1f}" y="{cy+4:.1f}">{_esc(lab)}</text>')
    if xlabel:
        b.append(f'<text class="lbl" x="{left+pw/2:.1f}" y="{h-10}" '
                 f'text-anchor="middle">{_esc(xlabel)}</text>')
    if ylabel:
        b.append(f'<text class="lbl" x="14" y="{top+ph/2:.1f}" '
                 f'transform="rotate(-90 14 {top+ph/2:.1f})" '
                 f'text-anchor="middle">{_esc(ylabel)}</text>')
    b.append(f'<line class="ax" x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}"/>')
    return _frame(w, h, title, subtitle, "".join(b), theme_lock)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def render_csv(args) -> str:
    rows = csvio.read_rows(args.csv)
    have = list(rows[0].keys())
    for col in filter(None, [args.x] + (args.y or []) + [args.series_col]):
        if col not in have:
            raise ChartError(f"column {col!r} not in CSV. Columns: {', '.join(have)}")
    if not args.y:
        raise ChartError("--y is required")

    x = [r[args.x] for r in rows] if args.x else list(range(1, len(rows) + 1))
    kind = args.type

    if args.series_col and len(args.y) == 1:
        groups: dict[str, dict[str, str]] = {}
        for r in rows:
            groups.setdefault(r[args.series_col], {})[r[args.x]] = r[args.y[0]]
        xs = sorted({r[args.x] for r in rows}, key=lambda v: (str(v)))
        series = {g: [vals.get(k) for k in xs] for g, vals in groups.items()}
        if kind in ("line", "area"):
            return line(xs, series, title=args.title, subtitle=args.subtitle,
                        unit=args.unit, area_fill=(kind == "area"),
                        theme_lock=args.theme)
        if kind in ("stacked", "stacked_bar"):
            return stacked_bar(xs, series, title=args.title, subtitle=args.subtitle,
                               unit=args.unit, theme_lock=args.theme,
                               percent=args.percent)
        raise ChartError(f"--series-col is not supported for --type {kind}")

    if kind in ("line", "area"):
        vals = {c: [r[c] for r in rows] for c in args.y}
        return line(x, vals if len(args.y) > 1 else [r[args.y[0]] for r in rows],
                    title=args.title, subtitle=args.subtitle, unit=args.unit,
                    area_fill=(kind == "area"), theme_lock=args.theme)
    if kind == "bar":
        return bar(x, [r[args.y[0]] for r in rows], title=args.title,
                   subtitle=args.subtitle, unit=args.unit, theme_lock=args.theme,
                   color_by_label=True)
    if kind == "hbar":
        return hbar(x, [r[args.y[0]] for r in rows], title=args.title,
                    subtitle=args.subtitle, unit=args.unit, theme_lock=args.theme)
    if kind == "donut":
        return donut(x, [r[args.y[0]] for r in rows], title=args.title,
                     subtitle=args.subtitle, unit=args.unit, theme_lock=args.theme)
    if kind == "scatter":
        if len(args.y) < 2 and not args.x:
            raise ChartError("scatter needs --x and --y")
        return scatter([r[args.x] for r in rows], [r[args.y[0]] for r in rows],
                       labels=[r.get(args.series_col) for r in rows] if args.series_col else None,
                       title=args.title, subtitle=args.subtitle,
                       xlabel=args.x, ylabel=args.y[0], theme_lock=args.theme)
    if kind in ("stacked", "stacked_bar"):
        return stacked_bar(x, {c: [r[c] for r in rows] for c in args.y},
                           title=args.title, subtitle=args.subtitle, unit=args.unit,
                           theme_lock=args.theme, percent=args.percent)
    if kind == "sparkline":
        return sparkline([r[args.y[0]] for r in rows], theme_lock=args.theme)
    raise ChartError(f"unknown --type {kind}")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="chartkit", description="Dependency-free, theme-aware SVG charts.")
    p.add_argument("--type", default="line", help=(
        "line | area | bar | hbar | stacked | donut | heatmap | scatter | sparkline"))
    p.add_argument("--csv", required=True, help="CSV path, or - for stdin")
    p.add_argument("--x", help="column for the x axis / category labels")
    p.add_argument("--y", action="append", help="value column (repeatable)")
    p.add_argument("--series-col", help="column whose values split data into series")
    p.add_argument("--title", default="")
    p.add_argument("--subtitle", default="")
    p.add_argument("--unit", default="", help="suffix on value labels, e.g. % or ms")
    p.add_argument("--percent", action="store_true", help="normalize stacks to 100%%")
    p.add_argument("--theme", choices=["light", "dark"],
                   help="pin one palette instead of adapting to the viewer")
    p.add_argument("--out", help="write here instead of stdout")
    a = p.parse_args(argv)
    try:
        svg = render_csv(a)
    except (ChartError, csvio.CsvError, OSError) as e:
        print(f"chartkit: {e}", file=sys.stderr)
        return 2
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(a.out)
    else:
        sys.stdout.write(svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
