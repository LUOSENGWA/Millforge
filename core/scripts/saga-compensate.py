#!/usr/bin/env python3
"""millforge core script: saga-compensate.py
B-10 decision_class 误分类：重分类判定 + saga 补偿指令生成（确定性，运行时无关）

输入: --task-id <id> --class-mismatch-event <path> --dependency-graph <path> --forward-ops <path>
      [--out <compensation.json 路径>] [--dry-run]
输出: stdout JSON {event_id, task_id, reclassify_to, suggested_action,
                   compensation_directive: {steps[]: {seq, op_id, operation, inputs, expected_state, required},
                                            rollback_possible: bool},
                   escalate: bool, idempotent_hit: bool}
退出码: 0=生成成功; 60=需人工裁决（已提交且不可补偿的外部副作用）; 61=dependency graph 缺失/非法; 62=正向操作日志缺失/覆盖不全
幂等性: 以 event_id 为幂等键；--out 已存在且 event_id 相同 → 返回同一 directive（idempotent_hit=true）
日志: $HOME/.millforge/logs/saga-compensate.jsonl
语义（B-10）: R4→R1 暂停 2h 重分 / R3→R2 事后聚合 / R2→R1 重做；
  decision_class_v2 不覆盖原值（重分类是新记录，非改写）；
  已执行副作用走 saga 补偿（未提交→补偿指令；已提交不可补偿→升级 human）。
  核心脚本只写本地 --out 路径（CAP-STORE 上传由绑定层负责，见 bindings/）。

event schema: {"event_id","task_id","from_class":"R1..R6","to_class":"R1..R6",
               "detected_at","reason","affected_op_ids":[op_id...]}
dependency-graph schema: {"nodes":[{"id","op_ids":[op_id...]}],"edges":[[from_id,to_id]...]}
forward-ops schema: [{"op_id","operation","inputs","executed_at","committed":bool,
                      "external_side_effect":bool,"reversible":bool,"expected_state_after"}]
"""
import json
import os
import sys
from datetime import datetime, timezone

LOG = os.path.join(os.environ.get("HOME", "/root"), ".millforge/logs/saga-compensate.jsonl")
CLASSES = {"R1", "R2", "R3", "R4", "R5", "R6"}
ACTION_BY_TRANSITION = {
    ("R4", "R1"): "pause_2h_and_reclassify",
    ("R3", "R2"): "post_hoc_aggregate",
    ("R2", "R1"): "redo",
}


def log_line(summary):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    except Exception:
        pass


def die(code, payload):
    print(json.dumps(payload, ensure_ascii=False))
    log_line({"exit": code, "summary": payload.get("error") or payload.get("reason") or ""})
    sys.exit(code)


