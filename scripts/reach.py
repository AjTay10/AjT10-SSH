#!/usr/bin/env python3
"""
reach — read the major social platforms and any website from this container.

Agent Reach routes everything through Jina Reader and per-platform CLIs that
assume either a desktop browser session or an unblocked residential IP. Neither
holds here: Jina Reader answers 401 to our egress IP, and Reddit/TikTok/
Instagram block it outright. This tool implements the access paths that were
measured to actually work, with an explicit fallback chain per platform, so a
blocked primary degrades instead of failing.

Every command prints human-readable text by default and structured JSON with
--json. Exit codes: 0 ok, 3 no content, 4 platform needs credentials, 5 all
backends failed.

  reach web URL                     any webpage as markdown
  reach search QUERY [--site D]     semantic web search (Exa)
  reach x URL|ID                    a tweet/post on X
  reach reddit QUERY|URL            reddit threads
  reach bluesky QUERY [--user H]    bluesky posts
  reach mastodon TAG|URL            mastodon posts
  reach telegram CHANNEL            public telegram channel
  reach tiktok URL                  tiktok video
  reach instagram URL|QUERY         instagram post/profile
  reach facebook URL|QUERY          facebook video/page
  reach linkedin URL|QUERY          linkedin profile/company/jobs
  reach threads URL|QUERY           threads post/profile
  reach pinterest URL|QUERY         pinterest pin/board
  reach youtube URL|QUERY           youtube video/search
  reach wikipedia QUERY             wikipedia articles
  reach hn QUERY                    hacker news
  reach stackoverflow QUERY         stack overflow
  reach doctor                      probe every backend live
"""

import argparse
import html as _html
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

__version__ = "1.0.0"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 30
MAX_BYTES = 8 * 1024 * 1024

EXIT_OK, EXIT_EMPTY, EXIT_NEEDS_AUTH, EXIT_FAILED = 0, 3, 4, 5


class ReachError(Exception):
    """A backend failed in a way the caller should see."""


# --------------------------------------------------------------------- http


def http(url, headers=None, timeout=TIMEOUT, accept_errors=False):
    """GET a URL. Returns (status, body_bytes). Raises ReachError on transport
    failure so every caller can treat a dead backend uniformly."""
    hdrs = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(MAX_BYTES)
    except urllib.error.HTTPError as e:
        try:
            body = e.read(MAX_BYTES)
        except Exception:
            body = b""
        if accept_errors:
            return e.code, body
        # JSON APIs explain themselves in the error body ("Profile not found").
        # Surfacing that beats a bare status code for the caller.
        detail = ""
        try:
            j = json.loads(body.decode("utf-8", errors="replace"))
            if isinstance(j, dict):
                detail = str(j.get("message") or j.get("error") or "")[:120]
        except Exception:
            pass
        raise ReachError(f"HTTP {e.code} from {_host(url)}"
                         + (f": {detail}" if detail else ""))
    except Exception as e:  # timeouts, DNS, TLS
        raise ReachError(f"{type(e).__name__} reaching {_host(url)}: {e}")


def get_json(url, headers=None, timeout=TIMEOUT):
    status, body = http(url, headers=headers, timeout=timeout)
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        raise ReachError(f"non-JSON response from {_host(url)} (HTTP {status})")


def _host(url):
    try:
        return urllib.parse.urlparse(url).netloc or url[:40]
    except Exception:
        return url[:40]


