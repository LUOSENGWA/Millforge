#!/usr/bin/env python3
"""millforge migration scaffold — 从存量角色目录反向生成 team.json 骨架（B-7 阶段 1）

零网络、零 LLM、确定性：同输入 → 同输出。
用法:
  python3 migration/scaffold-team.py --from <roles_dir> --name my-team \
      --mode multi_user --lang zh --out team.json

边界:
  - 只读 *.soul.md 文件名 + 首段身份行；不改任何存量文件
  - 不可推断项（charter 目标 / 人类成员 / 权重 / 决策类别）一律写 TODO，**不猜**
"""
import argparse
import json
import os
import re
import sys

BUDGET_DEFAULT = {"coordinator": 500, "leader": 250, "worker": 150, "critic": 150}
KIND_RULES = [("coordinator", ("coordinator", "manager", "协调")),
              ("leader", ("lead", "leader", "队长")),
              ("critic", ("critic", "review", "审核", "评审"))]
IDENTITY_RE = re.compile(r"^(?:#+\s*|你是|You are\s+)(.{4,120})$", re.M)


def sanitize_id(stem: str) -> str:
    """按 team.schema.json 的 id 模式清洗：^[a-z0-9][a-z0-9-]{0,31}[a-z0-9]$"""
    low = stem.lower()
    low = re.sub(r"[^a-z0-9-]", "-", low).strip("-")
    low = re.sub(r"-{2,}", "-", low)[:32]
    return low or "role"


def infer_kind(stem: str) -> str:
    low = stem.lower()
    for kind, needles in KIND_RULES:
        if any(n in low for n in needles):
            return kind
    return "worker"


def first_identity(path: str) -> str:
    try:
        head = open(path, encoding="utf-8", errors="ignore").read(4096)
    except OSError:
        return ""
    m = IDENTITY_RE.search(head)
    return (m.group(1).strip()[:80] if m else "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Reverse-generate a Millforge team.json skeleton from existing roles (B-7 phase 1)")
    ap.add_argument("--from", dest="src", required=True, help="directory containing *.soul.md")
    ap.add_argument("--name", required=True)
    ap.add_argument("--mode", default="multi_user", choices=["single_user", "multi_user"])
    ap.add_argument("--lang", default="zh", choices=["zh", "en"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if not os.path.isdir(a.src):
        print(json.dumps({"error": f"not a directory: {a.src}"}), file=sys.stderr)
        return 2
    stems = sorted(f[:-len(".soul.md")] for f in os.listdir(a.src)
                   if f.endswith(".soul.md") and not f.endswith(".en.soul.md"))
    if not stems:
        print(json.dumps({"error": f"no *.soul.md found in {a.src}"}), file=sys.stderr)
        return 2

    roles, todos = [], 0
    for stem in stems:
        kind = infer_kind(stem)
        ident = first_identity(os.path.join(a.src, f"{stem}.soul.md"))
        rid = sanitize_id(stem)
        roles.append({
            "id": rid, "kind": kind,
            "profile": "TODO: 角色画像（从存量 SOUL 转录后替换，≥10 字符）",
            "domains": [], "skills": [], "budget": BUDGET_DEFAULT[kind],
        })
        if not ident:
            todos += 1

    doc = {
        "name": a.name,
        "mode": a.mode,
        "lang": a.lang,
        "template": None,  # TODO: 人工改选 software/embedded/data/content/business/custom（custom 需 industry_fragment）
        "charter": {
            "mission": "TODO: 存量团队使命（从迁移前的团队章程转录，勿猜测）",
            "scope": ["TODO: 交付边界 1", "TODO: 交付边界 2"],
            "non_goals": ["TODO: 明确不做的事"],
        },
        "roles": roles,
        "protocol": {"nmh": True, "nma": True, "five_clauses": True, "attention": True,
                     "dual_channel": True, "fuse_threshold": 2, "fuse_window_seconds": 30},
        "roster": [{"id": "TODO-human-a", "role": "accountable", "weight": 1.0}],
        "experimental": False,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    summary = {
        "ok": True, "out": a.out, "roles": len(roles),
        "kinds": {k: sum(1 for r in roles if r["kind"] == k) for k in BUDGET_DEFAULT},
        "todo_markers": todos + 1,
        "next": "按 migration/MIGRATION-CHECKLIST.md 人工确认（charter/roster/权重/TODO 全部替换）后进阶段 2",
        "identity_found_note": "soul 首段身份行未找到的角色各计 1 个 TODO（需人工补 role 描述）",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
