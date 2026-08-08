"""RSS/Atom parsing and feed autodiscovery.

Feeds are the highest-yield path for "any popular website" — never login-walled
and usually full text where the HTML page is metered — so the parser has to
cope with both formats and with the malformed-but-common cases real publishers
ship. Every parametrised case below is a shape observed in a live feed.
"""

import pytest

RSS = """<?xml version="1.0"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <title>Example Feed</title>
  <item>
    <title>First &amp; best</title>
    <link>https://example.com/1</link>
    <dc:creator>Alice</dc:creator>
    <pubDate>Sat, 08 Aug 2026 00:11:02 +0000</pubDate>
    <description>&lt;p&gt;Body one.&lt;/p&gt;</description>
  </item>
  <item>
    <title>Second</title>
    <link>https://example.com/2</link>
    <content:encoded>&lt;p&gt;Richer body.&lt;/p&gt;</content:encoded>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Example</title>
  <entry>
    <title>Atom One</title>
    <link href="https://example.com/a1" rel="alternate"/>
    <id>tag:example.com,2026:1</id>
    <author><name>Bob</name></author>
    <updated>2026-08-08T00:11:02Z</updated>
    <summary>Atom body.</summary>
  </entry>
</feed>"""


def test_parses_rss(reach):
    feed = reach.parse_feed(RSS)
    assert feed["title"] == "Example Feed"
    assert len(feed["entries"]) == 2
    first = feed["entries"][0]
    assert first["title"] == "First & best"
    assert first["url"] == "https://example.com/1"
    assert first["author"] == "Alice"
    assert "Body one." in first["text"]


def test_parses_atom(reach):
    feed = reach.parse_feed(ATOM)
    assert feed["title"] == "Atom Example"
    e = feed["entries"][0]
    assert e["title"] == "Atom One"
    assert "Atom body." in e["text"]


def test_atom_link_comes_from_the_href_attribute(reach):
    """Atom <link/> is an empty element; reading .text yields nothing."""
    assert reach.parse_feed(ATOM)["entries"][0]["url"] == "https://example.com/a1"


def test_prefers_content_encoded_over_description(reach):
    assert "Richer body." in reach.parse_feed(RSS)["entries"][1]["text"]


def test_entry_html_is_converted_to_text(reach):
    assert "<p>" not in reach.parse_feed(RSS)["entries"][0]["text"]


def test_respects_the_entry_limit(reach):
    assert len(reach.parse_feed(RSS, n=1)["entries"]) == 1


def test_respects_max_chars(reach):
    long_body = "<description>" + ("x" * 5000) + "</description>"
    doc = RSS.replace("<description>&lt;p&gt;Body one.&lt;/p&gt;</description>", long_body)
    assert len(reach.parse_feed(doc, max_chars=100)["entries"][0]["text"]) < 200


def test_missing_title_gets_a_placeholder_not_a_crash(reach):
    doc = """<rss version="2.0"><channel><item>
             <link>https://example.com/x</link></item></channel></rss>"""
    assert reach.parse_feed(doc)["entries"][0]["title"] == "(untitled)"


def test_leading_bom_and_whitespace_are_tolerated(reach):
    """A stray BOM is a hard ParseError for ElementTree and a non-event for
    every real feed reader; publishers ship them constantly."""
    assert reach.parse_feed("﻿\n  " + RSS)["entries"]


def test_accepts_bytes(reach):
    assert reach.parse_feed(RSS.encode("utf-8"))["entries"]


def test_empty_feed_parses_to_no_entries(reach):
    doc = '<rss version="2.0"><channel><title>Nothing</title></channel></rss>'
    assert reach.parse_feed(doc)["entries"] == []


@pytest.mark.parametrize("junk", [
    "<html><body>not a feed</body></html>",
    "",
    "{\"json\": true}",
    "<rss><channel><item>unclosed",
])
def test_non_feed_input_raises_reacherror(reach, junk):
    with pytest.raises(reach.ReachError):
        reach.parse_feed(junk)


# --------------------------------------------------- recorded live feeds


def test_real_rss_feed(reach, fixture_bytes):
    feed = reach.parse_feed(fixture_bytes("rss_hn.xml"), n=5)
    assert feed["title"]
    assert len(feed["entries"]) == 5
    assert all(e["url"].startswith("http") for e in feed["entries"])
    assert all(e["title"] for e in feed["entries"])


def test_real_atom_feed(reach, fixture_bytes):
    feed = reach.parse_feed(fixture_bytes("atom_feed.xml"), n=3)
    assert feed["title"]
    assert feed["entries"]
    assert all(e["url"].startswith("http") for e in feed["entries"])


def test_real_medium_feed_carries_body_text(reach, fixture_bytes):
    """Medium's page is metered; its feed is not. If this stops returning body
    text the platform has silently degraded to headlines-only."""
    feed = reach.parse_feed(fixture_bytes("rss_medium.xml"), n=3)
    assert feed["entries"]
    assert any(len(e["text"]) > 200 for e in feed["entries"])


# ------------------------------------------------------------ discovery


@pytest.mark.parametrize("tag", [
    '<link rel="alternate" type="application/rss+xml" href="/feed.xml">',
    '<link type="application/rss+xml" rel="alternate" href="/feed.xml">',
    "<link rel='alternate' type='application/atom+xml' href='/feed.xml'>",
    '<link rel="alternate" type="application/rss+xml" title="RSS" href="/feed.xml"/>',
])
def test_discovers_feed_link(reach, tag):
    html = f"<html><head>{tag}</head></html>"
    assert reach.discover_feed(html, "https://example.com/blog/") == \
        "https://example.com/feed.xml"


def test_discovery_resolves_relative_urls(reach):
    html = '<link rel="alternate" type="application/rss+xml" href="rss">'
    assert reach.discover_feed(html, "https://example.com/blog/index.html") == \
        "https://example.com/blog/rss"


def test_discovery_keeps_absolute_urls(reach):
    html = ('<link rel="alternate" type="application/rss+xml" '
            'href="https://cdn.example.net/f.xml">')
    assert reach.discover_feed(html, "https://example.com/") == \
        "https://cdn.example.net/f.xml"


def test_discovery_unescapes_entities_in_href(reach):
    html = ('<link rel="alternate" type="application/rss+xml" '
            'href="/f?a=1&amp;b=2">')
    assert reach.discover_feed(html, "https://example.com/") == \
        "https://example.com/f?a=1&b=2"


def test_discovery_returns_none_when_absent(reach):
    assert reach.discover_feed("<html><head></head></html>", "https://example.com") is None


def test_discovery_ignores_stylesheets_and_icons(reach):
    html = ('<link rel="stylesheet" href="/a.css">'
            '<link rel="icon" href="/favicon.ico">')
    assert reach.discover_feed(html, "https://example.com") is None
