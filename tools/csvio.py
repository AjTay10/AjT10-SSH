#!/usr/bin/env python3
"""csvio — one honest CSV reader shared by every tool here.

Real platform exports are not clean UTF-8. Excel on Windows writes cp1252,
older exports write latin-1, and almost everything carries a BOM. A tool that
raises UnicodeDecodeError on those is a tool that fails on the exact files it
exists to read — and because UnicodeDecodeError subclasses ValueError rather
than OSError, it slips past the usual `except OSError` and reaches the user as
a traceback.

This reads utf-8 first, falls back through the common single-byte encodings,
and says on stderr which one it used so a mojibake result is explainable
rather than mysterious.

Also warns about duplicate header names: csv.DictReader silently keeps only
the last column of a repeated name, which means a tool can read the wrong
column and produce confident nonsense.
"""

from __future__ import annotations

import csv
import io
import sys

# utf-8-sig first: it strips a BOM when present and is identical to utf-8
# otherwise. cp1252 before latin-1 because it is a superset for the byte
# range that actually differs (smart quotes, dashes, euro sign).
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


class CsvError(ValueError):
    """Raised when a file cannot be read as CSV at all."""


def read_rows(path, quiet=False):
    """Return a list of dicts. Accepts '-' for stdin.

    Raises CsvError with an actionable message rather than letting a decode
    or parse failure escape as something the caller cannot explain.
    """
    if path == "-":
        data = sys.stdin.buffer.read()
        origin = "stdin"
    else:
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as e:
            raise CsvError(f"{path}: {e.strerror or e}")
        origin = path

    if not data.strip():
        raise CsvError(f"{origin}: file is empty")

    # latin-1 decodes literally any byte sequence, so without this check a
    # binary file becomes "valid text" and the error surfaces later as a
    # column-not-found listing full of mojibake.
    if b"\x00" in data[:8192]:
        raise CsvError(
            f"{origin}: contains NUL bytes — this is a binary file, not CSV. "
            f"If it is a spreadsheet, export it as CSV first.")

    text, used = None, None
    for enc in ENCODINGS:
        try:
            text = data.decode(enc)
            used = enc
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise CsvError(
            f"{origin}: not readable as text in any of "
            f"{', '.join(ENCODINGS)}. If this is a spreadsheet, export it as "
            f"CSV UTF-8 rather than renaming the file.")

    if used != "utf-8-sig" and not quiet:
        print(f"note: {origin} is not UTF-8; read it as {used}. Check any "
              f"accented characters in the output.", file=sys.stderr)

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        rows = list(reader)
    except csv.Error as e:
        raise CsvError(f"{origin}: malformed CSV ({e})")

    if not rows:
        raise CsvError(f"{origin}: no data rows (header only?)")

    headers = [h for h in (reader.fieldnames or []) if h is not None]
    if not headers:
        raise CsvError(f"{origin}: no header row")

    dupes = sorted({h for h in headers if headers.count(h) > 1})
    if dupes and not quiet:
        print(f"note: {origin} has duplicate column name(s): "
              f"{', '.join(dupes)}. Only the last of each is readable, so a "
              f"lookup may silently return the wrong column.", file=sys.stderr)

    return rows


def require(rows, *cols, origin="input"):
    """Fail with the list of columns that do exist — the message people need."""
    have = set(rows[0].keys())
    missing = [c for c in cols if c and c not in have]
    if not missing:
        return

    # Keep the "Present:" list readable. A mis-parsed file can produce hundreds
    # of junk headers, and a screenful of garbage buries the actual message.
    names = []
    for h in sorted(str(x) for x in have):
        clean = "".join(ch if ch.isprintable() else "?" for ch in h)
        names.append(clean[:40] + ("…" if len(clean) > 40 else ""))
    shown = ", ".join(names[:12])
    if len(names) > 12:
        shown += f", … ({len(names) - 12} more)"

    raise CsvError(f"{origin}: missing column(s) {', '.join(missing)}. "
                   f"Present: {shown}")
