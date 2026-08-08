"""Bucketing logic in hermes-skills-audit.py.

The audit answers "can this skill actually run here", which hermes-verify.sh
turns into a pass/fail gate. Its two heuristics — scraping `pip install` lines
out of prose, and classifying what is missing — are exactly the kind of code
that rots silently, because a wrong answer still looks like a report.
"""

import textwrap

import pytest


# ------------------------------------------------- pip packages from prose


@pytest.mark.parametrize("body,want", [
    ("pip install requests", ["requests"]),
    ("pip3 install requests", ["requests"]),
    ("Run `pip install openpyxl` first.", ["openpyxl"]),
    ("pip install --user requests", ["requests"]),
    ("pip install requests numpy pandas", ["requests", "numpy", "pandas"]),
    ("pip install 'requests>=2.0'", ["requests"]),
    ("pip install requests[socks]", ["requests"]),
    ("pip install requests==2.31.0", ["requests"]),
])
def test_extracts_declared_packages(audit, body, want):
    assert audit.body_pip_packages(body) == want


@pytest.mark.parametrize("body", [
    "pip install -r requirements.txt",
    "pip install .",
    "pip install -e .",
    "pip install https://example.com/pkg.whl",
    "pip install ../local/path",
])
def test_ignores_non_package_arguments(audit, body):
    """The regex runs over English prose, so it also sees redirections, paths
    and URLs that follow `pip install` on the same line."""
    assert audit.body_pip_packages(body) == []


def test_deduplicates(audit):
    assert audit.body_pip_packages(
        "pip install requests\nlater: pip install requests") == ["requests"]


def test_no_pip_line_yields_nothing(audit):
    assert audit.body_pip_packages("Just prose about installing things.") == []


def test_empty_body_is_safe(audit):
    assert audit.body_pip_packages("") == []
    assert audit.body_pip_packages(None) == []


# ------------------------------------------------------------- bucketing


@pytest.fixture
def skill(audit, tmp_path, monkeypatch):
    """Write a SKILL.md into a throwaway HERMES_HOME and audit it."""
    skills = tmp_path / "skills"
    monkeypatch.setattr(audit, "SKILLS", skills)
    monkeypatch.setattr(audit, "HERMES_HOME", tmp_path)

    def go(frontmatter, body="", name="demo", category="misc"):
        d = skills / category / name
        d.mkdir(parents=True)
        p = d / "SKILL.md"
        p.write_text("---\n" + textwrap.dedent(frontmatter).strip()
                     + "\n---\n" + body, encoding="utf-8")
        return audit.audit_one(p)
    return go


def test_no_prerequisites_is_ready(audit, skill):
    assert skill("name: demo")["status"] == audit.READY


def test_missing_command_is_needs_bin(audit, skill):
    e = skill("""
        name: demo
        prerequisites:
          commands:
            - definitely-not-a-real-binary-xyz
    """)
    assert e["status"] == audit.NEEDS_BIN
    assert "definitely-not-a-real-binary-xyz" in e["missing_commands"]


def test_assumed_commands_are_not_reported_missing(audit, skill):
    """curl/jq/python are always present; flagging them would bury real gaps."""
    e = skill("""
        name: demo
        prerequisites:
          commands:
            - curl
            - python3
            - reach
    """)
    assert e["missing_commands"] == []


def test_missing_env_is_needs_cred(audit, skill):
    e = skill("""
        name: demo
        prerequisites:
          env_vars:
            - SOME_UNSET_KEY_XYZ
    """)
    assert e["status"] == audit.NEEDS_CRED


def test_credentials_outrank_binaries(audit, skill):
    """A missing key is the user's problem; a missing binary is ours. Report
    the one that blocks the user."""
    e = skill("""
        name: demo
        prerequisites:
          commands:
            - definitely-not-a-real-binary-xyz
          env_vars:
            - SOME_UNSET_KEY_XYZ
    """)
    assert e["status"] == audit.NEEDS_CRED


