#!/usr/bin/env python3
"""calendar_gen — turn a weekly slot pattern into a real calendar.

A schedule that lives in a document you never open is not a schedule. This
emits a CSV to work from and an .ics file that imports into any calendar app,
so the slots appear where you already look.

    python3 tools/calendar_gen.py --start 2026-09-01 --weeks 8 \\
        --slot "Tue 09:00 teardown" --slot "Thu 09:00 clip" \\
        --slot "Sat 11:00 community" --tz America/New_York \\
        --out schedule.csv --ics schedule.ics

    python3 tools/calendar_gen.py --start 2026-09-01 --weeks 4 \\
        --slot "Tue 09:00 pillar" --skip 2026-09-15 --skip 2026-09-16

Stdlib only. Timezones use zoneinfo when the system has tzdata; otherwise
pass --utc-offset and it does the arithmetic without it.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date, datetime, timedelta, timezone

DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
SLOT_RE = re.compile(
    r"^\s*(mon|tue|wed|thu|fri|sat|sun)[a-z]*\s+(\d{1,2}):(\d{2})\s*(.*)$",
    re.IGNORECASE)


class CalError(ValueError):
    pass


def parse_slot(s):
    m = SLOT_RE.match(s)
    if not m:
        raise CalError(
            f"bad --slot {s!r}. Expected 'Tue 09:00 label', e.g. 'Thu 17:30 clip'")
    day, hh, mm, label = m.group(1).lower(), int(m.group(2)), int(m.group(3)), m.group(4)
    if hh > 23 or mm > 59:
        raise CalError(f"bad --slot {s!r}: {hh:02d}:{mm:02d} is not a valid time")
    return DAYS[day], hh, mm, (label.strip() or "post")


def get_tz(name, offset_hours):
    if offset_hours is not None:
        return timezone(timedelta(hours=offset_hours)), f"UTC{offset_hours:+g}"
    if not name:
        return timezone.utc, "UTC"
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name), name
    except Exception as e:                       # missing tzdata, bad name
        raise CalError(
            f"cannot load timezone {name!r} ({e}). Install tzdata "
            f"(pip install tzdata) or pass --utc-offset instead.")


def ics_escape(s):
    return (str(s).replace("\\", "\\\\").replace(";", r"\;")
            .replace(",", r"\,").replace("\n", r"\n"))


def fold(line):
    """RFC 5545 caps lines at 75 octets; continuation lines start with a space."""
    out, cur = [], line
    while len(cur.encode("utf-8")) > 75:
        cut = 74
        while len(cur[:cut].encode("utf-8")) > 74:
            cut -= 1
        out.append(cur[:cut])
        cur = " " + cur[cut:]
    out.append(cur)
    return "\r\n".join(out)


def build(start, weeks, slots, tz, skips, duration_min):
    events = []
    for w in range(weeks):
        week_start = start + timedelta(days=7 * w)
        # Anchor on the Monday of the week containing --start so slot weekdays
        # land where a human expects, rather than counting from an arbitrary day.
        monday = week_start - timedelta(days=week_start.weekday())
        for weekday, hh, mm, label in slots:
            d = monday + timedelta(days=weekday)
            if d < start or d in skips:
                continue
            local = datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
            events.append({
                "date": d.isoformat(),
                "weekday": d.strftime("%a"),
                "time": f"{hh:02d}:{mm:02d}",
                "slot": label,
                "week": w + 1,
                "status": "planned",
                "topic": "",
                "asset": "",
                "_dt": local,
                "_end": local + timedelta(minutes=duration_min),
            })
    events.sort(key=lambda e: e["_dt"])
    return events


def write_ics(events, path, tzlabel, stamp):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//claude-config//calendar_gen//EN", "CALSCALE:GREGORIAN"]
    for i, e in enumerate(events, 1):
        s = e["_dt"].astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        t = e["_end"].astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        uid = f"{e['date'].replace('-','')}-{i:04d}-calgen@local"
        lines += [
            "BEGIN:VEVENT",
            fold(f"UID:{uid}"),
            fold(f"DTSTAMP:{stamp}"),
            fold(f"DTSTART:{s}"),
            fold(f"DTEND:{t}"),
            fold(f"SUMMARY:{ics_escape(e['slot'])}"),
            fold("DESCRIPTION:" + ics_escape(
                f"Slot: {e['slot']} (week {e['week']}). Planned in {tzlabel}.")),
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\r\n".join(lines) + "\r\n")


def main(argv=None):
    p = argparse.ArgumentParser(prog="calendar_gen",
                                description=__doc__.split("\n")[0])
    p.add_argument("--start", required=True, help="YYYY-MM-DD (first week)")
    p.add_argument("--weeks", type=int, default=4)
    p.add_argument("--slot", action="append", required=True,
                   help="'Tue 09:00 label' (repeatable)")
    p.add_argument("--tz", default="", help="IANA name, e.g. America/New_York")
    p.add_argument("--utc-offset", type=float,
                   help="use instead of --tz when tzdata is unavailable")
    p.add_argument("--skip", action="append", default=[],
                   help="YYYY-MM-DD to leave empty (repeatable)")
    p.add_argument("--duration", type=int, default=30,
                   help="event length in minutes (default 30)")
    p.add_argument("--out", help="CSV path (default stdout)")
    p.add_argument("--ics", help="also write an .ics file here")
    p.add_argument("--stamp", default="20260101T000000Z",
                   help="DTSTAMP for ICS; fixed so reruns diff cleanly")
    a = p.parse_args(argv)

    try:
        if a.weeks < 1:
            raise CalError("--weeks must be at least 1")
        if a.weeks > 260:
            raise CalError("--weeks above 260 (5 years) is almost certainly a "
                           "mistake; a calendar beyond 4 weeks already goes stale")
        if a.duration < 1:
            raise CalError("--duration must be at least 1 minute")
        try:
            start = date.fromisoformat(a.start)
        except ValueError:
            raise CalError(f"--start {a.start!r} is not YYYY-MM-DD")
        skips = set()
        for s in a.skip:
            try:
                skips.add(date.fromisoformat(s))
            except ValueError:
                raise CalError(f"--skip {s!r} is not YYYY-MM-DD")

        slots = [parse_slot(s) for s in a.slot]
        tz, tzlabel = get_tz(a.tz, a.utc_offset)
        events = build(start, a.weeks, slots, tz, skips, a.duration)
        if not events:
            raise CalError(
                "no events generated — every slot fell before --start or was "
                "skipped. Check the weekday names against your start date.")

        cols = ["date", "weekday", "time", "slot", "week", "status", "topic", "asset"]
        fh = open(a.out, "w", newline="", encoding="utf-8") if a.out else sys.stdout
        try:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(events)
        finally:
            if a.out:
                fh.close()

        if a.ics:
            write_ics(events, a.ics, tzlabel, a.stamp)

        if a.out or a.ics:
            per_week = len(events) / a.weeks
            print(f"{len(events)} slots over {a.weeks} weeks "
                  f"({per_week:.1f}/week) in {tzlabel}", file=sys.stderr)
            if a.out:
                print(f"  csv → {a.out}", file=sys.stderr)
            if a.ics:
                print(f"  ics → {a.ics}", file=sys.stderr)
            if per_week > 7:
                print("\nnote: more than one slot per day. On ranked feeds, posts "
                      "compete with your own recent posts for the same audience. "
                      "Confirm this cadence beats a smaller one before committing.",
                      file=sys.stderr)
        return 0
    except (CalError, OSError) as e:
        print(f"calendar_gen: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
