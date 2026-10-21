#!/usr/bin/env python3
"""Validate [E#] evidence references against docs/EVIDENCE.md (and the EN twin).

Exit 0 = every referenced evidence ID is registered and every internal-observation
row carries the "not externally verifiable" label. Exit 1 = violations.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EV_ZH = ROOT / "docs" / "EVIDENCE.md"
EV_EN = ROOT / "docs" / "EVIDENCE.en.md"


def registered_ids(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"\|\s*\*\*(E\d+)\*\*\s*\|", text))


def referenced_ids() -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    roots = [ROOT / "core", ROOT / "docs", ROOT / "bindings"]
    files = [p for r in roots for p in r.rglob("*.md")]
    files.append(ROOT / "README.md")
    for p in files:
        if p.name in ("EVIDENCE.md", "EVIDENCE.en.md"):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\[(E\d+)\]", text):
            refs.setdefault(m.group(1), []).append(str(p.relative_to(ROOT)))
    return refs


def main() -> int:
    ids = registered_ids(EV_ZH) | registered_ids(EV_EN)
    refs = referenced_ids()
    missing = {k: v for k, v in refs.items() if k not in ids}
    problems: list[str] = []
    for path in (EV_ZH, EV_EN):
        if not path.exists():
            problems.append(f"missing evidence file: {path}")
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "internal-observation" in line and ("不可外部验证" not in line and "not externally verifiable" not in line):
                problems.append(f"internal row without label in {path.name}: {line[:80]}")
    ok = not missing and not problems
    print(json.dumps({
        "ok": ok,
        "registered": sorted(ids),
        "referenced": sorted(refs),
        "missing": missing,
        "problems": problems,
    }, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
