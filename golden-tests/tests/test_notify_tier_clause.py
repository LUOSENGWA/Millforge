#!/usr/bin/env python3
"""M5 static clause check: the CAP-NOTIFY tiering clause (09-GOVERNANCE §8).

Asserts that the normative clause exists in both the zh and en twins, and that
every normative element is present — in particular that FAILURE STATES must
enter the human tier (no silent failure). Deterministic; text-only.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC_ZH = ROOT / "core" / "protocol" / "09-GOVERNANCE.md"
DOC_EN = ROOT / "core" / "protocol" / "09-GOVERNANCE.en.md"

failures: list[str] = []
N_CHECKS = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global N_CHECKS
    N_CHECKS += 1
    if not cond:
        failures.append(f"{name}: {detail}")


def has(text: str, *markers: str) -> bool:
    return all(m in text for m in markers)


zh = DOC_ZH.read_text(encoding="utf-8") if DOC_ZH.exists() else ""
en = DOC_EN.read_text(encoding="utf-8") if DOC_EN.exists() else ""

# section exists in both twins
check("zh_section8", "## 8." in zh, "09-GOVERNANCE.md missing section 8")
check("en_section8", "## 8." in en, "09-GOVERNANCE.en.md missing section 8")

# 8.1 tier declaration: exactly one of machine / agent / human
check("zh_tiers", has(zh, "machine", "agent", "human"),
      "zh must declare the three tiers (machine/agent/human)")
check("en_tiers", has(en, "machine", "agent", "human"),
      "en must declare the three tiers (machine/agent/human)")
check("zh_no_default_tier", "未声明 tier = 违反" in zh,
      "zh must forbid undeclared tiers (no default-tier fallback)")
check("en_no_default_tier", "No tier declared = violation" in en,
      "en must forbid undeclared tiers (no default-tier fallback)")

# 8.2 human tier: fixed 3 lines, plain language, hard constraint
check("zh_3line", "固定 3 行" in zh, "zh human tier must be fixed 3 lines")
check("en_3line", "Fixed 3 lines" in en, "en human tier must be fixed 3 lines")
check("zh_plain", "人话无术语" in zh, "zh human tier must be plain language, no jargon")
check("en_plain", "Plain language, no jargon" in en,
      "en human tier must be plain language, no jargon")

# 8.3 failure states must enter the human tier (the load-bearing clause)
check("zh_failure_human", "失败态必须进 human tier" in zh,
      "zh must mandate failure states in the human tier")
check("en_failure_human", "Failure states must enter the human tier" in en,
      "en must mandate failure states in the human tier")
check("zh_no_silent", "人看见失败" in zh, "zh must define no-silent = human sees failure")
check("en_no_silent", "a human sees the failure" in en,
      "en must define no-silent = human sees failure")

# 8.4 prohibitions: no payload, no question-form
check("zh_no_payload", "禁止 payload 化" in zh, "zh must forbid payload inlining")
check("en_no_payload", "No payload" in en, "en must forbid payload inlining")
check("zh_no_questions", "禁止提问式通知" in zh, "zh must forbid question-form notifications")
check("en_no_questions", "No question-form notifications" in en,
      "en must forbid question-form notifications")

if failures:
    print(json.dumps({"ok": False, "checks": N_CHECKS, "failures": failures},
                     ensure_ascii=False, indent=1))
    sys.exit(1)
print(json.dumps({"ok": True, "checks": N_CHECKS}, ensure_ascii=False))
