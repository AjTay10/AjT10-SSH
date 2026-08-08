"""HTML handling.

html_to_text has two independent implementations — BeautifulSoup when it is
importable, a regex stripper when it is not — and callers cannot tell which one
ran. Both are exercised here, and the shared cases assert they agree, because
silent divergence between them is invisible in production.
"""

import sys

import pytest

SAMPLE = """
<html><head><title>  Title &amp; more </title>
<style>.a{color:red}</style><script>var x = 1 < 2;</script></head>
<body><nav>skip me</nav>
<article><h1>Heading</h1><p>First para.</p><p>Second para.</p>
<ul><li>one</li><li>two</li></ul>
<div>Tail &mdash; done</div></article>
<footer>footer junk</footer></body></html>
"""


@pytest.fixture
def no_bs4(monkeypatch, reach):
    """Force the regex fallback path."""
    monkeypatch.setitem(sys.modules, "bs4", None)
    return reach


@pytest.fixture(params=["bs4", "regex"])
def either_impl(request, monkeypatch, reach):
    if request.param == "regex":
        monkeypatch.setitem(sys.modules, "bs4", None)
    return reach


# ------------------------------------------------------------ both paths


def test_extracts_visible_text(either_impl):
    out = either_impl.html_to_text(SAMPLE)
    assert "First para." in out
    assert "Second para." in out
    assert "one" in out and "two" in out


def test_drops_script_and_style(either_impl):
    out = either_impl.html_to_text(SAMPLE)
    assert "color:red" not in out
    assert "var x" not in out


def test_drops_chrome(either_impl):
    out = either_impl.html_to_text(SAMPLE)
    assert "skip me" not in out
    assert "footer junk" not in out


def test_unescapes_entities(either_impl):
    assert "—" in either_impl.html_to_text("<p>a &mdash; b</p>")


def test_accepts_bytes(either_impl):
    assert "hello" in either_impl.html_to_text(b"<p>hello</p>")


def test_decodes_invalid_utf8_without_raising(either_impl):
    assert either_impl.html_to_text(b"<p>caf\xff</p>")


def test_truncation_is_marked(either_impl):
    out = either_impl.html_to_text("<p>" + ("x" * 500) + "</p>", max_chars=100)
    assert len(out) < 200
    assert "truncated at 100" in out


def test_collapses_runs_of_blank_lines(either_impl):
    out = either_impl.html_to_text("<p>a</p>" + "<br>" * 10 + "<p>b</p>")
    assert "\n\n\n" not in out


def test_empty_input_is_empty_not_an_error(either_impl):
    assert either_impl.html_to_text("") == ""


def test_both_implementations_agree_on_content(reach, monkeypatch):
    """The two paths may format differently, but they must not disagree about
    which words are on the page."""
    with_bs4 = set(reach.html_to_text(SAMPLE).split())
    monkeypatch.setitem(sys.modules, "bs4", None)
    without = set(reach.html_to_text(SAMPLE).split())
    for word in ("First", "Second", "one", "two"):
        assert word in with_bs4 and word in without
    for junk in ("skip", "footer"):
        assert junk not in with_bs4 and junk not in without


def test_regex_fallback_really_is_the_fallback(no_bs4):
    """Guards the guard: if the import stub stopped working, every 'regex' case
    above would silently retest BeautifulSoup."""
    with pytest.raises(ImportError):
        from bs4 import BeautifulSoup  # noqa: F401


# ---------------------------------------------------------------- title


@pytest.mark.parametrize("raw,want", [
    ("<title>Hello</title>", "Hello"),
    ("<title>  padded  </title>", "padded"),
    ("<TITLE>Caps</TITLE>", "Caps"),
    ("<title>a &amp; b</title>", "a & b"),
    ("<title>multi\nline</title>", "multi\nline"),
    ("<title></title>", ""),
    ("no title here", ""),
])
def test_html_title(reach, raw, want):
    assert reach.html_title(raw) == want


def test_html_title_accepts_bytes(reach):
    assert reach.html_title(b"<title>B</title>") == "B"


# ------------------------------------------------------------- opengraph


OG = """<html><head>
<meta property="og:title" content="The Title">
<meta property="og:description" content="A description.">
<meta property="og:image" content="https://cdn/img.png">
<meta property="og:site_name" content="Site">
<meta name="twitter:description" content="twitter copy">
<meta name="description" content="plain description">
<meta charset="utf-8">
<meta property="og:title">
</head><body></body></html>"""


def test_og_meta_reads_property_and_name(reach):
    m = reach.og_meta(OG)
    assert m["og:title"] == "The Title"
    assert m["og:description"] == "A description."
    assert m["description"] == "plain description"


def test_og_meta_normalises_twitter_cards(reach):
    """twitter:* is the same data under a different prefix; callers should not
    have to check both."""
    m = reach.og_meta('<meta name="twitter:title" content="T">')
    assert m.get("og:title") == "T"


def test_og_meta_prefers_the_first_value_seen(reach):
    m = reach.og_meta(OG)
    assert m["og:description"] == "A description."


def test_og_meta_skips_tags_without_content(reach):
    assert "charset" not in reach.og_meta(OG)


def test_og_meta_ignores_unrelated_meta(reach):
    m = reach.og_meta('<meta name="viewport" content="width=device-width">')
    assert m == {}


def test_og_meta_handles_single_quotes(reach):
    m = reach.og_meta("<meta property='og:title' content='Q'>")
    assert m["og:title"] == "Q"


def test_og_meta_unescapes_entities(reach):
    m = reach.og_meta('<meta property="og:title" content="a &amp; b">')
    assert m["og:title"] == "a & b"


def test_og_summary_joins_title_and_description(reach):
    s = reach.og_summary(reach.og_meta(OG))
    assert "The Title" in s and "A description." in s


def test_og_summary_does_not_repeat_identical_fields(reach):
    m = {"og:title": "Same", "og:description": "Same", "description": "Same"}
    assert reach.og_summary(m) == "Same"


def test_og_summary_respects_max_chars(reach):
    m = {"og:title": "x" * 500}
    assert len(reach.og_summary(m, max_chars=50)) == 50


def test_og_summary_of_nothing_is_empty(reach):
    assert reach.og_summary({}) == ""


# ------------------------------------------------------- block detection


@pytest.mark.parametrize("text", [
    "You've been blocked by network security",
    "JUST A MOMENT...",
    "Verifying your browser before accessing",
    "Please enable JavaScript and cookies to continue",
])
def test_blocked_detects_challenge_pages(reach, text):
    assert reach._blocked(text)


@pytest.mark.parametrize("text", [
    "A normal article about network security practices.",
    "",
    "The moment I saw it, I knew.",
])
def test_blocked_does_not_fire_on_ordinary_prose(reach, text):
    assert not reach._blocked(text)


# ------------------------------------------------------------------ host


@pytest.mark.parametrize("url,want", [
    ("https://example.com/a", "example.com"),
    ("https://sub.example.com:8443/a", "sub.example.com:8443"),
    ("not a url", "not a url"),
])
def test_host_extraction(reach, url, want):
    assert reach._host(url) == want
