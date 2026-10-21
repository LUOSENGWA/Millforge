#!/usr/bin/env python3
"""Unit + end-to-end tests for the context-tier resident-token gate (12-REDLINES §5.2)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("millforge_compile", ROOT / "compiler" / "millforge-compile.py")
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)  # type: ignore[union-attr]

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}: {detail}")


# 1) token estimation: CJK ≈1 token/char, ASCII ≈1/4 token/char
check("cjk_estimate", mf.estimate_tokens("中" * 1000) == 1000)
check("ascii_estimate", mf.estimate_tokens("a" * 400) == 100)
check("tier_caps", mf.TIER_CAPS == {"S": 8000, "M": 10000, "L": 12000})

# 2) tier_exceeded helper
exceeded, est, cap = mf.tier_exceeded("S", "中" * 9000)
check("s_exceeded", exceeded and est == 9000 and cap == 8000)
check("m_not_exceeded", not mf.tier_exceeded("M", "中" * 9000)[0])
check("no_tier_never_exceeds", not mf.tier_exceeded(None, "中" * 9000)[0])

# 3) end-to-end: patched S cap → compile fails with EXIT_BUDGET (4); restored cap → ok
fixture = json.loads((ROOT / "golden-tests" / "fixtures" / "example-biz-team.json").read_text(encoding="utf-8"))
doc = dict(fixture)
doc["context_tier"] = "S"
old_cap = mf.TIER_CAPS["S"]
try:
    mf.TIER_CAPS["S"] = 100
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                mf.compile_team(dict(doc), tmp)
            check("e2e_fail", False, "compile did not fail with a patched S cap")
        except SystemExit as exc:
            check("e2e_fail_code", exc.code == 4, f"exit code {exc.code}")
finally:
    mf.TIER_CAPS["S"] = old_cap

with tempfile.TemporaryDirectory() as tmp:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = mf.compile_team(dict(doc), tmp)
    check("e2e_ok", rc == 0)

# 4) normal fixture without tier still compiles
with tempfile.TemporaryDirectory() as tmp:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = mf.compile_team(dict(fixture), tmp)
    check("e2e_no_tier_ok", rc == 0)

if failures:
    print(json.dumps({"ok": False, "failures": failures}, ensure_ascii=False, indent=1))
    sys.exit(1)
print(json.dumps({"ok": True, "tests": 10}, ensure_ascii=False))
