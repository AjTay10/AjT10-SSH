"""Platform parsers against recorded upstream payloads.

Every handler walks third-party JSON or HTML through .get() chains. Until now
the only way to learn that a parser broke was to run `reach doctor` against the
live internet, which conflates three different failures: our parser changed,
the vendor changed their payload, or this container's egress got blocked.

These tests answer only the first question. They are fully offline — the
`no_network` fixture turns any real request into a failure — so a red result
here always means the code is wrong, never that a website is down.

Refreshing a fixture is deliberate: re-record it, and the diff shows exactly
what the vendor changed.
"""

import json

import pytest


@pytest.fixture
def stub(monkeypatch, reach):
    """Point the transport helpers at recorded bytes."""
    def go(*, json_payload=None, body=None, status=200):
        if json_payload is not None:
            monkeypatch.setattr(reach, "get_json", lambda *a, **k: json_payload)
        if body is not None:
            monkeypatch.setattr(reach, "http", lambda *a, **k: (status, body))
        monkeypatch.setattr(reach, "_validate_url", lambda u: u)
    return go


# ------------------------------------------------------------------- x


def test_x_parses_a_real_syndication_payload(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("x_syndication_tweet.json"))
    r = reach.cmd_x(args("20"))
    assert r["platform"] == "x"
    assert r["backend"] == "syndication"
    assert r["author"] == "jack"
    assert "twttr" in r["content"]
    assert r["url"].endswith("/20")


def test_x_exposes_engagement_counts(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("x_syndication_tweet.json"))
    r = reach.cmd_x(args("20"))
    assert isinstance(r["likes"], int)


def test_x_tombstone_is_an_error_not_a_row_of_nulls(reach, args, stub):
    """Deleted, protected and age-restricted posts come back HTTP 200 with no
    fields. Returning them as a Tweet yields author=None, text=None."""
    stub(json_payload={"__typename": "TweetTombstone",
                       "tombstone": {"text": {"text": "This Post was deleted."}}})
    with pytest.raises(reach.ReachError) as e:
        reach.cmd_x(args("20"))
    assert "deleted" in str(e.value).lower()


def test_x_extracts_id_from_a_url(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("x_syndication_tweet.json"))
    r = reach.cmd_x(args("https://x.com/jack/status/20"))
    assert r["url"].endswith("/20")


def test_x_photos_are_surfaced_as_media(reach, args, stub):
    stub(json_payload={"__typename": "Tweet", "text": "t", "user": {},
                       "photos": [{"url": "https://img/1.jpg"}, {}]})
    assert reach.cmd_x(args("20"))["media"] == ["https://img/1.jpg"]


# ------------------------------------------------------------- bluesky


def test_bluesky_search_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("bluesky_search.json"))
    r = reach.cmd_bluesky(args("anthropic", user=None))
    assert r["backend"] == "searchPosts"
    assert r["posts"]
    first = r["posts"][0]
    assert first["author"] and first["text"] is not None


def test_bluesky_author_feed_uses_a_different_endpoint(reach, args, monkeypatch,
                                                       reach_calls):
    r = reach.cmd_bluesky(args(None, user="@alice.bsky.social"))
    assert r["backend"] == "getAuthorFeed"
    assert r["user"] == "alice.bsky.social", "the leading @ must be stripped"
    assert "getAuthorFeed" in reach_calls[-1]


@pytest.fixture
def reach_calls(monkeypatch, reach):
    calls = []

    def fake(url, *a, **k):
        calls.append(url)
        return {"feed": [{"post": {"record": {"text": "hi"},
                                   "author": {"handle": "alice.bsky.social"}}}],
                "posts": []}
    monkeypatch.setattr(reach, "get_json", fake)
    return calls


def test_bluesky_tolerates_missing_nested_keys(reach, args, stub):
    stub(json_payload={"posts": [{}, {"record": {}, "author": {}}]})
    r = reach.cmd_bluesky(args("q", user=None))
    assert len(r["posts"]) == 2


# ------------------------------------------------------------ mastodon


def test_mastodon_tag_timeline_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("mastodon_tag.json"))
    r = reach.cmd_mastodon(args("ai", instance=None))
    assert r["posts"]
    assert all("author" in p for p in r["posts"])