def _validate_url(url):
    """Reject anything that is not a plain public http(s) URL.

    Mirrors agent_reach.utils.url.normalize_public_http_url so this tool cannot
    become the SSRF hole that agent-reach carefully is not.
    """
    import ipaddress
    import socket

    if not isinstance(url, str) or "\n" in url or "\r" in url or not url.strip():
        raise ReachError("invalid URL")
    p = urllib.parse.urlparse(url.strip())
    if p.scheme not in ("http", "https"):
        raise ReachError("only public http(s) URLs are allowed")
    if p.username or p.password:
        raise ReachError("URLs with embedded credentials are not allowed")
    host = p.hostname
    if not host:
        raise ReachError("invalid URL: no host")
    if host.lower() in ("localhost",) or host.lower().endswith(".localhost") \
            or host.lower().endswith(".internal") or host.lower().endswith(".local"):
        raise ReachError("only public http(s) URLs are allowed")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise ReachError(f"cannot resolve host: {host}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ReachError("only public http(s) URLs are allowed")
    return url.strip()


# ------------------------------------------------------------------ html→md


_TAG_RE = re.compile(r"<[^>]+>")
_DROP_RE = re.compile(
    r"<(script|style|noscript|svg|head|nav|footer|form|iframe|template)\b.*?</\1>",
    re.I | re.S,
)
_BR_RE = re.compile(r"<(br|/p|/div|/li|/h[1-6]|/tr)\b[^>]*>", re.I)
_LI_RE = re.compile(r"<li\b[^>]*>", re.I)
_H_RE = re.compile(r"<h([1-6])\b[^>]*>", re.I)


def html_to_text(raw, max_chars=20000):
    """Convert HTML to readable text.

    Uses BeautifulSoup when available for correctness and falls back to regex
    stripping so the tool still works if the optional dependency is absent.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "head",
                         "nav", "footer", "form", "iframe", "template"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup.body or soup
        text = main.get_text("\n", strip=True)
    except Exception:
        body = _DROP_RE.sub(" ", raw)
        body = _H_RE.sub(lambda m: "\n\n" + "#" * int(m.group(1)) + " ", body)
        body = _LI_RE.sub("\n- ", body)
        body = _BR_RE.sub("\n", body)
        text = _html.unescape(_TAG_RE.sub("", body))
    lines = [ln.strip() for ln in text.splitlines()]
    out, blank = [], 0
    for ln in lines:
        if not ln:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    text = "\n".join(out).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[truncated at {max_chars} chars]"
    return text


def html_title(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    return _html.unescape(m.group(1)).strip() if m else ""


# -------------------------------------------------------------------- exa


def exa_available():
    return shutil.which("mcporter") is not None


def exa_call(tool, args, timeout=150):
    """Call an Exa MCP tool through mcporter.

    Exa fetches server-side, which is why it reaches pages this container's IP
    is blocked from. It is the fallback for every platform below.
    """
    if not exa_available():
        raise ReachError("mcporter not installed — Exa backend unavailable")
    cmd = ["mcporter", "call", f"exa.{tool}"] + args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ReachError(f"Exa {tool} timed out after {timeout}s")
    out = (p.stdout or "").strip()
    if p.returncode != 0 and not out:
        err = (p.stderr or "").strip().splitlines()
        raise ReachError(f"Exa {tool} failed: {err[-1] if err else 'no output'}")
    if not out:
        raise ReachError(f"Exa {tool} returned nothing")
    return out


def exa_search(query, n=5):
    return exa_call("web_search_exa", [f"query={query}", f"numResults={n}"])


def exa_fetch(urls, max_chars=6000):
    payload = json.dumps(list(urls))
    return exa_call("web_fetch_exa", [f"urls={payload}", f"maxCharacters={max_chars}"])


def _blocked(text):
    """Exa returns 200 with the origin's block page for hard-blocked sites."""
    low = text.lower()
    return any(m in low for m in (
        "you've been blocked by network security",
        "blocked by network security",
        "just a moment...",
        "verifying your browser",
        "enable javascript and cookies to continue",
    ))


# --------------------------------------------------------------- platforms


def cmd_web(a):
    """Any webpage. Direct fetch first (fast, full text), Exa second (reaches
    what our IP cannot), Jina last (usually 401 here, kept for other hosts)."""
    url = _validate_url(a.target)
    attempts = []
    try:
        status, body = http(url, accept_errors=True)
        if status == 200:
            text = html_to_text(body, a.max_chars)
            # Short-but-real pages exist (example.com is ~150 chars). Only fall
            # through when the page is a block/challenge page or near-empty,
            # which is the signature of a JS-only or gated site.
            if len(text) >= 80 and not _blocked(text):
                return {"platform": "web", "backend": "direct", "url": url,
                        "title": html_title(body), "content": text}
            attempts.append(f"direct: {'block page' if _blocked(text) else 'thin content'}")
        else:
            attempts.append(f"direct: HTTP {status}")
    except ReachError as e:
        attempts.append(f"direct: {e}")

    for name, fn in (("exa", lambda: exa_fetch([url], a.max_chars)),
                     ("jina", lambda: http("https://r.jina.ai/" + url)[1].decode("utf-8", "replace"))):
        try:
            text = fn()
            if text and not _blocked(text):
                return {"platform": "web", "backend": name, "url": url,
                        "title": html_title(text) or "", "content": text.strip()}
            attempts.append(f"{name}: block page")
        except ReachError as e:
            attempts.append(f"{name}: {e}")
    raise ReachError("all web backends failed — " + "; ".join(attempts))


def cmd_search(a):
    q = a.target
    if a.site:
        q = f"{q} (on {a.site})"
    return {"platform": "search", "backend": "exa", "query": q,
            "content": exa_search(q, a.n)}


_X_ID_RE = re.compile(r"(?:status(?:es)?/)(\d+)")
_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _x_token(tweet_id):
    """Reproduce the token X's own embed script derives from the post id.

    Old ids are served with any token, but modern ids 404 without the real
    one: ((id / 1e15) * PI) rendered in base 36 with zeros and the point
    stripped — the JS is `.toString(36).replace(/(0+|\\.)/g, '')`.
    """
    import math

    v = (int(tweet_id) / 1e15) * math.pi
    whole = int(v)
    frac = v - whole
    s = ""
    n = whole
    if n == 0:
        s = "0"
    while n:
        s = _B36[n % 36] + s
        n //= 36
    out = [s, "."]
    for _ in range(24):
        frac *= 36
        d = int(frac)
        out.append(_B36[d])
        frac -= d
    return re.sub(r"(0+|\.)", "", "".join(out))


def cmd_x(a):
    """A post on X/Twitter.

    The syndication endpoint that powers embedded tweets serves full post JSON
    without any credential — the only anonymous read path left on X. Search
    still needs a logged-in session, so it routes to Exa.
    """
    target = a.target.strip()
    m = _X_ID_RE.search(target)
    tweet_id = m.group(1) if m else (target if target.isdigit() else None)

    if tweet_id:
        base = (f"https://cdn.syndication.twimg.com/tweet-result"
                f"?id={tweet_id}&lang=en&token=")
        last = ""
        d = None
        for token in (_x_token(tweet_id), "a"):
            try:
                d = get_json(base + token)
                break
            except ReachError as e:
                last = str(e)
        if d is not None:
            # Deleted, protected and age-restricted posts come back 200 as a
            # TweetTombstone with no fields; say so instead of returning nulls.
            if d.get("__typename") and d["__typename"] != "Tweet":
                note = (((d.get("tombstone") or {}).get("text") or {}).get("text")
                        or "post is unavailable")
                raise ReachError(f"X post {tweet_id}: {note}")
            user = d.get("user") or {}
            photos = [p.get("url") for p in (d.get("photos") or []) if p.get("url")]
            return {
                "platform": "x", "backend": "syndication",
                "url": f"https://x.com/i/status/{tweet_id}",
                "author": user.get("screen_name"), "author_name": user.get("name"),
                "created_at": d.get("created_at"), "text": d.get("text"),
                "likes": d.get("favorite_count"),
                "replies": (d.get("conversation_count")
                            or d.get("reply_count")),
                "media": photos,
                "content": d.get("text") or "",
            }
        try:
            o = get_json("https://publish.twitter.com/oembed?url=" +
                         urllib.parse.quote(f"https://twitter.com/i/status/{tweet_id}", safe=""))
            return {"platform": "x", "backend": "oembed",
                    "url": o.get("url"), "author": o.get("author_name"),
                    "content": html_to_text(o.get("html", ""))}
        except ReachError as e:
            raise ReachError(f"syndication ({last}) and oembed ({e}) both failed")

    return {"platform": "x", "backend": "exa (search needs no login this way)",
            "query": target,
            "content": exa_search(f"posts on x.com / twitter.com about {target}", a.n)}


def cmd_reddit(a):
    """Reddit blocks this container on every direct route (www, old, .rss, and
    every public redlib mirror tested — 403/429/Cloudflare), and Exa's fetcher
    is blocked too. Exa's *index* still has the thread text, so search is the
    only working read path."""
    t = a.target.strip()
    if t.startswith("http"):
        _validate_url(t)
        try:
            text = exa_fetch([t], a.max_chars)
            if not _blocked(text):
                return {"platform": "reddit", "backend": "exa-fetch",
                        "url": t, "content": text}
        except ReachError:
            pass
        slug = re.sub(r"[/_-]+", " ", urllib.parse.urlparse(t).path).strip()
        return {"platform": "reddit", "backend": "exa-search (direct fetch blocked)",
                "url": t,
                "content": _reddit_search(f"reddit thread {slug}", a.n)}
    sub = f" in r/{a.subreddit}" if a.subreddit else ""
    return {"platform": "reddit", "backend": "exa-search",
            "query": t,
            "content": _reddit_search(
                f"reddit.com discussion thread about {t}{sub}", a.n)}


_RESULT_SPLIT = re.compile(r"\n-{3,}\n")


def _reddit_search(query, n):
    """Exa's index holds real thread text for most Reddit URLs, but for some it
    only cached Reddit's "You've been blocked by network security" page. Drop
    those results instead of handing the caller a block page as if it were the
    discussion, and retry once with a reworded query if everything was junk."""
    spare = []
    for q in (query, query.replace("reddit.com", "") +
              " site:reddit.com user opinions comments"):
        raw = exa_search(q, max(n * 2, 6))
        blocks = [b for b in _RESULT_SPLIT.split(raw) if b.strip()]
        kept = [b for b in blocks if not _blocked(b)]
        # Prefer blocks that really are Reddit threads; anything else is a
        # topical substitute and must be labelled as one, not passed off as
        # "what Reddit said".
        on_reddit = [b for b in kept if "reddit.com" in b]
        if on_reddit:
            out = "\n---\n".join(on_reddit[:n])
            if len(kept) < len(blocks):
                out += ("\n\n[note: some Reddit results were dropped — Exa only "
                        "had Reddit's block page cached for them]")
            return out
        spare.extend(kept)
    if spare:
        return ("[note: no Reddit thread was readable for this query — Reddit "
                "blocks this container directly and Exa had only block pages "
                "cached. The results below are OTHER sites discussing the same "
                "topic, not Reddit.]\n\n" + "\n---\n".join(spare[:n]))
    raise ReachError(
        "Reddit is unreachable from this container (direct, mirrors and Exa's "
        "cache are all blocked for this query). Try `reach search` with "
        "different wording, or ask the user for Reddit credentials.")


BSKY = "https://api.bsky.app/xrpc"


def cmd_bluesky(a):
    """Bluesky's AppView serves search, profiles and threads with no auth.
    Note the host: public.api.bsky.app answers 403 to searchPosts from here,
    api.bsky.app does not."""
    if a.user:
        handle = a.user.lstrip("@")
        d = get_json(f"{BSKY}/app.bsky.feed.getAuthorFeed"
                     f"?actor={urllib.parse.quote(handle)}&limit={a.n}")
        posts = []
        for item in d.get("feed", []):
            rec = (item.get("post") or {}).get("record") or {}
            au = (item.get("post") or {}).get("author") or {}
            posts.append({"author": au.get("handle"), "text": rec.get("text"),
                          "created_at": rec.get("createdAt"),
                          "likes": (item.get("post") or {}).get("likeCount")})
        return {"platform": "bluesky", "backend": "getAuthorFeed",
                "user": handle, "posts": posts}
    d = get_json(f"{BSKY}/app.bsky.feed.searchPosts"
                 f"?q={urllib.parse.quote(a.target)}&limit={a.n}")
    posts = []
    for p in d.get("posts", []):
        rec = p.get("record") or {}
        au = p.get("author") or {}
        posts.append({"author": au.get("handle"), "text": rec.get("text"),
                      "created_at": rec.get("createdAt"),
                      "likes": p.get("likeCount"), "reposts": p.get("repostCount")})
    return {"platform": "bluesky", "backend": "searchPosts",
            "query": a.target, "posts": posts}


def cmd_mastodon(a):
    """Any Mastodon instance exposes public timelines unauthenticated; default
    to mastodon.social and accept a full status URL too."""
    t = a.target.strip()
    if t.startswith("http"):
        _validate_url(t)
        p = urllib.parse.urlparse(t)
        m = re.search(r"/(\d+)$", p.path)
        if m:
            d = get_json(f"https://{p.netloc}/api/v1/statuses/{m.group(1)}")
            return {"platform": "mastodon", "backend": "statuses", "url": t,
                    "author": (d.get("account") or {}).get("acct"),
                    "created_at": d.get("created_at"),
                    "content": html_to_text(d.get("content", ""))}
        return cmd_web(argparse.Namespace(target=t, max_chars=a.max_chars))
    inst = a.instance or "mastodon.social"
    d = get_json(f"https://{inst}/api/v1/timelines/tag/"
                 f"{urllib.parse.quote(t.lstrip('#'))}?limit={a.n}")
    posts = [{"author": (s.get("account") or {}).get("acct"),
              "created_at": s.get("created_at"),
              "url": s.get("url"),
              "text": html_to_text(s.get("content", ""), 800)} for s in d]
    return {"platform": "mastodon", "backend": f"{inst} tag timeline",
            "tag": t, "posts": posts}


def cmd_telegram(a):
    """Public channels render a full server-side preview at t.me/s/<channel>."""
    ch = a.target.strip().lstrip("@")
    ch = re.sub(r"^https?://t\.me/(s/)?", "", ch).strip("/")
    status, body = http(f"https://t.me/s/{urllib.parse.quote(ch)}", accept_errors=True)
    if status != 200:
        raise ReachError(f"t.me returned HTTP {status} for @{ch}")
    raw = body.decode("utf-8", errors="replace")
    msgs = re.findall(
        r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', raw, re.S)
    posts = [html_to_text(m, 1200) for m in msgs][-a.n:]
    if not posts:
        raise ReachError(f"no public messages found for @{ch} "
                         "(private channel, or the channel does not exist)")
    return {"platform": "telegram", "backend": "t.me/s preview",
            "channel": ch, "title": html_title(raw), "posts": posts}


def cmd_tiktok(a):
    """yt-dlp is IP-blocked on TikTok here ("Your IP address is blocked"), but
    the oEmbed endpoint is open and carries title/author/thumbnail."""
    t = a.target.strip()
    if t.startswith("http"):
        _validate_url(t)
        try:
            d = get_json("https://www.tiktok.com/oembed?url=" +
                         urllib.parse.quote(t, safe=""))
            return {"platform": "tiktok", "backend": "oembed", "url": t,
                    "author": d.get("author_name"), "title": d.get("title"),
                    "thumbnail": d.get("thumbnail_url"),
                    "content": d.get("title") or ""}
        except ReachError as e:
            first = str(e)
        try:
            return {"platform": "tiktok", "backend": "exa-fetch", "url": t,
                    "content": exa_fetch([t], a.max_chars)}
        except ReachError as e:
            raise ReachError(f"oembed ({first}) and Exa ({e}) both failed")
    return {"platform": "tiktok", "backend": "exa-search", "query": t,
            "content": exa_search(f"tiktok.com videos about {t}", a.n)}


def _ytdlp_or_exa(platform, target, a, search_hint):
    """Shared path for the video platforms yt-dlp still handles anonymously."""
    if target.startswith("http"):
        _validate_url(target)
        if shutil.which("yt-dlp"):
            try:
                p = subprocess.run(
                    ["yt-dlp", "--skip-download", "--dump-json",
                     "--no-warnings", "--socket-timeout", "20", target],
                    capture_output=True, text=True, timeout=120)
                if p.returncode == 0 and p.stdout.strip().startswith("{"):
                    d = json.loads(p.stdout.splitlines()[0])
                    # Many videos carry an empty description; fall back to the
                    # title so callers always get something to work with.
                    text = (d.get("description") or "").strip() or (d.get("title") or "")
                    return {"platform": platform, "backend": "yt-dlp",
                            "url": target, "title": d.get("title"),
                            "uploader": d.get("uploader") or d.get("channel"),
                            "duration": d.get("duration"),
                            "views": d.get("view_count"),
                            "upload_date": d.get("upload_date"),
                            "content": text[:a.max_chars]}
                err = (p.stderr or "").strip().splitlines()
                reason = err[-1][:160] if err else "unknown yt-dlp error"
            except subprocess.TimeoutExpired:
                reason = "yt-dlp timed out"
            except Exception as e:
                reason = f"{type(e).__name__}: {e}"
        else:
            reason = "yt-dlp not installed"
        try:
            text = exa_fetch([target], a.max_chars)
            if not _blocked(text):
                return {"platform": platform, "backend": f"exa-fetch (yt-dlp: {reason})",
                        "url": target, "content": text}
        except ReachError as e:
            reason += f"; exa: {e}"
        raise ReachError(f"{platform}: {reason}")
    return {"platform": platform, "backend": "exa-search", "query": target,
            "content": exa_search(f"{search_hint} {target}", a.n)}


def cmd_youtube(a):
    return _ytdlp_or_exa("youtube", a.target.strip(), a, "youtube.com videos about")


def cmd_facebook(a):
    return _ytdlp_or_exa("facebook", a.target.strip(), a, "facebook.com posts about")


def _exa_only(platform, a, search_hint, auth_note=None):
    """Platforms with no anonymous API: Exa is the only read path."""
    t = a.target.strip()
    if t.startswith("http"):
        _validate_url(t)
        text = exa_fetch([t], a.max_chars)
        if _blocked(text) or len(text.strip()) < 80:
            note = f" {auth_note}" if auth_note else ""
            raise ReachError(f"{platform}: page is login-walled for anonymous "
                             f"readers.{note}")
        return {"platform": platform, "backend": "exa-fetch", "url": t,
                "content": text}
    return {"platform": platform, "backend": "exa-search", "query": t,
            "content": exa_search(f"{search_hint} {t}", a.n)}


def cmd_instagram(a):
    return _exa_only("instagram", a, "instagram.com posts by or about",
                     "Instagram requires a logged-in session for post detail; "
                     "search still works.")


def cmd_linkedin(a):
    return _exa_only("linkedin", a, "linkedin.com profile or company page for")


def cmd_threads(a):
    t = a.target.strip()
    if t.startswith("http"):
        _validate_url(t)
        try:
            status, body = http(t, accept_errors=True)
            if status == 200:
                text = html_to_text(body, a.max_chars)
                if len(text) > 200 and not _blocked(text):
                    return {"platform": "threads", "backend": "direct",
                            "url": t, "title": html_title(body), "content": text}
        except ReachError:
            pass
    return _exa_only("threads", a, "threads.net posts by or about")


def cmd_pinterest(a):
    return _exa_only("pinterest", a, "pinterest.com pins or boards about")


def cmd_wikipedia(a):
    lang = a.lang or "en"
    d = get_json(f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search"
                 f"&srsearch={urllib.parse.quote(a.target)}&format=json&srlimit={a.n}")
    hits = [{"title": r["title"],
             "url": f"https://{lang}.wikipedia.org/wiki/"
                    + urllib.parse.quote(r["title"].replace(" ", "_")),
             "snippet": html_to_text(r.get("snippet", ""), 400)}
            for r in d.get("query", {}).get("search", [])]
    if hits and a.full:
        s = get_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
                     + urllib.parse.quote(hits[0]["title"].replace(" ", "_")))
        hits[0]["extract"] = s.get("extract")
    return {"platform": "wikipedia", "backend": "mediawiki api",
            "query": a.target, "results": hits}


def cmd_hn(a):
    d = get_json("https://hn.algolia.com/api/v1/search?query="
                 f"{urllib.parse.quote(a.target)}&hitsPerPage={a.n}")
    hits = [{"title": h.get("title") or h.get("story_title"),
             "url": h.get("url") or
                    f"https://news.ycombinator.com/item?id={h.get('objectID')}",
             "points": h.get("points"), "comments": h.get("num_comments"),
             "author": h.get("author"), "created_at": h.get("created_at")}
            for h in d.get("hits", [])]
    return {"platform": "hackernews", "backend": "algolia", "query": a.target,
            "results": hits}


def cmd_stackoverflow(a):
    d = get_json("https://api.stackexchange.com/2.3/search/advanced"
                 f"?order=desc&sort=votes&q={urllib.parse.quote(a.target)}"
                 f"&site={a.site or 'stackoverflow'}&pagesize={a.n}&filter=default")
    hits = [{"title": _html.unescape(i.get("title", "")), "url": i.get("link"),
             "score": i.get("score"), "answered": i.get("is_answered"),
             "tags": i.get("tags")} for i in d.get("items", [])]
    return {"platform": "stackoverflow", "backend": "stackexchange api",
            "query": a.target, "results": hits}


# ------------------------------------------------------------------ doctor

PROBES = [
    ("web",        lambda: cmd_web(_ns(target="https://example.com"))),
    ("search",     lambda: cmd_search(_ns(target="anthropic claude", site=None, n=2))),
    ("x",          lambda: cmd_x(_ns(target="20", n=2))),
    ("reddit",     lambda: cmd_reddit(_ns(target="rust programming language",
                                          subreddit=None, n=2))),
    ("bluesky",    lambda: cmd_bluesky(_ns(target="anthropic", user=None, n=2))),
    ("mastodon",   lambda: cmd_mastodon(_ns(target="ai", instance=None, n=2))),
    ("telegram",   lambda: cmd_telegram(_ns(target="telegram", n=2))),
    ("tiktok",     lambda: cmd_tiktok(_ns(
        target="https://www.tiktok.com/@scout2015/video/6718335390845095173", n=2))),
    ("youtube",    lambda: cmd_youtube(_ns(
        target="https://www.youtube.com/watch?v=dQw4w9WgXcQ", n=2))),
    ("facebook",   lambda: cmd_facebook(_ns(
        target="https://www.facebook.com/watch/?v=10153231379946729", n=2))),
    ("instagram",  lambda: cmd_instagram(_ns(target="nasa space photos", n=2))),
    ("linkedin",   lambda: cmd_linkedin(_ns(
        target="https://www.linkedin.com/company/anthropicresearch/", n=2))),
    ("threads",    lambda: cmd_threads(_ns(target="tech news", n=2))),
    ("pinterest",  lambda: cmd_pinterest(_ns(target="kitchen design ideas", n=2))),
    ("wikipedia",  lambda: cmd_wikipedia(_ns(target="anthropic", lang=None,
                                             n=2, full=False))),
    ("hn",         lambda: cmd_hn(_ns(target="anthropic", n=2))),
    ("stackoverflow", lambda: cmd_stackoverflow(_ns(target="python asyncio",
                                                    site=None, n=2))),
]


def _ns(**kw):
    kw.setdefault("max_chars", 3000)
    kw.setdefault("n", 5)
    return argparse.Namespace(**kw)


def cmd_doctor(a):
    results = {}
    width = max(len(n) for n, _ in PROBES)
    for name, fn in PROBES:
        try:
            r = fn()
            body = r.get("content") or r.get("posts") or r.get("results") or r.get("text")
            # A short answer is still an answer: the canonical probe tweet is
            # "just setting up my twttr" (24 chars). Only truly empty counts.
            size = len(json.dumps(body, ensure_ascii=False).strip()) if body else 0
            if size < 5:
                results[name] = {"status": "empty", "backend": r.get("backend"),
                                 "detail": "backend responded but returned no content"}
            else:
                results[name] = {"status": "ok", "backend": r.get("backend"),
                                 "detail": f"{size} chars"}
        except ReachError as e:
            results[name] = {"status": "fail", "backend": None, "detail": str(e)[:150]}
        except Exception as e:  # a probe must never take the report down
            results[name] = {"status": "fail", "backend": None,
                             "detail": f"{type(e).__name__}: {e}"[:150]}
        if not a.json:
            r = results[name]
            mark = {"ok": "  OK  ", "empty": " EMPTY", "fail": " FAIL "}[r["status"]]
            print(f"[{mark}] {name.ljust(width)}  {r['backend'] or ''}"
                  f"{'' if r['status'] == 'ok' else '  ' + r['detail']}", flush=True)
    n_ok = sum(1 for r in results.values() if r["status"] == "ok")
    if not a.json:
        print(f"\n{n_ok}/{len(results)} platforms reachable")
    return {"platform": "doctor", "results": results,
            "ok": n_ok, "total": len(results)}


# ------------------------------------------------------------------ render


def render(r):
    """Human-readable rendering. Keys are printed in a stable order so output
    diffs cleanly between runs."""
    if r.get("platform") == "doctor":
        return ""
    head = f"# {r.get('platform', '?')}"
    if r.get("title"):
        head += f" — {r['title']}"
    lines = [head]
    meta = [("backend", r.get("backend")), ("url", r.get("url")),
            ("query", r.get("query")), ("author", r.get("author")),
            ("author_name", r.get("author_name")), ("uploader", r.get("uploader")),
            ("channel", r.get("channel")), ("user", r.get("user")),
            ("tag", r.get("tag")), ("created_at", r.get("created_at")),
            ("upload_date", r.get("upload_date")), ("duration", r.get("duration")),
            ("views", r.get("views")), ("likes", r.get("likes")),
            ("replies", r.get("replies")), ("thumbnail", r.get("thumbnail"))]
    for k, v in meta:
        if v not in (None, "", []):
            lines.append(f"{k}: {v}")
    if r.get("media"):
        lines.append("media: " + ", ".join(r["media"]))
    lines.append("")
    if r.get("text"):
        lines.append(r["text"])
    if r.get("content"):
        lines.append(r["content"])
    for item in r.get("posts", []) or []:
        # Telegram yields plain strings, the API-backed platforms yield dicts.
        if isinstance(item, str):
            lines.append(f"- {item}\n")
            continue
        who = item.get("author") or ""
        when = (item.get("created_at") or "")[:19]
        stats = f"  ({item.get('likes')} likes)" if item.get("likes") else ""
        lines.append(f"- @{who} {when}{stats}\n  {item.get('text', '')}\n")
    for item in r.get("results", []) or []:
        lines.append(f"- {item.get('title')}\n  {item.get('url')}")
        for k in ("points", "score", "comments", "snippet", "extract"):
            if item.get(k):
                lines.append(f"  {k}: {item[k]}")
        lines.append("")
    return "\n".join(lines).strip()


# -------------------------------------------------------------------- main


def build_parser():
    p = argparse.ArgumentParser(
        prog="reach",
        description="Read the major social platforms and any website.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Exit codes:")[1].split("\n", 1)[1] if "Exit codes:" in __doc__ else None,
    )
    p.add_argument("--version", action="version", version=f"reach {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, target_help, **opts):
        s = sub.add_parser(name, help=target_help)
        if opts.get("target", True):
            s.add_argument("target", help=target_help)
        s.add_argument("--json", action="store_true", help="machine-readable output")
        s.add_argument("-n", type=int, default=5, help="max results (default 5)")
        s.add_argument("--max-chars", type=int, default=8000,
                       dest="max_chars", help="truncate page text (default 8000)")
        s.set_defaults(func=fn)
        return s

    add("web", cmd_web, "URL to read")
    s = add("search", cmd_search, "search query")
    s.add_argument("--site", help="bias results to a domain")
    add("x", cmd_x, "tweet URL, tweet ID, or search query")
    s = add("reddit", cmd_reddit, "thread URL or search query")
    s.add_argument("--subreddit", help="restrict a search to one subreddit")
    s = add("bluesky", cmd_bluesky, "search query")
    s.add_argument("--user", help="read this handle's feed instead of searching")
    s = add("mastodon", cmd_mastodon, "hashtag or status URL")
    s.add_argument("--instance", help="instance host (default mastodon.social)")
    add("telegram", cmd_telegram, "public channel name or t.me URL")
    add("tiktok", cmd_tiktok, "video URL or search query")
    add("instagram", cmd_instagram, "post/profile URL or search query")
    add("facebook", cmd_facebook, "video/page URL or search query")
    add("linkedin", cmd_linkedin, "profile/company URL or search query")
    add("threads", cmd_threads, "post/profile URL or search query")
    add("pinterest", cmd_pinterest, "pin/board URL or search query")
    add("youtube", cmd_youtube, "video URL or search query")
    s = add("wikipedia", cmd_wikipedia, "search query")
    s.add_argument("--lang", help="wiki language (default en)")
    s.add_argument("--full", action="store_true", help="include a summary extract")
    add("hn", cmd_hn, "search query")
    s = add("stackoverflow", cmd_stackoverflow, "search query")
    s.add_argument("--site", help="stackexchange site (default stackoverflow)")

    d = sub.add_parser("doctor", help="probe every backend live")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_doctor, target=None)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except ReachError as e:
        print(f"reach: {e}", file=sys.stderr)
        return EXIT_NEEDS_AUTH if "login" in str(e).lower() else EXIT_FAILED
    except KeyboardInterrupt:
        return 130

    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        out = render(result)
        if out:
            print(out)

    if result.get("platform") == "doctor":
        return EXIT_OK if result["ok"] else EXIT_FAILED
    has = any(result.get(k) for k in ("content", "text", "posts", "results"))
    if not has:
        print("reach: backend responded but returned no content", file=sys.stderr)
        return EXIT_EMPTY
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