def test_heavy_ml_stack_is_needs_gpu(audit, skill):
    e = skill("name: demo\ndependencies: [torch]")
    assert e["status"] == audit.NEEDS_GPU


def test_heavy_plus_ordinary_dep_is_needs_bin(audit, skill):
    """Only classify as GPU-blocked when the ML stack is the *only* blocker."""
    e = skill("name: demo\ndependencies: [torch, definitely-not-a-pkg-xyz]")
    assert e["status"] == audit.NEEDS_BIN


def test_wrong_platform_is_incompatible(audit, skill):
    e = skill("name: demo\nplatforms: [macos]")
    assert e["status"] == audit.INCOMPATIBLE


def test_matching_platform_is_evaluated_normally(audit, skill):
    assert skill("name: demo\nplatforms: [linux]")["status"] == audit.READY


def test_platform_match_is_case_insensitive(audit, skill):
    assert skill("name: demo\nplatforms: [Linux]")["status"] == audit.READY


def test_body_pip_packages_feed_the_verdict(audit, skill):
    """Only a handful of skills declare `dependencies`; many just open with
    `pip install X`. Ignoring those reports READY for a skill that dies on its
    first import."""
    e = skill("name: demo", body="Setup:\n\n    pip install definitely-not-a-pkg-xyz\n")
    assert e["status"] == audit.NEEDS_BIN
    assert "definitely-not-a-pkg-xyz" in e["missing_deps"]


def test_name_falls_back_to_the_directory(audit, skill):
    assert skill("description: no name key", name="dirname")["name"] == "dirname"


def test_category_comes_from_the_path(audit, skill):
    assert skill("name: demo", category="social-media")["category"] == "social-media"


# ------------------------------------------------------- credential probe


def test_env_present_reads_the_process_environment(audit, monkeypatch):
    monkeypatch.setenv("SOME_TEST_KEY", "value")
    assert audit.env_present("SOME_TEST_KEY")


def test_env_present_ignores_an_empty_value(audit, monkeypatch):
    monkeypatch.setenv("SOME_TEST_KEY", "")
    assert not audit.env_present("SOME_TEST_KEY")


def test_env_present_finds_a_key_in_the_env_file(audit, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "HERMES_HOME", tmp_path)
    monkeypatch.delenv("SOME_TEST_KEY", raising=False)
    (tmp_path / ".env").write_text("SOME_TEST_KEY=secret-value\n")
    assert audit.env_present("SOME_TEST_KEY")


def test_env_present_rejects_a_key_with_no_value(audit, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "HERMES_HOME", tmp_path)
    monkeypatch.delenv("SOME_TEST_KEY", raising=False)
    (tmp_path / ".env").write_text("SOME_TEST_KEY=\n")
    assert not audit.env_present("SOME_TEST_KEY")


def test_env_present_returns_only_a_boolean(audit, tmp_path, monkeypatch):
    """docs/security.md forbids reading or echoing credential values. The probe
    must answer "is it set" and nothing more — a leak here would end up in the
    audit's JSON output."""
    monkeypatch.setattr(audit, "HERMES_HOME", tmp_path)
    monkeypatch.delenv("SOME_TEST_KEY", raising=False)
    (tmp_path / ".env").write_text("SOME_TEST_KEY=super-secret-value\n")
    result = audit.env_present("SOME_TEST_KEY")
    assert result is True
    assert not isinstance(result, str)


def test_audit_output_never_contains_a_credential_value(audit, skill, tmp_path,
                                                        monkeypatch):
    import json
    (tmp_path / ".env").write_text("SOME_SET_KEY_XYZ=super-secret-value\n")
    e = skill("""
        name: demo
        prerequisites:
          env_vars:
            - SOME_SET_KEY_XYZ
    """)
    assert "super-secret-value" not in json.dumps(e)


def test_missing_env_file_is_not_an_error(audit, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "HERMES_HOME", tmp_path / "nonexistent")
    monkeypatch.delenv("SOME_TEST_KEY", raising=False)
    assert not audit.env_present("SOME_TEST_KEY")