def test_mastodon_strips_html_from_status_bodies(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("mastodon_tag.json"))
    r = reach.cmd_mastodon(args("ai", instance=None))
    assert not any("<p>" in (p["text"] or "") for p in r["posts"])


def test_mastodon_honours_a_custom_instance(reach, args, monkeypatch):
    seen = []
    monkeypatch.setattr(reach, "get_json",
                        lambda u, *a, **k: seen.append(u) or [])
    reach.cmd_mastodon(args("tag", instance="fosstodon.org"))
    assert "fosstodon.org" in seen[0]


# ------------------------------------------------------------ telegram


def test_telegram_extracts_messages_from_the_preview_page(reach, args, stub,
                                                          fixture_bytes):
    stub(body=fixture_bytes("telegram_channel.html"))
    r = reach.cmd_telegram(args("telegram"))
    assert r["backend"] == "t.me/s preview"
    assert r["channel"] == "telegram"
    assert r["posts"]
    assert all(isinstance(p, str) for p in r["posts"])


@pytest.mark.parametrize("given", [
    "telegram", "@telegram", "https://t.me/telegram", "https://t.me/s/telegram",
])
def test_telegram_normalises_channel_forms(reach, args, stub, fixture_bytes, given):
    stub(body=fixture_bytes("telegram_channel.html"))
    assert reach.cmd_telegram(args(given))["channel"] == "telegram"


def test_telegram_empty_page_is_an_explicit_error(reach, args, stub):
    stub(body=b"<html><body>no messages</body></html>")
    with pytest.raises(reach.ReachError) as e:
        reach.cmd_telegram(args("nosuchchannel"))
    assert "private" in str(e.value) or "does not exist" in str(e.value)


def test_telegram_non_200_is_an_error(reach, args, stub):
    stub(body=b"", status=404)
    with pytest.raises(reach.ReachError):
        reach.cmd_telegram(args("nope"))


# ------------------------------------------------------------------ hn


def test_hn_parses_algolia(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("hn_algolia.json"))
    r = reach.cmd_hn(args("anthropic"))
    assert r["results"]
    assert all(h["title"] for h in r["results"])
    assert all(h["url"].startswith("http") for h in r["results"])


def test_hn_synthesises_a_url_for_text_posts(reach, args, stub):
    """Ask HN entries have no `url`; without the fallback the caller gets None
    and cannot open the discussion."""
    stub(json_payload={"hits": [{"title": "Ask HN", "objectID": "123"}]})
    assert reach.cmd_hn(args("q"))["results"][0]["url"].endswith("id=123")


# -------------------------------------------------------- stackoverflow


def test_stackoverflow_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("stackexchange.json"))
    r = reach.cmd_stackoverflow(args("python asyncio", site=None))
    assert r["results"]
    assert all("title" in h for h in r["results"])


def test_stackoverflow_unescapes_titles(reach, args, stub):
    stub(json_payload={"items": [{"title": "a &amp; b", "link": "u"}]})
    assert reach.cmd_stackoverflow(args("q", site=None))["results"][0]["title"] == "a & b"


# ------------------------------------------------------------ wikipedia


def test_wikipedia_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("wikipedia_search.json"))
    r = reach.cmd_wikipedia(args("anthropic", lang=None, full=False))
    assert r["results"]
    assert all(h["url"].startswith("https://en.wikipedia.org/wiki/")
               for h in r["results"])


def test_wikipedia_builds_urls_with_underscores(reach, args, stub):
    stub(json_payload={"query": {"search": [{"title": "Machine learning"}]}})
    r = reach.cmd_wikipedia(args("q", lang=None, full=False))
    assert r["results"][0]["url"].endswith("Machine_learning")


def test_wikipedia_snippets_are_plain_text(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("wikipedia_search.json"))
    r = reach.cmd_wikipedia(args("anthropic", lang=None, full=False))
    assert not any("<span" in h["snippet"] for h in r["results"])


def test_wikipedia_missing_results_key_is_not_a_crash(reach, args, stub):
    stub(json_payload={})
    assert reach.cmd_wikipedia(args("q", lang=None, full=False))["results"] == []


