"""The YAML front-matter reader in hermes-skills-audit.py.

This parser decides whether a skill is READY. A prerequisite it fails to see is
a skill reported as runnable that dies on first use — and hermes-verify.sh
gates a container rebuild on the READY count, so a parser gap turns into a
green build over a broken install.
"""

import textwrap

import pytest


def fm(audit, text):
    """parse_frontmatter takes a path; write through tmp to exercise the real
    read path including the encoding handling."""
    return audit.parse_frontmatter(text)


@pytest.fixture
def parse(audit, tmp_path):
    def go(body):
        p = tmp_path / "SKILL.md"
        p.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")
        return audit.parse_frontmatter(p)
    return go


def test_reads_scalar_keys(parse):
    data, _ = parse("""
        ---
        name: my-skill
        description: does a thing
        ---
        body
    """)
    assert data["name"] == "my-skill"
    assert data["description"] == "does a thing"


def test_returns_the_body(parse):
    _, body = parse("""
        ---
        name: x
        ---
        the body text
    """)
    assert "the body text" in body


def test_inline_list(parse):
    data, _ = parse("""
        ---
        dependencies: [requests, numpy]
        ---
    """)
    assert data["dependencies"] == ["requests", "numpy"]


def test_block_list(parse):
    """Regression. Block sequences are the ordinary way to write a YAML list;
    they were parsed as an empty mapping, so every prerequisite written this
    way was invisible and the skill was reported READY."""
    data, _ = parse("""
        ---
        dependencies:
          - requests
          - numpy
        ---
    """)
    assert data["dependencies"] == ["requests", "numpy"]


def test_nested_block_list(parse):
    data, _ = parse("""
        ---
        prerequisites:
          commands:
            - ffmpeg
            - pandoc
          env_vars:
            - OPENAI_API_KEY
        ---
    """)
    assert data["prerequisites"]["commands"] == ["ffmpeg", "pandoc"]
    assert data["prerequisites"]["env_vars"] == ["OPENAI_API_KEY"]


def test_nested_inline_list_still_works(parse):
    data, _ = parse("""
        ---
        prerequisites:
          commands: [ffmpeg]
          env_vars: [KEY]
        ---
    """)
    assert data["prerequisites"]["commands"] == ["ffmpeg"]
    assert data["prerequisites"]["env_vars"] == ["KEY"]


def test_block_and_inline_lists_parse_identically(parse):
    """The two spellings mean the same thing in YAML; the audit must not treat
    them differently."""
    inline, _ = parse("""
        ---
        prerequisites:
          commands: [a, b]
        ---
    """)
    block, _ = parse("""
        ---
        prerequisites:
          commands:
            - a
            - b
        ---
    """)
    assert inline["prerequisites"]["commands"] == block["prerequisites"]["commands"]


def test_key_after_a_block_list_is_not_swallowed(parse):
    """The list conversion drops the placeholder mapping; a following key must
    still land on the right parent."""
    data, _ = parse("""
        ---
        prerequisites:
          commands:
            - ffmpeg
        name: after-the-list
        ---
    """)
    assert data["name"] == "after-the-list"
    assert data["prerequisites"]["commands"] == ["ffmpeg"]


def test_quotes_are_stripped(parse):
    data, _ = parse("""
        ---
        name: 'quoted'
        other: "double"
        items:
          - 'a'
          - "b"
        ---
    """)
    assert data["name"] == "quoted"
    assert data["other"] == "double"
    assert data["items"] == ["a", "b"]


def test_comments_and_blank_lines_are_ignored(parse):
    data, _ = parse("""
        ---
        # a comment
        name: x

        # another
        value: y
        ---
    """)
    assert data == {"name": "x", "value": "y"}


def test_no_frontmatter_returns_empty_mapping_and_full_text(parse):
    data, body = parse("""
        # Just a heading

        Some text.
    """)
    assert data == {}
    assert "Just a heading" in body


def test_unterminated_frontmatter_is_not_parsed(parse):
    data, _ = parse("""
        ---
        name: x
    """)
    assert data == {}


def test_horizontal_rule_in_body_does_not_break_parsing(parse):
    """`---` is also a markdown rule; the split has to stop at the closing
    delimiter, not the next rule."""
    data, body = parse("""
        ---
        name: x
        ---
        intro

        ---

        more
    """)
    assert data["name"] == "x"
    assert "more" in body


def test_missing_file_returns_empty(audit, tmp_path):
    data, body = audit.parse_frontmatter(tmp_path / "nope.md")
    assert data == {} and body == ""


def test_invalid_utf8_does_not_raise(audit, tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_bytes(b"---\nname: caf\xff\n---\nbody")
    data, _ = audit.parse_frontmatter(p)
    assert "name" in data


def test_empty_list_value(parse):
    data, _ = parse("""
        ---
        dependencies: []
        ---
    """)
    assert data["dependencies"] == []
