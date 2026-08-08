"""render() turns a handler's dict into the text a human (or an agent reading
stdout) actually sees. It is the only place the JSON and non-JSON paths differ,
and every platform funnels through it, so a shape it mishandles is a silent
data loss for that platform alone.
"""

import pytest


def test_header_carries_platform_and_title(reach):
    out = reach.render({"platform": "web", "title": "T", "content": "body"})
    assert out.splitlines()[0] == "# web — T"


def test_header_without_a_title(reach):
    assert reach.render({"platform": "x", "content": "c"}).startswith("# x")


def test_metadata_is_labelled(reach):
    out = reach.render({"platform": "x", "backend": "syndication",
                        "author": "alice", "likes": 12, "content": "hi"})
    assert "backend: syndication" in out
    assert "author: alice" in out
    assert "likes: 12" in out


def test_empty_metadata_is_omitted(reach):
    out = reach.render({"platform": "web", "author": None, "url": "",
                        "media": [], "content": "body"})
    assert "author:" not in out
    assert "url:" not in out
    assert "media:" not in out


def test_zero_is_not_treated_as_empty(reach):
    """`likes: 0` is a fact about the post; dropping it because it is falsy
    would misreport an unliked post as one with unknown engagement."""
    out = reach.render({"platform": "x", "likes": 0, "content": "c"})
    assert "likes: 0" in out


def test_content_is_included(reach):
    assert "the body" in reach.render({"platform": "web", "content": "the body"})


def test_text_and_content_both_render(reach):
    out = reach.render({"platform": "x", "text": "T", "content": "C"})
    assert "T" in out and "C" in out


def test_media_list_is_joined(reach):
    out = reach.render({"platform": "x", "media": ["a.png", "b.png"], "content": "c"})
    assert "media: a.png, b.png" in out


def test_string_posts_render_as_bullets(reach):
    """Telegram yields plain strings where the API platforms yield dicts."""
    out = reach.render({"platform": "telegram", "posts": ["one", "two"]})
    assert "- one" in out and "- two" in out


def test_dict_posts_render_author_and_text(reach):
    out = reach.render({"platform": "bluesky", "posts": [
        {"author": "alice", "text": "hello", "created_at": "2026-01-01T00:00:00Z",
         "likes": 3}]})
    assert "@alice" in out and "hello" in out and "3 likes" in out


def test_feed_posts_render_title_and_url(reach):
    out = reach.render({"platform": "rss", "posts": [
        {"title": "Headline", "url": "https://example.com/1",
         "author": "Bob", "created_at": "Sat, 08 Aug 2026 00:11:02 +0000",
         "text": "Body."}]})
    assert "- Headline" in out
    assert "https://example.com/1" in out
    assert "Body." in out


def test_rfc822_dates_are_not_truncated_mid_field(reach):
    """A blanket [:19] slice cut "Sat, 08 Aug 2026 00:11:02 +0000" down to
    "Sat, 08 Aug 2026 00" — a timestamp that reads as corrupt."""
    out = reach.render({"platform": "rss", "posts": [
        {"title": "H", "created_at": "Sat, 08 Aug 2026 00:11:02 +0000"}]})
    assert "00:11:02" in out


def test_iso_dates_are_trimmed_to_seconds(reach):
    out = reach.render({"platform": "bluesky", "posts": [
        {"author": "a", "text": "t", "created_at": "2026-01-01T12:34:56.789Z"}]})
    assert "2026-01-01T12:34:56" in out
    assert ".789" not in out


def test_results_render_title_url_and_stats(reach):
    out = reach.render({"platform": "hn", "results": [
        {"title": "Story", "url": "https://example.com", "points": 42,
         "comments": 7}]})
    assert "- Story" in out
    assert "https://example.com" in out
    assert "points: 42" in out


def test_doctor_renders_nothing_because_it_streams_its_own_output(reach):
    assert reach.render({"platform": "doctor", "results": {}}) == ""


def test_missing_platform_does_not_crash(reach):
    assert reach.render({"content": "x"}).startswith("# ?")


@pytest.mark.parametrize("payload", [
    {},
    {"platform": "web"},
    {"platform": "web", "posts": None},
    {"platform": "web", "results": None},
    {"platform": "web", "posts": [], "results": []},
])
def test_degenerate_payloads_render_without_raising(reach, payload):
    reach.render(payload)


def test_output_has_no_trailing_whitespace(reach):
    out = reach.render({"platform": "web", "content": "body\n\n"})
    assert out == out.strip()


def test_metadata_order_is_stable(reach):
    """Output is diffed between runs (doctor reports, verify scripts), so key
    order must not depend on dict iteration."""
    payload = {"platform": "x", "backend": "b", "url": "u", "author": "a",
               "created_at": "c", "likes": 1, "content": "z"}
    assert reach.render(payload) == reach.render(dict(reversed(list(payload.items()))))
