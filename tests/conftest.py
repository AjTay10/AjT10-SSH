"""Shared test fixtures.

`scripts/` is a directory of executable tools, not a package: there is no
`__init__.py`, and `hermes-skills-audit.py` is not a legal module name. Both are
loaded by path so the suite runs against the real files with no restructuring
and no install step.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def reach():
    return _load(SCRIPTS / "reach.py", "reach_under_test")


@pytest.fixture(scope="session")
def audit():
    return _load(SCRIPTS / "hermes-skills-audit.py", "hermes_skills_audit_under_test")


@pytest.fixture
def args():
    """Build the argparse.Namespace the cmd_* handlers expect.

    They read attributes directly, so a handler that grows a new option without
    a matching parser default will fail here the same way it fails in the CLI.
    """
    def make(target=None, **kw):
        kw.setdefault("n", 5)
        kw.setdefault("max_chars", 8000)
        kw.setdefault("json", False)
        return argparse.Namespace(target=target, **kw)
    return make


@pytest.fixture
def fixture_bytes():
    def read(name):
        return (FIXTURES / name).read_bytes()
    return read


@pytest.fixture
def fixture_json():
    def read(name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return read


@pytest.fixture
def no_network(monkeypatch, reach):
    """Fail loudly if a test reaches the network.

    Every test in this suite is meant to be offline and deterministic. Without
    this guard a stubbing mistake turns into a test that silently depends on
    the internet and fails in CI for reasons unrelated to the change.
    """
    def boom(*a, **kw):
        raise AssertionError("test attempted a real network call")

    monkeypatch.setattr(reach, "http", boom)
    monkeypatch.setattr(reach, "get_json", boom)
    monkeypatch.setattr(reach, "exa_call", boom)
    return boom
