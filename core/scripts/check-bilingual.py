#!/usr/bin/env python3
"""Bilingual completeness gate (local replacement for the removed CI job).

Every human-facing document ships in both languages: ``X.md`` and ``X.en.md``.
The rule used to be enforced by a CI job; CI is gone, so it is enforced here
and wired into ``make test``.

Scope (tracked Markdown files only):

* every ``X.md`` must have ``X.en.md`` and vice versa;
* ``docs/provenance/`` is exempt by design (verbatim design-session records,
  Chinese only, documented as the bilingual exception);
* ``golden-tests/`` is exempt because it holds compiled/generate artifacts
  (``*.soul.md`` baselines), not documents.

Exit 0 = complete; 1 = at least one missing twin (all reported).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXEMPT_PREFIXES = (
    "docs/provenance/",
    "golden-tests/",
)


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        print('{"ok": false, "problems": ["git ls-files failed; run inside the repository"]}')
        raise SystemExit(1)
    return [Path(line) for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    paths = tracked_markdown()
    chinese = [p for p in paths if not p.name.endswith(".en.md")]
    english = {str(p) for p in paths if p.name.endswith(".en.md")}
    base_names = {str(p) for p in chinese}

    problems: list[str] = []
    checked = 0
    for path in chinese:
        if str(path).startswith(EXEMPT_PREFIXES):
            continue
        checked += 1
        twin = path.with_name(path.stem + ".en.md")
        if str(twin) not in english:
            problems.append(f"{path}: missing English twin {twin.name}")

    for path in sorted(english):
        if path.startswith(EXEMPT_PREFIXES):
            continue
        twin = Path(path).with_name(Path(path).name[: -len(".en.md")] + ".md")
        if str(twin) not in base_names:
            problems.append(f"{path}: English twin without a Chinese source ({twin.name})")

    if problems:
        print('{"ok": false, "problems": [' + ", ".join(repr(p) for p in problems) + "]}")
        return 1
    print(f'{{"ok": true, "pairs": {checked}}}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
