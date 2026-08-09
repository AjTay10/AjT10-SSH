#!/usr/bin/env python3
"""usage — which skills, commands, and tools actually get used.

A skill library rots by accumulation. Every skill competes to be selected, so
twenty that never fire make the six that do harder to reach. This reads Claude
Code's own session transcripts and reports what has actually been invoked, so
pruning is a decision about evidence rather than about taste.

    python3 tools/usage.py                  # table
    python3 tools/usage.py --archive        # bank this session, then report
    python3 tools/usage.py --days 90        # only recent sessions
    python3 tools/usage.py --json

Claude Code on the web runs in a container that is reclaimed after inactivity,
so transcripts rarely survive between sessions and the report would show "1
session" forever. `--archive` fixes that by banking a small tally per session
into .claude/data/usage/.

Those tallies contain counts and dates only — never prompts, replies, file
contents, or paths beyond the project directory name. They are small and
non-sensitive by construction, so they are safe to commit, which is what makes
history accumulate at all.

It deliberately refuses to call anything "unused" until there is enough history
to mean it. One session proves nothing, and a confident-looking drop list built
from one session is worse than no list at all.

Transcripts live in ~/.claude/projects/<encoded-cwd>/*.jsonl. Read-only —
this never modifies them. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TRANSCRIPTS = os.path.expanduser("~/.claude/projects")
ARCHIVE = os.path.join(ROOT, ".claude", "data", "usage")

# Below these, an "unused" verdict is not evidence, it is an artifact of a
# short history. The thresholds are deliberately conservative.
MIN_SESSIONS = 5
MIN_DAYS = 14

CMD_RE = re.compile(r"<command-name>\s*/?([\w-]+)\s*</command-name>")
TOOLSCRIPT_RE = re.compile(r"tools/([a-z_][a-z0-9_]*)\.py")


class UsageError(ValueError):
    pass


# --------------------------------------------------------------------------

def inventory():
    """What this repo actually defines."""
    def names(path, suffix=None, dirs=False):
        if not os.path.isdir(path):
            return set()
        if dirs:
            return {d for d in os.listdir(path)
                    if os.path.isdir(os.path.join(path, d))}
        return {f[:-len(suffix)] for f in os.listdir(path) if f.endswith(suffix)}

    return {
        "skills": names(os.path.join(ROOT, ".claude", "skills"), dirs=True),
        "commands": names(os.path.join(ROOT, ".claude", "commands"), ".md"),
        "tools": {n for n in names(os.path.join(ROOT, "tools"), ".py")
                  if n not in ("usage", "csvio")},   # csvio is a library, not a CLI
    }


def iter_records(transcripts):
    """Yield (timestamp, session_id, record) from every transcript found."""
    if not os.path.isdir(transcripts):
        raise UsageError(
            f"{transcripts} does not exist. Claude Code writes transcripts to "
            f"~/.claude/projects; pass --transcripts if yours are elsewhere.")
    files = []
    for base, _, names in os.walk(transcripts):
        files += [os.path.join(base, n) for n in names if n.endswith(".jsonl")]
    if not files:
        raise UsageError(
            f"no .jsonl transcripts under {transcripts}. Nothing to measure yet.")

    for path in sorted(files):
        session = os.path.splitext(os.path.basename(path))[0]
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue          # a partially-written tail is normal
                ts = None
                raw = rec.get("timestamp")
                if raw:
                    try:
                        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    except ValueError:
                        ts = None
                yield ts, rec.get("sessionId") or session, rec


def blocks(rec):
    msg = rec.get("message") or {}
    c = msg.get("content")
    return c if isinstance(c, list) else []


def text_of(rec):
    msg = rec.get("message") or {}
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c
                        if isinstance(b, dict) and b.get("type") == "text")
    return ""


def per_session(transcripts):
    """Tally each session separately, so archives dedupe by session id."""
    out = defaultdict(lambda: {"skills": Counter(), "commands": Counter(),
                               "tools": Counter(), "first": None, "last": None,
                               "project": None})
    for ts, session, rec in iter_records(transcripts):
        t = out[session]
        if ts:
            if t["first"] is None or ts < t["first"]:
                t["first"] = ts
            if t["last"] is None or ts > t["last"]:
                t["last"] = ts
        if rec.get("cwd") and not t["project"]:
            # Directory name only — never the full path of anyone's machine.
            t["project"] = os.path.basename(str(rec["cwd"]))

        for b in blocks(rec):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name"), b.get("input") or {}
            if name == "Skill":
                sk = (inp.get("skill") or "").strip()
                if sk:
                    t["skills"][sk] += 1
            elif name == "Bash":
                for m in TOOLSCRIPT_RE.findall(str(inp.get("command", ""))):
                    t["tools"][m] += 1
        for m in CMD_RE.findall(text_of(rec)):
            t["commands"][m] += 1
    return out


def load_archive(path=ARCHIVE):
    """Previously banked tallies. Counts and dates only."""
    out = {}
    if not os.path.isdir(path):
        return out
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".json"):
            continue
        try:
            rec = json.load(open(os.path.join(path, fn), encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue                     # a corrupt tally is not worth failing over
        sid = rec.get("session") or fn[:-5]
        parse = lambda v: datetime.fromisoformat(v) if v else None
        try:
            out[sid] = {
                "skills": Counter(rec.get("skills") or {}),
                "commands": Counter(rec.get("commands") or {}),
                "tools": Counter(rec.get("tools") or {}),
                "first": parse(rec.get("first")), "last": parse(rec.get("last")),
                "project": rec.get("project"),
            }
        except ValueError:
            continue
    return out


def save_archive(sessions, path=ARCHIVE):
    """Bank one small JSON per session. Never writes conversation content."""
    os.makedirs(path, exist_ok=True)
    written = 0
    for sid, t in sessions.items():
        if not (t["skills"] or t["commands"] or t["tools"]):
            continue                     # nothing worth recording
        payload = {
            "session": sid,
            "project": t["project"],
            "first": t["first"].isoformat() if t["first"] else None,
            "last": t["last"].isoformat() if t["last"] else None,
            "skills": dict(t["skills"]),
            "commands": dict(t["commands"]),
            "tools": dict(t["tools"]),
        }
        target = os.path.join(path, f"{sid}.json")
        body = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if os.path.isfile(target) and open(target, encoding="utf-8").read() == body:
            continue                     # unchanged; keep the diff clean
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.replace(tmp, target)          # atomic, as everything persistent here is
        written += 1
    return written


def merge(sessions, since=None):
    skills, commands, tools = Counter(), Counter(), Counter()
    last, stamps, projects = {}, [], Counter()
    counted = 0

    for sid, t in sessions.items():
        if since and t["last"] and t["last"] < since:
            continue
        counted += 1
        for k in ("first", "last"):
            if t[k]:
                stamps.append(t[k])
        if t["project"]:
            projects[t["project"]] += 1
        for bucket, src in ((skills, t["skills"]), (commands, t["commands"]),
                            (tools, t["tools"])):
            for name, n in src.items():
                bucket[name] += n
                if t["last"] and (name not in last or t["last"] > last[name]):
                    last[name] = t["last"]

    return {
        "skills": skills, "commands": commands, "tools": tools, "last": last,
        "sessions": counted,
        "first_seen": min(stamps) if stamps else None,
        "last_seen": max(stamps) if stamps else None,
        "projects": projects,
    }


def span_days(data):
    if not data["first_seen"] or not data["last_seen"]:
        return 0
    return max(0, (data["last_seen"] - data["first_seen"]).days)


def confident(data):
    """Is there enough history for an 'unused' verdict to mean anything?"""
    return data["sessions"] >= MIN_SESSIONS and span_days(data) >= MIN_DAYS


# --------------------------------------------------------------------------

def report(data, inv, args):
    now = datetime.now(timezone.utc)
    days = span_days(data)

    print(f"{data['sessions']} session(s) · {days} day(s) of history"
          + (f" · {data['first_seen'].date()} → {data['last_seen'].date()}"
             if data["first_seen"] else ""))
    if len(data["projects"]) > 1:
        print(f"across {len(data['projects'])} project director"
              f"{'y' if len(data['projects']) == 1 else 'ies'}")
    print()

    for label, key, defined in (("SKILLS", "skills", inv["skills"]),
                                ("COMMANDS", "commands", inv["commands"]),
                                ("TOOLS", "tools", inv["tools"])):
        counts = data[key]
        used = {n: c for n, c in counts.items() if n in defined}
        unused = sorted(defined - set(used))
        external = {n: c for n, c in counts.items() if n not in defined}

        print(f"{label}  ({len(defined)} defined here)")
        print("-" * 64)
        if used:
            for n, c in sorted(used.items(), key=lambda kv: (-kv[1], kv[0])):
                when = data["last"].get(n)
                ago = f"{(now - when).days}d ago" if when else "—"
                print(f"  {n:<28}{c:>5} use{'s' if c != 1 else ' '}   last {ago}")
        else:
            print("  none recorded")

        if unused:
            print(f"\n  not recorded ({len(unused)}):")
            for i in range(0, len(unused), 3):
                print("    " + "  ".join(f"{n:<24}" for n in unused[i:i + 3]).rstrip())

        if external and key == "skills":
            print(f"\n  used but defined elsewhere (built-in or plugin):")
            for n, c in sorted(external.items(), key=lambda kv: -kv[1])[:10]:
                print(f"    {n:<28}{c:>5}")
        print()

    # The verdict, and the refusal to give one prematurely.
    print("what to do with this")
    print("-" * 64)
    if not confident(data):
        print(f"  Not enough history to drop anything yet. This covers "
              f"{data['sessions']} session(s)")
        print(f"  over {days} day(s); the bar is {MIN_SESSIONS} sessions and "
              f"{MIN_DAYS} days.")
        print()
        print("  A skill absent from one session has not been rejected — it")
        print("  simply had no occasion to fire. Treat the counts above as a")
        print("  running tally, not a verdict.")
        if data["sessions"] <= 1:
            print()
            print("  Note: Claude Code on the web runs in a container that is")
            print("  reclaimed after inactivity, so transcripts do not survive")
            print("  between sessions. Run this with --archive at the end of a")
            print("  session to bank a small tally (counts and dates only, no")
            print("  conversation text) into .claude/data/usage/ and commit it.")
            print("  History then accumulates across sessions and this report")
            print("  becomes able to say something.")
    else:
        skills_unused = sorted(inv["skills"] - set(data["skills"]))
        if skills_unused:
            print(f"  {len(skills_unused)} skill(s) have not fired in "
                  f"{days} days across {data['sessions']} sessions.")
            print("  These are the honest drop candidates:")
            for n in skills_unused:
                print(f"    - {n}")
            print()
            print("  Before dropping one, check its description says *when* to")
            print("  use it in the words you would actually type. A good skill")
            print("  with a bad description looks identical to a useless one")
            print("  from here.")
        else:
            print("  Every skill defined here has fired at least once. Nothing")
            print("  to prune on this evidence.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="usage", description=__doc__.split("\n")[0])
    ap.add_argument("--transcripts", default=DEFAULT_TRANSCRIPTS,
                    help="where Claude Code session .jsonl files live")
    ap.add_argument("--days", type=int,
                    help="only count sessions from the last N days")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--archive", action="store_true",
                    help="bank this session's tally so history survives the "
                         "container being reclaimed")
    ap.add_argument("--archive-dir", default=ARCHIVE)
    a = ap.parse_args(argv)

    try:
        if a.days is not None and a.days < 1:
            raise UsageError("--days must be at least 1")
        since = (datetime.now(timezone.utc) - timedelta(days=a.days)) if a.days else None

        live = per_session(a.transcripts)
        if a.archive:
            n = save_archive(live, a.archive_dir)
            print(f"banked {n} session tally file(s) to "
                  f"{os.path.relpath(a.archive_dir, ROOT)}\n", file=sys.stderr)

        # Archived tallies first; live transcripts win where both exist, since
        # the live one is the same session with more of it recorded.
        sessions = load_archive(a.archive_dir)
        sessions.update(live)
        data = merge(sessions, since)
        inv = inventory()
    except (UsageError, OSError) as e:
        print(f"usage: {e}", file=sys.stderr)
        return 2

    if a.json:
        print(json.dumps({
            "sessions": data["sessions"],
            "span_days": span_days(data),
            "first_seen": data["first_seen"].isoformat() if data["first_seen"] else None,
            "last_seen": data["last_seen"].isoformat() if data["last_seen"] else None,
            "enough_history": confident(data),
            "defined": {k: sorted(v) for k, v in inv.items()},
            "skills": dict(data["skills"]),
            "commands": dict(data["commands"]),
            "tools": dict(data["tools"]),
            "unused_skills": sorted(inv["skills"] - set(data["skills"])),
            "unused_tools": sorted(inv["tools"] - set(data["tools"])),
            "last_used": {k: v.isoformat() for k, v in data["last"].items()},
        }, indent=2))
        return 0

    report(data, inv, a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
