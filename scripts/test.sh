#!/usr/bin/env bash
#
# Run the offline test suite: Python unit + contract tests, then the shell
# script logic tests.
#
# Everything here is deterministic and needs no network. The live checks live
# in agent-reach-verify.sh / hermes-verify.sh and are deliberately NOT run
# from here — mixing them would mean a failing test could mean "a website is
# down" instead of "this commit is broken".
#
#   ./scripts/test.sh            # everything
#   ./scripts/test.sh -k feed    # pass extra args through to pytest
#
# Exit codes: 0 all passed, 1 a test failed, 2 pytest is not installed.

set -uo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR" || exit 2

PY="${PYTHON:-python3}"
if ! "$PY" -c "import pytest" 2>/dev/null; then
  echo "pytest is not installed for $PY — install it with:" >&2
  echo "  $PY -m pip install pytest beautifulsoup4" >&2
  exit 2
fi

rc=0

printf '\n== python (unit + contract)\n'
"$PY" -m pytest "$@" || rc=1

printf '\n== shell\n'
./tests/bash/run.sh || rc=1

printf '\n'
if [ "$rc" -eq 0 ]; then
  echo "all offline tests passed"
else
  echo "FAILURES — see above" >&2
fi
exit "$rc"