# ------------------------------------------------------------- discord


def test_discord_invite_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("discord_invite.json"))
    r = reach.cmd_discord(args("https://discord.gg/python"))
    assert r["backend"] == "invite api"
    assert r["title"]
    assert "members:" in r["content"]


@pytest.mark.parametrize("given", [
    "https://discord.gg/python", "https://discord.com/invite/python", "python",
])
def test_discord_accepts_every_invite_form(reach, args, stub, fixture_json, given):
    stub(json_payload=fixture_json("discord_invite.json"))
    assert reach.cmd_discord(args(given))["backend"] == "invite api"


def test_discord_guild_id_uses_the_widget_api(reach, args, stub):
    stub(json_payload={"id": "1", "name": "Guild", "presence_count": 5,
                       "channels": [{"name": "general"}]})
    r = reach.cmd_discord(args("267624335836053506"))
    assert r["backend"] == "widget api"
    assert "general" in r["content"]


def test_discord_widget_disabled_explains_itself(reach, args, monkeypatch, reach_err):
    with pytest.raises(reach.ReachError) as e:
        reach.cmd_discord(args("267624335836053506"))
    assert "widget" in str(e.value).lower()


@pytest.fixture
def reach_err(monkeypatch, reach):
    def boom(*a, **k):
        raise reach.ReachError("HTTP 403 from discord.com")
    monkeypatch.setattr(reach, "get_json", boom)


# --------------------------------------------------------------- vimeo


def test_vimeo_oembed_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("vimeo_oembed.json"))
    r = reach.cmd_vimeo(args("https://vimeo.com/347119375"))
    assert r["backend"] == "oembed"
    assert r["title"]
    assert r["uploader"]


def test_vimeo_falls_back_to_the_title_when_there_is_no_description(reach, args, stub):
    stub(json_payload={"title": "Only a title"})
    assert reach.cmd_vimeo(args("https://vimeo.com/1"))["content"] == "Only a title"


# -------------------------------------------------------------- tiktok


def test_tiktok_oembed_parses(reach, args, stub, fixture_json):
    stub(json_payload=fixture_json("tiktok_oembed.json"))
    r = reach.cmd_tiktok(args("https://www.tiktok.com/@scout2015/video/671833539"))
    assert r["backend"] == "oembed"
    assert r["author"]
    assert r["content"]


# ------------------------------------------------------------ snapchat


def test_snapchat_reads_opengraph_from_a_real_profile(reach, args, stub,
                                                      fixture_bytes):
    """Snapchat's profile page is a JS shell; the og: tags are the content."""
    stub(body=fixture_bytes("snapchat_profile.html"))
    r = reach.cmd_snapchat(args("teamsnapchat"))
    assert r["backend"].startswith("direct")
    assert r["content"]


def test_snapchat_builds_a_profile_url_from_a_bare_username(reach, args,
                                                           monkeypatch, reach_seen):
    reach.cmd_snapchat(args("teamsnapchat"))
    assert reach_seen[0] == "https://www.snapchat.com/add/teamsnapchat"


@pytest.fixture
def reach_seen(monkeypatch, reach, fixture_bytes):
    seen = []

    def fake(url, *a, **k):
        seen.append(url)
        return 200, fixture_bytes("snapchat_profile.html")
    monkeypatch.setattr(reach, "http", fake)
    monkeypatch.setattr(reach, "_validate_url", lambda u: u)
    return seen


# --------------------------------------------------- feeds via platforms


def test_rss_command_parses_a_real_feed(reach, args, stub, fixture_bytes):
    stub(body=fixture_bytes("rss_hn.xml"))
    r = reach.cmd_rss(args("https://hnrss.org/frontpage", n=3))
    assert r["platform"] == "rss"
    assert len(r["posts"]) == 3


