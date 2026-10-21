#!/usr/bin/env bash
# millforge core script: verification-mismatch-window.sh
# B-6 critic 死环防护：mismatch 计数 + 24h 裁决窗口（确定性，运行时无关）
#
# 输入: --task-meta <path> [--now <iso8601>] [--dry-run]
# 输出: stdout JSON {task_id, open_mismatches[]: {criterion_id, round, age_hours, action: wait|expire_to_spec},
#                   rounds_by_criterion{}, should_freeze: bool, total_count, next_action}
# 退出码: 0=无动作; 50=有 mismatch 到期（维持原 spec + critic 记 dissent 且仍出评分卡）; 51=同一 criterion 第 3 轮 → 冻结升级; 52=task meta 不可读
# 幂等性: 读 task meta 的 verification_mismatch[] 派生状态；不修改 task meta（到期动作由绑定层 write 脚本执行）
# 日志: $HOME/.millforge/logs/verification-mismatch-window.jsonl
# 语义（B-6）: 超时=维持 spec+critic 记 dissent 且必须仍出评分卡；同一 criterion 最多 2 轮，第 3 轮冻结升级
#             （多 critic 下按投票轮计——每轮 = 同一 criterion_id 的一条新记录）
#
# task meta 读取面:
# {"task_id":"...", "verification_mismatch":[{"criterion_id","opened_at","window_hours":24,
#   "status":"open|expired|frozen","round_note":"..."}]}
set -euo pipefail

META=""; NOW=""; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-meta) META="${2:?}"; shift 2 ;;
    --now) NOW="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 52 ;;
  esac
done

log() {
  local dir="${HOME}/.millforge/logs"; mkdir -p "$dir" 2>/dev/null || true
  printf '%s\n' "$1" >> "${dir}/verification-mismatch-window.jsonl" 2>/dev/null || true
}

if [[ -z "$META" || ! -r "$META" ]]; then
  printf '%s\n' '{"error":"task meta missing or unreadable"}'
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":52}"
  exit 52
fi

CODE=0
RESULT=$(META="$META" NOW="$NOW" python3 - <<'PYEOF'
import json, os, sys
from datetime import datetime

meta_path = os.environ["META"]
now_s = os.environ.get("NOW") or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

now = parse(now_s)
if now is None:
    print(json.dumps({"error": f"bad --now: {now_s}"})); sys.exit(52)

try:
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    mms = meta.get("verification_mismatch")
    if mms is None:
        print(json.dumps({"task_id": meta.get("task_id"), "open_mismatches": [], "rounds_by_criterion": {},
                          "should_freeze": False, "total_count": 0, "next_action": "none"}))
        sys.exit(0)
    if not isinstance(mms, list):
        print(json.dumps({"error": "verification_mismatch[] not a list"})); sys.exit(52)
except Exception:
    print(json.dumps({"error": "task meta parse failure"})); sys.exit(52)

rounds = {}
open_list = []
expired_any = False
freeze = False
for i, m in enumerate(mms):
    if not isinstance(m, dict):
        continue
    cid = m.get("criterion_id") or f"#{i}"
    opened = parse(m.get("opened_at"))
    if opened is None:
        print(json.dumps({"error": f"verification_mismatch[{i}].opened_at unparsable"})); sys.exit(52)
    rounds[cid] = rounds.get(cid, 0) + 1
    if rounds[cid] >= 3 and m.get("status") != "frozen":
        freeze = True
    if m.get("status") == "open":
        window_h = float(m.get("window_hours", 24))
        age = (now - opened).total_seconds() / 3600.0
        if age >= window_h:
            open_list.append({"criterion_id": cid, "round": rounds[cid], "age_hours": round(age, 2),
                              "action": "expire_to_spec"})
            expired_any = True
        else:
            open_list.append({"criterion_id": cid, "round": rounds[cid], "age_hours": round(age, 2),
                              "action": "wait"})

if freeze:
    code, action = 51, "freeze"
elif expired_any:
    code, action = 50, "expire_to_spec"
else:
    code, action = 0, "none"

print(json.dumps({
    "task_id": meta.get("task_id"),
    "open_mismatches": open_list,
    "rounds_by_criterion": {k: rounds[k] for k in sorted(rounds)},
    "should_freeze": freeze,
    "total_count": len(mms),
    "next_action": action,
}, ensure_ascii=False, indent=1))
sys.exit(code)
PYEOF
) || CODE=$?
printf '%s\n' "$RESULT"
log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$CODE,\"dry_run\":$DRY_RUN}"
exit "$CODE"
