#!/usr/bin/env python3
"""millforge core script: detect-conflict.py
B-2 Step 1-3 冲突检测纯函数（确定性，零 LLM）

输入: <decision_a.json> <decision_b.json> [--type-registry <path>] [--dry-run]
输出: stdout JSON {candidates[]: {artifact, entry_a_id, entry_b_id, conflict_type, confidence: "deterministic"}}
退出码: 0=无候选冲突; 20=发现 hard-conflict; 21=发现 assumption-conflict; 22=仅 shared-surface（需 Step 4 语义确认）
幂等性: 纯函数，同输入同输出（dry-run 与正式执行输出一致，均无副作用）
日志: $HOME/.millforge/logs/detect-conflict.jsonl
前置检查: 两份文件均须先过 validate-decision-log.sh（本脚本不重复校验，但解析失败按 12 报）
调用链: B-1 第 1 层通过 → 本脚本 → (20/21 直接拒 merge; 22 → 专用 merge spawn Step 4 → 父执行体只读 Step 5)

type_registry (C-1 封闭枚举): {"<type>": {"dimension": "<语义维度名>"}, ...}
  同一 artifact 被两个不同 dimension 的 type 触碰 = type_dimension_mismatch = hard-conflict
"""
import json
import os
import sys

LOG = os.path.join(os.environ.get("HOME", "/root"), ".millforge/logs/detect-conflict.jsonl")


def log_line(summary):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    except Exception:
        pass


def norm(v):
    """规范化值比较：字符串去空白小写；容器递归规范化。"""
    if isinstance(v, str):
        return " ".join(v.split()).lower()
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in sorted(v.items())}
    return v


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    type_registry_path = None
    if "--type-registry" in args:
        i = args.index("--type-registry")
        type_registry_path = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        print(json.dumps({"candidates": [], "error": "usage: detect-conflict.py <a.json> <b.json> [--type-registry p] [--dry-run]"}))
        log_line({"error": "usage", "exit": 12})
        sys.exit(12)

    registry = {}
    if type_registry_path:
        try:
            with open(type_registry_path, encoding="utf-8") as f:
                registry = json.load(f)
        except Exception as e:
            print(json.dumps({"candidates": [], "error": f"type-registry unreadable: {e}"}))
            log_line({"error": "registry", "exit": 12})
            sys.exit(12)

    candidates = []
    try:
        docs = []
        for p in args:
            with open(p, encoding="utf-8") as f:
                docs.append(json.load(f))
    except Exception as e:
        print(json.dumps({"candidates": [], "error": f"parse failure: {e}"}))
        log_line({"error": "parse", "exit": 12})
        sys.exit(12)

    A, B = docs
    entries_a = {e["id"]: e for e in A.get("entries", []) if isinstance(e, dict) and e.get("id")}
    entries_b = {e["id"]: e for e in B.get("entries", []) if isinstance(e, dict) and e.get("id")}

    def dim(t):
        if not t:
            return None
        entry = registry.get(t)
        if not isinstance(entry, dict):
            return f"<unregistered:{t}>"
        return entry.get("dimension")

    for eid_a, ea in sorted(entries_a.items()):
        arts_a = sorted(set(ea.get("affected_artifacts") or []))
        for eid_b, eb in sorted(entries_b.items()):
            arts_b = sorted(set(eb.get("affected_artifacts") or []))
            shared = sorted(set(arts_a) & set(arts_b))
            if not shared:
                continue
            # --- hard: 同 artifact 同 field 值不同 ---
            fa = (ea.get("field") or None)
            fb = (eb.get("field") or None)
            hard = False
            if fa and fb and fa == fb and "value" in ea and "value" in eb:
                if norm(ea["value"]) != norm(eb["value"]):
                    hard = True
            # --- hard: 封闭枚举 dimension 冲突 (C-1) ---
            da, db = dim(ea.get("type")), dim(eb.get("type"))
            if da and db and da != db and not da.startswith("<unregistered") and not db.startswith("<unregistered"):
                hard = True
            # --- assumption: 同 key 布尔值相反 ---
            assum = False
            amap_a = {a.get("key"): a.get("holds") for a in (ea.get("assumptions") or []) if isinstance(a, dict)}
            amap_b = {a.get("key"): a.get("holds") for a in (eb.get("assumptions") or []) if isinstance(a, dict)}
            for k in set(amap_a) & set(amap_b):
                if amap_a[k] is not None and amap_b[k] is not None and amap_a[k] != amap_b[k]:
                    assum = True
                    break
            for art in shared:
                if hard:
                    candidates.append({"artifact": art, "entry_a_id": eid_a, "entry_b_id": eid_b,
                                       "conflict_type": "hard-conflict", "confidence": "deterministic"})
                elif assum:
                    candidates.append({"artifact": art, "entry_a_id": eid_a, "entry_b_id": eid_b,
                                       "conflict_type": "assumption-conflict", "confidence": "deterministic"})
                else:
                    candidates.append({"artifact": art, "entry_a_id": eid_a, "entry_b_id": eid_b,
                                       "conflict_type": "shared-surface", "confidence": "deterministic"})

    # 去重（同 artifact+entry 对只保留最高严重级）
    rank = {"hard-conflict": 0, "assumption-conflict": 1, "shared-surface": 2}
    best = {}
    for c in candidates:
        key = (c["artifact"], c["entry_a_id"], c["entry_b_id"])
        if key not in best or rank[c["conflict_type"]] < rank[best[key]["conflict_type"]]:
            best[key] = c
    out = sorted(best.values(), key=lambda c: (rank[c["conflict_type"]], c["artifact"], c["entry_a_id"], c["entry_b_id"]))

    types_present = {c["conflict_type"] for c in out}
    if "hard-conflict" in types_present:
        code = 20
    elif "assumption-conflict" in types_present:
        code = 21
    elif out:
        code = 22
    else:
        code = 0

    print(json.dumps({"candidates": out}, ensure_ascii=False, indent=1))
    log_line({"candidates": len(out), "types": sorted(types_present), "exit": code, "dry_run": dry_run})
    sys.exit(code)


if __name__ == "__main__":
    main()
