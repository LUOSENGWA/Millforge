#!/usr/bin/env python3
"""millforge core script: consistency-check.py
C-3 locked_spec_consistency_check —— 最关键的"规则 vs LLM"分界点

加权多数可"程序合法"推翻人锁 spec（第六轮 C-3 定案漏洞）：
R6 回答写回前强制本检查。机器可判的二元矛盾 → 拒收 → spec_conflict 升级链。
规则层判不了的 → LLM 受限分类 spawn（输出 schema 固定）→ neutral 按 undecidable 升级 human，不自动放行。

输入: --r6-response <path> --locked-criteria <path>
      [--mode auto|strict|llm-fallback] [--llm-result <受限分类 spawn 结果 path>] [--dry-run]
输出: stdout JSON {result: consistent|contradict|undecidable, criterion_id, method: rule|llm,
                   confidence, llm_ref, checked[], unstructured[]}
退出码: 0=consistent; 70=contradict（拒收）; 71=undecidable（升级 human，不自动放行）; 72=输入不可读
幂等性: 规则层幂等；LLM fallback 以输入哈希为幂等键（--llm-result 内须带 input_hash 匹配）
日志: $HOME/.millforge/logs/consistency-check.jsonl

locked-criteria schema:
  [{"criterion_id","description","structured": {"field","allowed_values":[...],"forbidden_values":[...]} | null}]
r6-response schema:
  {"text": "...", "structured": {"<field>": <value>, ...} | null}
  非结构化（无 structured 字段）→ 直接 undecidable，不强行规则判定
llm-result schema（受限分类 spawn 的固定输出）:
  {"input_hash","contradict": bool, "criterion_id","reason": "≤50字"}
  contradict=false 且无法判定（neutral）→ 按 undecidable 处理
"""
import hashlib
import json
import os
import sys

LOG = os.path.join(os.environ.get("HOME", "/root"), ".millforge/logs/consistency-check.jsonl")


def log_line(summary):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    except Exception:
        pass


def die(code, payload):
    print(json.dumps(payload, ensure_ascii=False))
    log_line({"exit": code, "summary": payload.get("error") or ""})
    sys.exit(code)


def norm(v):
    if isinstance(v, str):
        return " ".join(v.split()).lower()
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in sorted(v.items())}
    return v


