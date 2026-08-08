#!/usr/bin/env python3
"""social_ingest — normalize native platform exports into one schema.

Every platform names the same number differently. YouTube says "Views",
TikTok says "Video views", LinkedIn says "Impressions", X says "impressions",
Instagram says "Reach" for something subtly different. This maps them all onto
one table so a single dashboard can compare them honestly — and it says out
loud where a metric is *not* comparable rather than quietly averaging it.

    python3 tools/social_ingest.py --csv yt.csv --platform youtube --out norm.csv
    python3 tools/social_ingest.py --csv a.csv --platform tiktok \\
        --csv b.csv --platform instagram --out norm.csv --summary
    python3 tools/social_ingest.py --inspect unknown_export.csv

Unified schema:
    date, platform, post_id, title, impressions, reach, engagements,
    likes, comments, shares, saves, clicks, followers_delta, watch_time_sec,
    video_views, er_pct

`er_pct` is engagements / impressions * 100 when both exist. It is left blank
rather than guessed when the denominator is missing. Stdlib only. Reads files
only — this never touches a network or a platform API.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import csvio  # noqa: E402

FIELDS = ["date", "platform", "post_id", "title", "impressions", "reach",
          "engagements", "likes", "comments", "shares", "saves", "clicks",
          "followers_delta", "watch_time_sec", "video_views", "er_pct"]

# Aliases are matched case-insensitively after stripping punctuation, so
# "Video views", "video_views" and "Video Views (total)" all land together.
ALIASES = {
    "date": ["date", "day", "post date", "published", "publish time",
             "publish date", "time", "date posted", "created", "created at",
             "post publish date", "video publish time"],
    "post_id": ["post id", "id", "video id", "tweet id", "content id",
                "permalink", "post link", "url", "share url", "media id"],
    "title": ["title", "caption", "post text", "description", "text", "tweet text",
              "video title", "post caption", "headline"],
    "impressions": ["impressions", "views", "post views", "plays", "impression",
                    "total impressions", "content views", "views (total)",
                    "impressions total"],
    "reach": ["reach", "accounts reached", "unique views", "unique viewers",
              "reached accounts", "unique impressions", "people reached"],
    "engagements": ["engagements", "total engagements", "interactions",
                    "total interactions", "engagement", "reactions total"],
    "likes": ["likes", "like", "favorites", "reactions", "hearts", "upvotes",
              "likes count", "thumbs up"],
    "comments": ["comments", "comment", "replies", "comment count", "reply count"],
    "shares": ["shares", "share", "retweets", "reposts", "shares count",
               "repost count", "sends"],
    "saves": ["saves", "saved", "bookmarks", "save count", "bookmark count",
              "collects", "added to favorites"],
    "clicks": ["clicks", "link clicks", "url clicks", "outbound clicks",
               "website clicks", "clicks total", "profile clicks"],
    "followers_delta": ["followers gained", "new followers", "net followers",
                        "follows", "subscribers gained", "net follows",
                        "follower change", "subscribers"],
    "watch_time_sec": ["watch time", "watch time (seconds)", "total watch time",
                       "view time", "watch time (hours)", "average view duration",
                       "total time watched"],
    "video_views": ["video views", "video view", "plays", "views", "vv",
                    "3-second views", "2-second views"],
}

# Where a platform's export lies to you if you take the columns at face value.
CAVEATS = {
    "youtube": "Views are counted after ~30s or full watch on Shorts; "
               "impressions here are thumbnail impressions, not views.",
    "tiktok": "A 'view' is counted at 0s (immediate autoplay). TikTok views "
              "are not comparable to YouTube views — never chart them on one axis.",
    "instagram": "Reach is unique accounts; impressions can be many per account. "
                 "Reels 'plays' start at ~1s.",
    "facebook": "Video views default to 3-second. 'Reach' is deduped per day, "
                "so summing daily reach over a month overcounts.",
    "x": "Impressions include timeline scroll-past. Engagement rate on X is "
         "typically 5-10x lower than Instagram by construction, not by quality.",
    "twitter": "Same as x — impressions include scroll-past.",
    "linkedin": "Impressions are feed-render based; dwell time drives distribution "
                "more than clicks do.",
    "reddit": "Upvote counts are fuzzed by the platform. Treat exact numbers as "
              "approximate and rank-order only.",
    "pinterest": "Impressions accrue for months after publishing — a post's totals "
                 "are never final. Compare at fixed age, not calendar date.",
    "youtube_shorts": "Shorts and long-form share a channel but not an algorithm; "
                      "never blend their retention numbers.",
    "threads": "Views count at render. Comparable to X impressions, not to "
               "Instagram reach.",
    "snapchat": "Story views expire; exports only cover the retention window.",
    "twitch": "Average concurrent viewers matters more than total views.",
    "bluesky": "No native analytics export; numbers are third-party estimates.",
    "discord": "Engagement is message volume, not impressions. Do not compute ER.",
    "telegram": "Channel views count once per user, forever — a cumulative counter, "
                "not a daily one. Diff it before charting.",
    "whatsapp": "Channel metrics are limited to views and reactions.",
    "youtube_community": "Reach is a fraction of subscribers by design.",
}

PLATFORMS = sorted(set(list(CAVEATS.keys()) + ["weibo", "douyin", "xiaohongshu",
                                               "kuaishou", "wechat", "vk",
                                               "line", "tumblr", "medium",
                                               "substack", "quora", "twitch"]))


class IngestError(ValueError):
    pass


def norm_key(s):
    return re.sub(r"[^a-z0-9 ]", " ", str(s).lower()).replace("_", " ").strip()


def squash(s):
    return re.sub(r"\s+", " ", norm_key(s))


def build_map(headers, platform):
    """Return {unified_field: source_header}.

    Two rules keep this honest, both learned the hard way:

    1. Exact header matches are resolved for *every* field before any fuzzy
       match is attempted. Otherwise a loose alias on an early field eats a
       column that a later field matches exactly.
    2. Fuzzy matching is word-boundary, never bare substring. A plain
       ``"id" in header`` check happily maps ``Video publish time`` to
       ``post_id``, because "video" contains "id".
    """
    lookup = {squash(h): h for h in headers}
    out, claimed = {}, set()

    for field, names in ALIASES.items():                     # pass 1: exact
        for want in names:
            w = squash(want)
            if w in lookup and lookup[w] not in claimed:
                out[field] = lookup[w]
                claimed.add(lookup[w])
                break

    for field, names in ALIASES.items():                     # pass 2: bounded
        if field in out:
            continue
        for h_sq, h in lookup.items():
            if h in claimed:
                continue
            if any(re.search(rf"\b{re.escape(squash(w))}\b", h_sq)
                   for w in names if len(squash(w)) >= 3):
                out[field] = h
                claimed.add(h)
                break

    # 'views' is ambiguous: on video-first platforms it means video_views, and
    # those platforms genuinely have no impression metric to report.
    if platform in ("tiktok", "youtube_shorts", "douyin", "kuaishou", "snapchat"):
        imp = out.get("impressions")
        if imp and squash(imp) in ("views", "video views", "plays", "play count"):
            out.pop("impressions")
            out.setdefault("video_views", imp)
    return out


def to_num(v):
    if v is None:
        return None
    s = str(v).strip().replace(",", "").replace("%", "").replace("$", "")
    if s == "" or s.lower() in {"n/a", "na", "-", "--", "null", "none"}:
        return None
    m = 1.0
    if s and s[-1] in "kKmMbB":
        m = {"k": 1e3, "m": 1e6, "b": 1e9}[s[-1].lower()]
        s = s[:-1]
    try:
        return float(s) * m
    except ValueError:
        return None


def to_date(v):
    s = str(v).strip()
    if not s:
        return ""
    for f in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d, %Y",
              "%d %b %Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
              "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s[:len(f) + 6], f).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return s[:10]


def ingest_one(path, platform, warnings):
    rows = csvio.read_rows(path)
    headers = [h for h in rows[0].keys() if h is not None]
    mapping = build_map(headers, platform)
    if "date" not in mapping:
        warnings.append(f"{path}: no date-like column found; rows will sort badly")
    unmapped = [h for h in headers if h not in mapping.values()]

    out = []
    for r in rows:
        rec = {f: "" for f in FIELDS}
        rec["platform"] = platform
        for field, src in mapping.items():
            raw = r.get(src, "")
            if field == "date":
                rec["date"] = to_date(raw)
            elif field in ("post_id", "title"):
                rec[field] = str(raw).replace("\n", " ").strip()[:300]
            else:
                v = to_num(raw)
                rec[field] = "" if v is None else round(v, 4)

        if platform in ("youtube", "youtube_shorts") and rec["watch_time_sec"] != "":
            src = mapping.get("watch_time_sec", "").lower()
            if "hour" in src:
                rec["watch_time_sec"] = round(float(rec["watch_time_sec"]) * 3600, 2)
            elif "minute" in src:
                rec["watch_time_sec"] = round(float(rec["watch_time_sec"]) * 60, 2)

        if rec["engagements"] == "":
            parts = [rec[k] for k in ("likes", "comments", "shares", "saves")
                     if rec[k] != ""]
            if parts:
                rec["engagements"] = round(sum(float(p) for p in parts), 2)

        denom = rec["impressions"] or rec["reach"] or rec["video_views"]
        if rec["engagements"] != "" and denom not in ("", 0):
            rec["er_pct"] = round(float(rec["engagements"]) / float(denom) * 100, 3)
        out.append(rec)

    if unmapped:
        warnings.append(
            f"{path}: {len(unmapped)} column(s) not mapped and dropped: "
            f"{', '.join(unmapped[:8])}")
    if platform in CAVEATS:
        warnings.append(f"{platform}: {CAVEATS[platform]}")
    return out


def cmd_inspect(path):
    rows = csvio.read_rows(path)
    headers = list(rows[0].keys())
    print(f"{len(rows)} rows, {len(headers)} columns\n")
    guesses = {}
    for plat in ("youtube", "tiktok", "instagram", "x", "linkedin", "facebook"):
        m = build_map(headers, plat)
        guesses[plat] = len(m)
    best = max(guesses.items(), key=lambda kv_: kv_[1])
    mapping = build_map(headers, best[0])
    rev = {v: k for k, v in mapping.items()}
    print(f"{'source column':<38}{'maps to':<20}sample")
    print("-" * 78)
    for h in headers:
        sample = str(rows[0].get(h, ""))[:22]
        print(f"{str(h)[:37]:<38}{rev.get(h, '— dropped —'):<20}{sample}")
    print(f"\nbest-guess platform: {best[0]} ({best[1]} columns matched)")
    print("Pass --platform explicitly; the guess is a convenience, not a decision.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="social_ingest",
                                description=__doc__.split("\n")[0])
    p.add_argument("--csv", action="append", default=[],
                   help="input CSV (repeatable; pair with --platform in order)")
    p.add_argument("--platform", action="append", default=[],
                   help=f"one per --csv. Known: {', '.join(PLATFORMS[:12])}…")
    p.add_argument("--out", help="write normalized CSV here (default: stdout)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--summary", action="store_true",
                   help="print per-platform totals after writing")
    p.add_argument("--inspect", help="show how one file's columns would map, then exit")
    p.add_argument("--list-platforms", action="store_true")
    a = p.parse_args(argv)

    try:
        if a.list_platforms:
            for pl in PLATFORMS:
                print(f"{pl:<20}{CAVEATS.get(pl, '')}")
            return 0
        if a.inspect:
            return cmd_inspect(a.inspect)
        if not a.csv:
            raise IngestError("need at least one --csv (or use --inspect)")
        if len(a.platform) != len(a.csv):
            raise IngestError(
                f"got {len(a.csv)} --csv but {len(a.platform)} --platform; "
                "they must pair up one-to-one and in order")

        warnings, records = [], []
        for path, plat in zip(a.csv, a.platform):
            plat = plat.strip().lower()
            if plat not in PLATFORMS:
                warnings.append(
                    f"{plat}: not a known platform — mapped generically. "
                    f"Run --list-platforms to see the known set.")
            records.extend(ingest_one(path, plat, warnings))

        records.sort(key=lambda r: (r["date"], r["platform"]))

        if a.json:
            payload = json.dumps({"records": records, "warnings": warnings}, indent=2)
            if a.out:
                with open(a.out, "w", encoding="utf-8") as fh:
                    fh.write(payload + "\n")
            else:
                print(payload)
        else:
            fh = open(a.out, "w", newline="", encoding="utf-8") if a.out else sys.stdout
            try:
                w = csv.DictWriter(fh, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(records)
            finally:
                if a.out:
                    fh.close()
            if a.out:
                print(f"{a.out}: {len(records)} rows", file=sys.stderr)

        for w_ in warnings:
            print(f"note: {w_}", file=sys.stderr)

        if a.summary:
            agg = defaultdict(lambda: defaultdict(float))
            for r in records:
                agg[r["platform"]]["posts"] += 1
                for k in ("engagements", "followers_delta"):
                    if r[k] != "":
                        agg[r["platform"]][k] += float(r[k])
                # Video-first platforms report no impressions at all; falling
                # back keeps them out of the "0 reach, 0% ER" bucket, which is
                # a reporting artifact rather than a result.
                denom = r["impressions"] or r["video_views"] or r["reach"]
                if denom != "":
                    agg[r["platform"]]["impressions"] += float(denom)
            print(f"\n{'platform':<16}{'posts':>8}{'impressions':>16}"
                  f"{'engagements':>14}{'ER%':>8}", file=sys.stderr)
            print("-" * 62, file=sys.stderr)
            for plat, v in sorted(agg.items()):
                er = (v["engagements"] / v["impressions"] * 100) if v["impressions"] else 0
                print(f"{plat:<16}{int(v['posts']):>8,}{int(v['impressions']):>16,}"
                      f"{int(v['engagements']):>14,}{er:>8.2f}", file=sys.stderr)
            print("\nDo not rank platforms on this ER column alone — the "
                  "denominators are defined differently per platform (see notes).",
                  file=sys.stderr)
        return 0
    except (IngestError, csvio.CsvError, OSError) as e:
        print(f"social_ingest: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
