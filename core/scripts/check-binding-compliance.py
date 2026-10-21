#!/usr/bin/env python3
"""Validate binding compliance declarations (`bindings/<name>/compliance.json`).

Checks:
  * every binding directory has compliance.json;
  * 8 CAP-* keys, levels in {full, partial, declared-degraded};
  * X1/X4 hard gates declared as pass/not-enforced;
  * every non-full capability has a gap entry with matching scope;
  * every gap references a real capability or hard gate;
  * `compliant` equals "all capabilities full AND X1/X4 pass";
  * the binding READMEs contain the Capability Declaration table.

Exit 0 = all good, 1 = violations.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BINDINGS = ROOT / "bindings"
CAPS = ["CAP-STATE", "CAP-STORE", "CAP-TIMER", "CAP-NOTIFY", "CAP-ATTN", "CAP-SPAWN", "CAP-EXEC", "CAP-ROSTER"]
LEVELS = {"full", "partial", "declared-degraded"}
STATUSES = {"compliant", "reference"}
HARD_VALUES = {"pass", "not-enforced"}


def main() -> int:
    problems: list[str] = []
    seen: list[str] = []
    for d in sorted(p for p in BINDINGS.iterdir() if p.is_dir()):
        f = d / "compliance.json"
        if not f.exists():
            problems.append(f"{d.name}: missing compliance.json")
            continue
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{d.name}: invalid json: {exc}")
            continue
        seen.append(d.name)
        for key in ("binding", "status", "compliant", "capabilities", "hard_gates", "gaps"):
            if key not in c:
                problems.append(f"{d.name}: missing key {key}")
        if c.get("binding") != d.name:
            problems.append(f"{d.name}: binding field {c.get('binding')!r} != directory name")
        if c.get("status") not in STATUSES:
            problems.append(f"{d.name}: bad status {c.get('status')!r}")
        caps = c.get("capabilities", {})
        if set(caps) != set(CAPS):
            missing = sorted(set(CAPS) - set(caps))
            extra = sorted(set(caps) - set(CAPS))
            problems.append(f"{d.name}: capability keys mismatch (missing={missing}, extra={extra})")
        for cap, level in caps.items():
            if level not in LEVELS:
                problems.append(f"{d.name}: {cap} has bad level {level!r}")
        hard = c.get("hard_gates", {})
        for gate in ("X1", "X4"):
            if hard.get(gate) not in HARD_VALUES:
                problems.append(f"{d.name}: hard gate {gate} has bad value {hard.get(gate)!r}")
        gaps = c.get("gaps", [])
        for cap, level in caps.items():
            if level != "full" and not any(g.get("scope") == cap for g in gaps):
                problems.append(f"{d.name}: {cap} is {level} but has no gap entry")
        for g in gaps:
            scope = g.get("scope")
            if scope == "hard-gate":
                if g.get("id") not in hard:
                    problems.append(f"{d.name}: hard-gate gap {g.get('id')} not present in hard_gates")
            elif scope not in caps:
                problems.append(f"{d.name}: gap {g.get('id')} has unknown scope {scope!r}")
        all_full = all(v == "full" for v in caps.values()) and all(hard.get(g) == "pass" for g in ("X1", "X4"))
        if bool(c.get("compliant")) != all_full:
            problems.append(f"{d.name}: compliant={c.get('compliant')} but the declaration implies {all_full}")
        for readme, label in ((d / "README.md", "README.md"), (d / "README.en.md", "README.en.md")):
            if not readme.exists():
                continue
            text = readme.read_text(encoding="utf-8")
            if "能力声明（CAP-*）" not in text and "Capability Declaration (CAP-*)" not in text:
                problems.append(f"{d.name}/{label}: missing capability declaration section")
            for cap in CAPS:
                if cap not in text:
                    problems.append(f"{d.name}/{label}: missing {cap}")
    if not seen:
        problems.append("no compliance.json found under bindings/")
    print(json.dumps({"ok": not problems, "bindings": seen, "problems": problems}, ensure_ascii=False, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
