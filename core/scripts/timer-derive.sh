#!/usr/bin/env bash
# millforge core script: timer-derive.sh
# CAP-TIMER 定时器派生（确定性，运行时无关）
#
# 输入: --task-meta <path> [--now <iso8601>]
# 输出: stdout JSON {task_id, timers[]: {name, due_at, action, idempotency_key},
#                   next_check_at, generated_at}
# 退出码: 0=OK; 90=task meta 不可读
# 幂等性: 纯派生——同输入同输出；定时器不是状态（CAP-TIMER U1-U4）：
#   绑定层 cron 每次触发都重跑本脚本，due_at 全部来自持久化状态（task meta），
#   "定时器已运行过"不作为任何判定依据（F-2：watchdog 缓存降级为通知去重，幂等重派生）。
# 日志: $HOME/.millforge/logs/timer-derive.jsonl
# 派生规则:
#   attention-due:<id>      open attention 的 due_at        → action run:attention-stall
#   mismatch-due:<cid>:<n>  open mismatch opened_at+窗口    → action run:mismatch-window
#   vote-due:<decision-id>  决策窗口结束（R5 24h/4h, R2 4h） → action run:aggregate-vote
#   reopen-window:<id>      resolved 决策的 reopen_until    → action run:attention-stall
#   staleness-alert        dispatched_at+6h（未闭环）        → action notify:stale
#   stale-cleanup          dispatched_at+48h（未闭环）       → action cleanup:stale
#
# task meta 读取面:
# {"task_id","dispatched_at":"iso|null","completed_at":"iso|null",
#  "attention":[...], "verification_mismatch":[...]}
set -euo pipefail

META=""; NOW=""; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-meta) META="${2:?}"; shift 2 ;;
    --now) NOW="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 90 ;;
  esac
done

log() {
  local dir="${HOME}/.millforge/logs"; mkdir -p "$dir" 2>/dev/null || true
  printf '%s\n' "$1" >> "${dir}/timer-derive.jsonl" 2>/dev/null || true
}

if [[ -z "$META" || ! -r "$META" ]]; then
  printf '%s\n' '{"error":"task meta missing or unreadable"}'
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":90}"
  exit 90
fi

CODE=0
RESULT=$(META="$META" NOW="$NOW" python3 - <<'PYEOF'
import json, os, sys
from datetime import datetime, timedelta, timezone

meta_path = os.environ["META"]
now = datetime.now(timezone.utc)

def parse(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None

try:
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
except Exception:
    print(json.dumps({"error": "task meta parse failure"})); sys.exit(90)

timers = []
task_id = meta.get("task_id")

for a in meta.get("attention", []):
    if not isinstance(a, dict) or not a.get("id"):
        continue
    aid = a["id"]
    due = parse(a.get("due_at")) or parse(a.get("reopen_until"))
    if a.get("status") == "open" and due:
        timers.append({"name": f"attention-due:{aid}", "due_at": iso(due),
                       "action": "run:attention-stall", "idempotency_key": f"{task_id}:{aid}:due"})
    elif a.get("status") == "resolved" and a.get("reopen_until"):
        ru = parse(a["reopen_until"])
        if ru:
            timers.append({"name": f"reopen-window:{aid}", "due_at": iso(ru),
                           "action": "run:attention-stall", "idempotency_key": f"{task_id}:{aid}:reopen"})

for i, m in enumerate(meta.get("verification_mismatch", [])):
    if not isinstance(m, dict) or m.get("status") != "open":
        continue
    opened = parse(m.get("opened_at"))
    if opened:
        cid = m.get("criterion_id") or f"#{i}"
        window_h = float(m.get("window_hours", 24))
        timers.append({"name": f"mismatch-due:{cid}:{i}", "due_at": iso(opened + timedelta(hours=window_h)),
                       "action": "run:mismatch-window", "idempotency_key": f"{task_id}:{cid}:{i}:due"})

for a in meta.get("attention", []):
    if not isinstance(a, dict) or a.get("status") != "open":
        continue
    opened, due = parse(a.get("opened_at")), parse(a.get("due_at"))
    if opened and not due:
        rule = a.get("rule", "R2")
        window = (24 if not a.get("reversible", True) else 4) if rule == "R5" else 4
        timers.append({"name": f"vote-due:{a['id']}", "due_at": iso(opened + timedelta(hours=window)),
                       "action": "run:aggregate-vote", "idempotency_key": f"{task_id}:{a['id']}:vote-due"})

disp, comp = parse(meta.get("dispatched_at")), parse(meta.get("completed_at"))
if disp and not comp:
    timers.append({"name": "staleness-alert", "due_at": iso(disp + timedelta(hours=6)),
                   "action": "notify:stale", "idempotency_key": f"{task_id}:stale:6h"})
    timers.append({"name": "stale-cleanup", "due_at": iso(disp + timedelta(hours=48)),
                   "action": "cleanup:stale", "idempotency_key": f"{task_id}:stale:48h"})

timers.sort(key=lambda t: (t["due_at"] or "", t["name"]))
print(json.dumps({
    "task_id": task_id,
    "timers": timers,
    "next_check_at": timers[0]["due_at"] if timers else None,
    "generated_at": iso(now),
}, ensure_ascii=False, indent=1))
sys.exit(0)
PYEOF
) || CODE=$?
printf '%s\n' "$RESULT"
log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$CODE,\"dry_run\":$DRY_RUN}"
exit "$CODE"
