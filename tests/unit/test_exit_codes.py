"""The CLI contract.

reach.py's docstring promises: 0 ok, 3 no content, 4 needs credentials, 5 all
backends failed. Callers (agent-reach-verify.sh, the Hermes reach-social skill,
and any agent shelling out) branch on these, so they are a real interface.
"""

import argparse

import pytest


def run(reach, monkeypatch, result=None, raises=None, argv=None, capsys=None):
    """Drive main() with a stubbed handler so only the exit-code logic runs."""
    argv = argv or ["web", "https://example.com"]

    def fake(a):
        if raises is not None:
            raise raises
        return result

    real_parser = reach.build_parser

    def parser():
        p = real_parser()
        return p

    monkeypatch.setattr(reach, "build_parser", parser)
    parsed = real_parser().parse_args(argv)
    monkeypatch.setattr(reach, "build_parser",
                        lambda: _StubParser(parsed, fake))
    return reach.main(argv)


class _StubParser:
    def __init__(self, parsed, fn):
        parsed.func = fn
        self._parsed = parsed

    def parse_args(self, argv=None):
        return self._parsed


def test_success_returns_zero(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch,
             result={"platform": "web", "content": "hello"})
    assert rc == reach.EXIT_OK


def test_empty_result_returns_three(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch, result={"platform": "web", "content": ""})
    assert rc == reach.EXIT_EMPTY


def test_missing_content_keys_return_three(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch, result={"platform": "web", "title": "t"})
    assert rc == reach.EXIT_EMPTY


@pytest.mark.parametrize("payload", [
    {"platform": "x", "text": "a post"},
    {"platform": "bluesky", "posts": [{"text": "hi"}]},
    {"platform": "hn", "results": [{"title": "t"}]},
])
def test_any_content_key_counts_as_success(reach, monkeypatch, capsys, payload):
    assert run(reach, monkeypatch, result=payload) == reach.EXIT_OK


def test_backend_failure_returns_five(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch,
             raises=reach.ReachError("all web backends failed"))
    assert rc == reach.EXIT_FAILED


def test_login_wall_returns_four(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch,
             raises=reach.ReachError("instagram: page is login-walled"))
    assert rc == reach.EXIT_NEEDS_AUTH


def test_credentials_wording_also_returns_four(reach, monkeypatch, capsys):
    """The auth check was a bare `"login" in msg`, so a handler that said
    "ask the user for credentials" reported "all backends failed" instead."""
    rc = run(reach, monkeypatch,
             raises=reach.ReachError(
                 "Reddit is unreachable — ask the user for Reddit credentials."))
    assert rc == reach.EXIT_NEEDS_AUTH


def test_keyboard_interrupt_returns_130(reach, monkeypatch, capsys):
    assert run(reach, monkeypatch, raises=KeyboardInterrupt()) == 130


def test_unexpected_exception_is_not_a_traceback(reach, monkeypatch, capsys):
    """Upstream payloads change shape without warning; a KeyError from a
    handler must still honour the documented contract rather than dumping a
    stack trace and exiting 1."""
    rc = run(reach, monkeypatch, raises=KeyError("user"))
    assert rc == reach.EXIT_FAILED
    assert "reach:" in capsys.readouterr().err


def test_doctor_all_down_returns_five(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch,
             result={"platform": "doctor", "results": {}, "ok": 0, "total": 3},
             argv=["doctor"])
    assert rc == reach.EXIT_FAILED


def test_doctor_partial_success_returns_zero(reach, monkeypatch, capsys):
    rc = run(reach, monkeypatch,
             result={"platform": "doctor", "results": {}, "ok": 1, "total": 3},
             argv=["doctor"])
    assert rc == reach.EXIT_OK


def test_json_flag_emits_valid_json(reach, monkeypatch, capsys):
    import json
    run(reach, monkeypatch, result={"platform": "web", "content": "hi"},
        argv=["web", "https://example.com", "--json"])
    assert json.loads(capsys.readouterr().out)["content"] == "hi"


# ------------------------------------------------------------ parser wiring


def test_every_subcommand_has_a_handler(reach):
    """A command registered without set_defaults(func=...) crashes on use."""
    parser = reach.build_parser()
    sub = next(a for a in parser._actions
               if isinstance(a, argparse._SubParsersAction))
    for name, p in sub.choices.items():
        ns = p.parse_args(["x"] if name != "doctor" else [])
        assert callable(getattr(ns, "func", None)), f"{name} has no handler"


def test_every_subcommand_accepts_the_shared_options(reach):
    """Handlers read a.n / a.max_chars / a.json unconditionally, so a command
    missing one raises AttributeError only when a user runs it."""
    parser = reach.build_parser()
    sub = next(a for a in parser._actions
               if isinstance(a, argparse._SubParsersAction))
    for name, p in sub.choices.items():
        if name == "doctor":
            continue
        ns = p.parse_args(["target"])
        for attr in ("n", "max_chars", "json"):
            assert hasattr(ns, attr), f"{name} is missing --{attr}"


def test_doctor_probe_names_match_registered_commands(reach):
    """Every probe must name a real platform, or `reach doctor` reports on a
    command nobody can run."""
    parser = reach.build_parser()
    sub = next(a for a in parser._actions
               if isinstance(a, argparse._SubParsersAction))
    known = set(sub.choices) | {"platforms"}
    for name, _ in reach.PROBES:
        assert name in known, f"probe '{name}' is not a registered command"


def test_doctor_covers_every_content_command(reach):
    """A platform added without a probe is invisible to `reach doctor`, which
    is the only end-to-end health signal this tool has."""
    parser = reach.build_parser()
    sub = next(a for a in parser._actions
               if isinstance(a, argparse._SubParsersAction))
    probed = {n for n, _ in reach.PROBES}
    for name in sub.choices:
        if name == "doctor":
            continue
        assert name in probed, f"command '{name}' has no doctor probe"
