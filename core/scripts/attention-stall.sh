#!/usr/bin/env bash
# millforge core script: attention-stall.sh
# B-5 R6 停摆熔断计数（确定性，运行时无关）
#
# 输入: --task-meta <task-meta.json 路径> [--now <iso8601>] [--dry-run]
# 输出: stdout JSON {task_id, stall_count, current_level, last_human_response, stallable_ids[], next_action: none|watch|escalate_to_owner|freeze}
# 退出码: 0=无需动作(level≤1); 40=escalate（第 2 次：升级 owner + blocked + 禁弃权计票）; 41=freeze（第 3 次：冻结 + 人显式解冻）; 42=task meta 不可读
# 幂等性: 以 task meta 中 attention[] 为唯一数据源；计数是读取派生（非写入累加），重复执行不改变结果
# 日志: $HOME/.millforge/logs/attention-stall.jsonl
# 语义（B-5）: 任何人应答 → 计数归零（派生：只统计 last_human_response 之后开立的 open 超时项）
#
# task meta schema（本脚本读取面）:
# {"task_id":"...", "decision_status":"open|blocked|frozen|paused|spec_conflict",
#  "attention":[{"id","kind","status":"open|resolved","opened_at","due_at",
#                "resolved_at":"iso|null","resolved_by":"id|null",
#                "votes":[{"user","weight","choice":"approve|reject|defer","received_at"}]}]}
set -euo pipefail

META=""; NOW=""; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-meta) META="${2:?}"; shift 2 ;;
    --now) NOW="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 42 ;;
  esac
done

log() {
  local dir="${HOME}/.millforge/logs"; mkdir -p "$dir" 2>/dev/null || true
  printf '%s\n' "$1" >> "${dir}/attention-stall.jsonl" 2>/dev/null || true
}

if [[ -z "$META" || ! -r "$META" ]]; then
  J='{"error":"task meta missing or unreadable"}'
  printf '%s\n' "$J"
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":42,\"summary\":\"meta unreadable\"}"
  exit 42
fi

CODE=0
RESULT=$(META="$META" NOW="$NOW" python3 - <<'PYEOF'
import json, os, sys
from datetime import datetime, timezone

meta_path = os.environ["META"]
now_s = os.environ.get("NOW") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def parse(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

now = parse(now_s)
if now is None:
    print(json.dumps({"error": f"bad --now: {now_s}"})); sys.exit(42)

try:
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    atts = meta.get("attention")
    if not isinstance(atts, list):
        print(json.dumps({"error": "attention[] missing"})); sys.exit(42)
except Exception:
    print(json.dumps({"error": "task meta parse failure"})); sys.exit(42)

resolved = [a for a in atts if isinstance(a, dict) and a.get("status") == "resolved" and parse(a.get("resolved_at"))]
last_human = max((parse(a["resolved_at"]) for a in resolved), default=None)

stallable = []
for a in atts:
    if not isinstance(a, dict) or a.get("status") != "open":
        continue
    opened, due = parse(a.get("opened_at")), parse(a.get("due_at"))
    if not due or not due < now:
        continue
    if last_human is not None and opened is not None and opened <= last_human:
        continue  # 人应答之后的才计入（任何人应答归零语义）
    stallable.append(a.get("id", "?"))

count = len(stallable)
status = meta.get("decision_status", "open")
if count >= 3:
    level, action, code = 3, "freeze", 41
elif count >= 2:
    level, action, code = 2, "escalate_to_owner", 40
elif count == 1:
    level, action, code = 1, "watch", 0
else:
    level, action, code = 0, "none", 0

# 幂等：已处于该状态或更重状态 → 不重复升级语义（next_action 保持一致）
if status == "frozen" and count >= 3:
    action = "freeze"
elif status == "blocked" and count >= 2 and code == 40:
    action = "escalate_to_owner"

print(json.dumps({
    "task_id": meta.get("task_id"),
    "stall_count": count,
    "current_level": level,
    "decision_status": status,
    "last_human_response": last_human.strftime("%Y-%m-%dT%H:%M:%SZ") if last_human else None,
    "stallable_ids": stallable,
    "next_action": action,
}, ensure_ascii=False))
sys.exit(code)
PYEOF
) || CODE=$?
printf '%s\n' "$RESULT"
log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$CODE,\"dry_run\":$DRY_RUN}"
exit "$CODE"