def test_rss_autodiscovers_from_an_html_page(reach, args, monkeypatch,
                                             fixture_bytes):
    """A well-formed HTML page is also well-formed XML, so 'it parsed' is not
    proof it was a feed — autodiscovery has to fire."""
    pages = {
        "https://example.com/": (
            200,
            b'<html><head><link rel="alternate" '
            b'type="application/rss+xml" href="/feed.xml"></head></html>'),
        "https://example.com/feed.xml": (200, fixture_bytes("rss_hn.xml")),
    }
    monkeypatch.setattr(reach, "http", lambda u, *a, **k: pages[u])
    monkeypatch.setattr(reach, "_validate_url", lambda u: u)
    r = reach.cmd_rss(args("https://example.com/", n=2))
    assert r["url"] == "https://example.com/feed.xml"
    assert len(r["posts"]) == 2


def test_rss_page_with_no_feed_is_an_explicit_error(reach, args, stub):
    stub(body=b"<html><head></head><body>nothing</body></html>")
    with pytest.raises(reach.ReachError) as e:
        reach.cmd_rss(args("https://example.com/"))
    assert "advertises none" in str(e.value)


def test_medium_reads_the_feed_not_the_metered_page(reach, args, monkeypatch,
                                                    fixture_bytes):
    seen = []

    def fake(url, *a, **k):
        seen.append(url)
        return 200, fixture_bytes("rss_medium.xml")
    monkeypatch.setattr(reach, "http", fake)
    monkeypatch.setattr(reach, "_validate_url", lambda u: u)
    r = reach.cmd_medium(args("https://medium.com/@medium", n=2))
    assert r["backend"] == "feed"
    assert seen[0] == "https://medium.com/feed/@medium"


def test_substack_derives_the_feed_url(reach, args, monkeypatch, fixture_bytes):
    seen = []

    def fake(url, *a, **k):
        seen.append(url)
        return 200, fixture_bytes("rss_medium.xml")
    monkeypatch.setattr(reach, "http", fake)
    monkeypatch.setattr(reach, "_validate_url", lambda u: u)
    reach.cmd_substack(args("https://bigtechnology.substack.com", n=1))
    assert seen[0] == "https://bigtechnology.substack.com/feed"


# ------------------------------------------------------------- degraded


def test_reddit_labels_a_non_reddit_substitute(reach, args, monkeypatch):
    """CLAUDE.md forbids presenting an Exa substitute as "what Reddit said".
    When no result is actually from reddit.com the output must say so."""
    monkeypatch.setattr(reach, "exa_search",
                        lambda q, n: "A blog post about rust\nhttps://blog.example")
    out = reach._reddit_search("rust", 2)
    assert "not Reddit" in out


def test_reddit_drops_cached_block_pages(reach, args, monkeypatch):
    monkeypatch.setattr(
        reach, "exa_search",
        lambda q, n: ("reddit.com/r/rust thread text\n---\n"
                      "You've been blocked by network security"))
    out = reach._reddit_search("rust", 2)
    assert "blocked by network security" not in out
    assert "dropped" in out


def test_reddit_total_failure_names_the_cause(reach, args, monkeypatch):
    monkeypatch.setattr(reach, "exa_search", lambda q, n: "")
    with pytest.raises(reach.ReachError) as e:
        reach._reddit_search("rust", 2)
    assert "unreachable" in str(e.value)


def test_weibo_login_wall_is_labelled_in_the_backend(reach, args, monkeypatch):
    """`ok: -100` is Weibo's anonymous-refused signal. Callers should see that,
    not an unexplained empty result."""
    monkeypatch.setattr(reach, "get_json", lambda *a, **k: {"ok": -100})
    monkeypatch.setattr(reach, "exa_search", lambda q, n: "substitute results")
    r = reach.cmd_weibo(args("ai"))
    assert "login required" in r["backend"]


def test_exa_only_platforms_report_a_login_wall_as_such(reach, args, monkeypatch):
    """The message must contain a token _is_auth_failure recognises, or the
    CLI reports exit 5 (dead backend) for what is really exit 4."""
    monkeypatch.setattr(reach, "exa_fetch", lambda *a, **k: "short")
    monkeypatch.setattr(reach, "_validate_url", lambda u: u)
    with pytest.raises(reach.ReachError) as e:
        reach._exa_only("instagram", args("https://instagram.com/p/1"), "hint")
    assert reach._is_auth_failure(str(e.value))