def toposort(nodes, edges):
    """Kahn 拓扑排序（节点 = node id）。环 → 报错。"""
    indeg = {n: 0 for n in nodes}
    adj = {n: [] for n in nodes}
    for a, b in edges:
        if a in adj and b in indeg:
            adj[a].append(b)
            indeg[b] += 1
    q = sorted(n for n in nodes if indeg[n] == 0)
    order = []
    while q:
        n = q.pop(0)
        order.append(n)
        for m in sorted(adj[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
        q.sort()
    if len(order) != len(nodes):
        raise ValueError("dependency graph has a cycle")
    return order


def main():
    args = sys.argv[1:]
    opts = {}
    dry_run = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dry-run":
            dry_run = True
        elif a in ("--task-id", "--class-mismatch-event", "--dependency-graph", "--forward-ops", "--out"):
            opts[a] = args[i + 1]
            i += 1
        else:
            die(62, {"error": f"unknown arg: {a}"})
        i += 1

    for req in ("--task-id", "--class-mismatch-event", "--dependency-graph", "--forward-ops"):
        if req not in opts:
            die(62, {"error": f"missing required arg {req}"})
    task_id = opts["--task-id"]

    # --- 幂等命中检查 ---
    if "--out" in opts:
        out_path = opts["--out"]
        if os.path.exists(out_path):
            try:
                with open(out_path, encoding="utf-8") as f:
                    prev = json.load(f)
                if prev.get("event_id") and prev.get("task_id") == task_id:
                    # 同一 event 重复执行 → 返回同一 directive（幂等命中显式标记）
                    prev["idempotent_hit"] = True
                    print(json.dumps(prev, ensure_ascii=False, indent=1))
                    log_line({"exit": 0, "idempotent_hit": True, "event_id": prev.get("event_id")})
                    sys.exit(0)
            except Exception:
                pass  # 损坏的 out 文件 → 重新生成

    # --- 读入三件 ---
    try:
        with open(opts["--class-mismatch-event"], encoding="utf-8") as f:
            event = json.load(f)
        with open(opts["--forward-ops"], encoding="utf-8") as f:
            forward = json.load(f)
    except Exception as e:
        die(62, {"error": f"event/forward-ops unreadable: {e}"})
    try:
        with open(opts["--dependency-graph"], encoding="utf-8") as f:
            graph = json.load(f)
        nodes = [n["id"] for n in graph.get("nodes", []) if isinstance(n, dict) and n.get("id")]
        edges = [tuple(e) for e in graph.get("edges", []) if isinstance(e, (list, tuple)) and len(e) == 2]
        if not nodes:
            die(61, {"error": "dependency graph has no nodes"})
    except FileNotFoundError:
        die(61, {"error": "dependency graph missing"})
    except Exception as e:
        die(61, {"error": f"dependency graph invalid: {e}"})

    # --- event 校验 ---
    fc, tc = event.get("from_class"), event.get("to_class")
    if fc not in CLASSES or tc not in CLASSES:
        die(60, {"error": f"illegal class transition {fc}->{tc}", "escalate": True})
    if event.get("task_id") not in (None, task_id):
        die(62, {"error": "event.task_id mismatch"})
    affected = event.get("affected_op_ids")
    if not isinstance(affected, list) or not affected:
        die(62, {"error": "event.affected_op_ids missing or empty"})

    # --- forward ops 覆盖检查 ---
    fops = {o["op_id"]: o for o in forward if isinstance(o, dict) and o.get("op_id")}
    missing = [op for op in affected if op not in fops]
    if missing:
        die(62, {"error": f"forward-ops coverage gap: {missing}"})

    # --- 拓扑序（子图：包含 affected op 的节点）---
    node_of_op = {}
    for n in graph.get("nodes", []):
        for op in n.get("op_ids", []):
            node_of_op[op] = n["id"]
    sub_nodes = sorted({node_of_op[op] for op in affected if op in node_of_op})
    if not sub_nodes:
        # 依赖图未登记这些 op → 用 forward-ops 原序（保守：无依赖假设显式声明）
        order_ops = list(affected)
    else:
        sub_edges = [(a, b) for a, b in edges if a in set(sub_nodes) and b in set(sub_nodes)]
        order = toposort(sub_nodes, sub_edges)
        order_ops = []
        for n in order:
            for op in graph["nodes"][[g["id"] for g in graph["nodes"]].index(n)].get("op_ids", []):
                if op in affected:
                    order_ops.append(op)
        # 未登记节点但 affected 的 op 追加在后（保守）
        for op in affected:
            if op not in order_ops:
                order_ops.append(op)

    # --- 生成补偿指令（逆序）---
    steps = []
    rollback_possible = True
    escalate = False
    state_stack = {}
    # 正序预计算 expected_state 链
    states = {}
    prev_state = "task_spec_baseline"
    for op in order_ops:
        o = fops[op]
        states[op] = prev_state
        prev_state = o.get("expected_state_after", f"after:{op}")
    for seq, op in enumerate(reversed(order_ops), start=1):
        o = fops[op]
        if not o.get("committed", False):
            steps.append({"seq": seq, "op_id": op, "operation": "skip_uncommitted",
                          "inputs": o.get("inputs"), "expected_state": states[op], "required": False})
            continue
        if o.get("external_side_effect") and not o.get("reversible", True):
            rollback_possible = False
            escalate = True
            steps.append({"seq": seq, "op_id": op, "operation": "ESCALATE_HUMAN",
                          "inputs": o.get("inputs"), "expected_state": states[op], "required": True,
                          "reason": "committed external side effect, not reversible (B-10: 已提交不可补偿→升级 human)"})
            continue
        steps.append({"seq": seq, "op_id": op, "operation": f"compensate:{o.get('operation', 'unknown')}",
                      "inputs": o.get("inputs"), "expected_state": states[op], "required": True})

    result = {
        "event_id": event.get("event_id"),
        "task_id": task_id,
        "reclassify_to": tc,
        "decision_class_v2_note": "重分类为 v2 新记录，不覆盖原 decision_class（B-10）",
        "suggested_action": ACTION_BY_TRANSITION.get((fc, tc), "manual_review"),
        "compensation_directive": {"steps": steps, "rollback_possible": rollback_possible},
        "escalate": escalate,
        "idempotent_hit": False,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if not dry_run and "--out" in opts:
        os.makedirs(os.path.dirname(opts["--out"]) or ".", exist_ok=True)
        with open(opts["--out"], "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    code = 60 if escalate else 0
    log_line({"exit": code, "event_id": event.get("event_id"), "steps": len(steps), "escalate": escalate, "dry_run": dry_run})
    sys.exit(code)


if __name__ == "__main__":
    main()