def input_hash(r6_path, crit_path):
    h = hashlib.sha256()
    for p in (r6_path, crit_path):
        with open(p, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def rule_check(crit, r6_structured):
    """规则层：仅当 criterion 有结构化字段且 R6 回答有同名字段时机械判定。
    返回 (verdict, detail): verdict in consistent|contradict|undecidable"""
    s = crit.get("structured")
    if not isinstance(s, dict):
        return "undecidable", "criterion not structured"
    field = s.get("field")
    if not field or not isinstance(r6_structured, dict) or field not in r6_structured:
        return "undecidable", f"field {field!r} not touched by r6 response"
    val = norm(r6_structured[field])
    forbidden = [norm(x) for x in s.get("forbidden_values", [])]
    allowed = [norm(x) for x in s.get("allowed_values", [])]
    if any(val == f for f in forbidden):
        return "contradict", f"value {val!r} in forbidden_values"
    if allowed and not any(val == a for a in allowed):
        return "contradict", f"value {val!r} deviates from allowed_values {allowed}"
    if allowed:
        return "consistent", f"value {val!r} within allowed_values"
    return "undecidable", "no allowed_values constraint to check"


def main():
    args = sys.argv[1:]
    opts = {}
    mode = "auto"
    dry_run = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dry-run":
            dry_run = True
        elif a in ("--r6-response", "--locked-criteria", "--llm-result"):
            opts[a] = args[i + 1]
            i += 1
        elif a == "--mode":
            mode = args[i + 1]
            i += 1
        else:
            die(72, {"error": f"unknown arg: {a}"})
        i += 1

    if "--r6-response" not in opts or "--locked-criteria" not in opts or mode not in ("auto", "strict", "llm-fallback"):
        die(72, {"error": "usage: consistency-check.py --r6-response <p> --locked-criteria <p> [--mode auto|strict|llm-fallback] [--llm-result <p>] [--dry-run]"})

    try:
        with open(opts["--r6-response"], encoding="utf-8") as f:
            r6 = json.load(f)
        with open(opts["--locked-criteria"], encoding="utf-8") as f:
            criteria = json.load(f)
        if not isinstance(criteria, list) or not criteria:
            die(72, {"error": "locked-criteria must be a non-empty list"})
    except Exception as e:
        die(72, {"error": f"input unreadable: {e}"})

    r6_structured = r6.get("structured") if isinstance(r6, dict) else None
    is_structured = isinstance(r6_structured, dict) and r6_structured
    ih = input_hash(opts["--r6-response"], opts["--locked-criteria"])

    checked = []
    unstructured = []
    contradiction = None

    if not is_structured:
        # 非结构化回答 → 规则层直接 undecidable（不强行判定）
        unstructured = [c.get("criterion_id") for c in criteria]
        result, method, llm_ref = "undecidable", "rule", None
        if mode in ("auto", "llm-fallback") and "--llm-result" in opts:
            result, method, llm_ref, _detail = llm_fallback(opts["--llm-result"], ih)
        die(71 if result == "undecidable" else (70 if result == "contradict" else 0), {
            "result": result, "criterion_id": None, "method": method, "confidence": "rule" if method == "rule" else "limited-llm",
            "llm_ref": llm_ref, "checked": checked, "unstructured": unstructured,
            "reason": "r6 response not structured -> rule layer cannot judge" + ("" if method == "llm" else " (llm-fallback not provided/allowed)")})

    for c in criteria:
        cid = c.get("criterion_id")
        verdict, detail = rule_check(c, r6_structured)
        checked.append({"criterion_id": cid, "verdict": verdict, "detail": detail})
        if verdict == "contradict" and contradiction is None:
            contradiction = {"criterion_id": cid, "detail": detail}

    if contradiction:
        die(70, {"result": "contradict", "criterion_id": contradiction["criterion_id"],
                 "method": "rule", "confidence": "deterministic", "llm_ref": None,
                 "checked": checked, "unstructured": [],
                 "reason": f"{contradiction['detail']} -> 拒收，spec_conflict 升级链（C-3）"})

    undecided = [c for c in checked if c["verdict"] == "undecidable"]
    if not undecided:
        die(0, {"result": "consistent", "criterion_id": None, "method": "rule",
                "confidence": "deterministic", "llm_ref": None, "checked": checked,
                "unstructured": [], "reason": "all criteria rule-checked consistent"})

    # 有 undecidable → LLM 受限 fallback（mode 允许时）
    if mode in ("auto", "llm-fallback") and "--llm-result" in opts:
        result, method, llm_ref, detail = llm_fallback(opts["--llm-result"], ih, undecided)
        code = 70 if result == "contradict" else (0 if result == "consistent" else 71)
        die(code, {"result": result, "criterion_id": (llm_ref or {}).get("criterion_id"), "method": method,
                   "confidence": "limited-llm", "llm_ref": llm_ref, "checked": checked,
                   "unstructured": [u["criterion_id"] for u in undecided], "reason": detail})

    # strict 或无 llm-result → undecidable 升级 human
    die(71, {"result": "undecidable", "criterion_id": undecided[0]["criterion_id"], "method": "rule",
             "confidence": "deterministic", "llm_ref": None, "checked": checked,
             "unstructured": [u["criterion_id"] for u in undecided],
             "reason": "rule layer undecidable; no LLM fallback (mode=strict or --llm-result absent) -> 升级 human，不自动放行"})


def llm_fallback(path, ih, undecided=None):
    """受限分类 spawn 结果。固定 schema {input_hash, contradict, criterion_id, reason≤50}。
    返回 (result, method, llm_ref)。hash 不匹配 = 结果不可信 → undecidable。
    neutral（contradict=false 且无明确 consistent 语义）→ undecidable。"""
    try:
        with open(path, encoding="utf-8") as f:
            lr = json.load(f)
        if lr.get("input_hash") != ih:
            return "undecidable", "llm", lr, "input_hash mismatch -> LLM result stale, treat as undecidable"
        reason = str(lr.get("reason", ""))[:50]
        if lr.get("contradict") is True:
            return "contradict", "llm", lr, f"limited-llm contradiction: {reason}"
        # contradict=false：受限 spawn 的 schema 没有 consistent 值 → neutral 语义
        return "undecidable", "llm", lr, f"limited-llm neutral: {reason} -> undecidable, 升级 human"
    except Exception as e:
        return "undecidable", "llm", None, f"llm-result unreadable: {e}"


if __name__ == "__main__":
    main()
