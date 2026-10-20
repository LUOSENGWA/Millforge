#!/usr/bin/env bash
# millforge core script: aggregate-vote.sh
# R2/R5 加权计票（确定性，运行时无关）
#
# 输入: --task-meta <path> --decision-id <id> --rule <R2|R5>
#       [--now <iso8601>] [--out <aggregation_result.json 路径>] [--dry-run]
# 输出: stdout JSON {task_id, decision_id, rule_applied, votes[]: {user, weight, choice, received_at, counted, demoted},
#                   sums: {approve, reject, abstain}, outcome: pass|reject|tie|timeout|wait,
#                   dissent[], next: write_result|escalate|block|wait, window_expired: bool, idempotent_hit: bool}
# 退出码: 0=产生 outcome（pass/reject/wait 窗内）; 80=平局需升级; 81=不可逆超时需阻塞; 82=票数据不可读
# 幂等性: 以 decision_id + rule 为幂等键；--out 已存在 → 返回同一 outcome（idempotent_hit=true）
# 日志: $HOME/.millforge/logs/aggregate-vote.jsonl
# 语义: 加权多数仅限 R2（资源类）/R4/R5（B-8/C-3：永不用于触及已锁 spec 的 R6）；
#       R5 锁定者超时（B-4）：不可逆 24h / 可逆 4h 窗口，超时权重 ×2 失效降 1.0（非默认同意），迟到应答恢复权重重算；
#       B-5：decision_status==blocked 时禁弃权计票（defer 完全不计）；
#       defer = 弃权（不计入 approve/reject 权重，记入 dissent）；非默认同意（无票 ≠ 同意）。
#
# task meta 读取面（attention 条目 = 决策载体，T3）:
# {"task_id", "decision_status", "attention":[
#   {"id","kind","status":"open|resolved","opened_at","due_at","reversible":bool,
#    "locker":"user|null","votes":[{"user","weight","choice":"approve|reject|defer","received_at"}]}]}
# R2 默认窗口 4h（无 due_at 时）；R5 默认窗口：reversible?4h:24h。
set -euo pipefail

META=""; DECISION=""; RULE=""; NOW=""; OUT=""; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-meta) META="${2:?}"; shift 2 ;;
    --decision-id) DECISION="${2:?}"; shift 2 ;;
    --rule) RULE="${2:?}"; shift 2 ;;
    --now) NOW="${2:?}"; shift 2 ;;
    --out) OUT="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 82 ;;
  esac
done

log() {
  local dir="${HOME}/.millforge/logs"; mkdir -p "$dir" 2>/dev/null || true
  printf '%s\n' "$1" >> "${dir}/aggregate-vote.jsonl" 2>/dev/null || true
}

if [[ -z "$META" || ! -r "$META" || -z "$DECISION" || "$RULE" != "R2" && "$RULE" != "R5" ]]; then
  printf '%s\n' '{"error":"usage: aggregate-vote.sh --task-meta <p> --decision-id <id> --rule R2|R5 [--now] [--out] [--dry-run]"}'
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":82}"
  exit 82
fi

# 幂等命中（返回同一 outcome，显式标记 idempotent_hit）
if [[ -n "$OUT" && -r "$OUT" ]]; then
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d['idempotent_hit']=True;print(json.dumps(d,ensure_ascii=False,indent=1))" "$OUT"
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":0,\"idempotent_hit\":true}"
  exit 0
fi

CODE=0
RESULT=$(META="$META" DECISION="$DECISION" RULE="$RULE" NOW="$NOW" OUT="${OUT:-}" DRY_RUN="$DRY_RUN" python3 - <<'PYEOF'
import json, os, sys
from datetime import datetime, timedelta, timezone

env = os.environ
meta_path, decision_id, rule = env["META"], env["DECISION"], env["RULE"]
now_s = env.get("NOW") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def parse(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None

now = parse(now_s)
if now is None:
    print(json.dumps({"error": f"bad --now: {now_s}"})); sys.exit(82)

try:
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    atts = [a for a in meta.get("attention", []) if isinstance(a, dict) and a.get("id") == decision_id]
    if not atts:
        print(json.dumps({"error": f"decision {decision_id} not found in attention[]"})); sys.exit(82)
except Exception:
    print(json.dumps({"error": "task meta parse failure"})); sys.exit(82)

att = atts[0]
opened = parse(att.get("opened_at"))
due = parse(att.get("due_at"))
if opened is None:
    print(json.dumps({"error": "attention.opened_at unparsable"})); sys.exit(82)
if due is None:
    if rule == "R5":
        window = 24 if not att.get("reversible", True) else 4
    else:
        window = 4
    due = opened + timedelta(hours=window)
window_expired = now > due
status = meta.get("decision_status", "open")
blocked = status == "blocked"  # B-5: 熔断后禁弃权计票

votes_out = []
s_a = s_r = s_abs = 0.0
dissent = []
locker = att.get("locker")
for v in att.get("votes", []):
    user, choice, w = v.get("user"), v.get("choice"), float(v.get("weight", 1.0))
    rec = parse(v.get("received_at"))
    demoted = False
    counted = choice in ("approve", "reject")
    # B-4: R5 锁定者迟到（窗口后应答）→ 权重降 1.0
    if rule == "R5" and user == locker and locker is not None and rec is not None and rec > due and w > 1.0:
        w = 1.0
        demoted = True
    # B-5 禁弃权计票（blocked 态）：defer 票计入分母（对通过不利），非 blocked 态弃权不计入分母
    if choice == "defer":
        counted = bool(blocked)
    entry = {"user": user, "weight": w, "choice": choice, "received_at": v.get("received_at"),
             "counted": counted, "demoted": demoted}
    votes_out.append(entry)
    if choice not in ("approve", "reject", "defer"):
        print(json.dumps({"error": f"illegal vote choice {choice!r}"})); sys.exit(82)
    if choice == "approve" and counted:
        s_a += w
    elif choice == "reject" and counted:
        s_r += w
    elif choice == "defer":
        s_abs += w
        if counted:
            dissent.append({"user": user, "reason": "abstain-counted(blocked)"})
        else:
            dissent.append({"user": user, "reason": "abstain"})

total = s_a + s_r + (s_abs if blocked else 0.0)
if total == 0:
    outcome, next_action, code = ("timeout" if window_expired else "wait"), ("block" if window_expired and rule == "R5" and not att.get("reversible", True) else "wait"), (81 if window_expired and rule == "R5" and not att.get("reversible", True) else 0)
elif s_a == s_r:
    outcome, next_action, code = "tie", "escalate", 80
elif s_a > s_r and s_a > total / 2.0:
    outcome, next_action, code = "pass", "write_result", 0
elif s_r > s_a:
    outcome, next_action, code = "reject", "write_result", 0
    dissent.extend({"user": e["user"], "reason": "minority"} for e in votes_out if e["choice"] == "approve" and e["counted"])
else:
    # s_a < s_r 不成立且 s_a <= total/2 → 弃权/缺席占多数，不通过但非 reject（需升级）
    outcome, next_action, code = "tie", "escalate", 80

result = {
    "task_id": meta.get("task_id"),
    "decision_id": decision_id,
    "rule_applied": rule,
    "votes": votes_out,
    "sums": {"approve": round(s_a, 4), "reject": round(s_r, 4), "abstain": round(s_abs, 4)},
    "outcome": outcome,
    "dissent": dissent,
    "next": next_action,
    "window_expired": window_expired,
    "blocked_no_abstain": blocked,
    "idempotent_hit": False,
    "aggregated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
}
print(json.dumps(result, ensure_ascii=False, indent=1))
if env.get("OUT") and not env.get("DRY_RUN") == "1":
    outp = env["OUT"]
    os.makedirs(os.path.dirname(outp) or ".", exist_ok=True)
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
sys.exit(code)
PYEOF
) || CODE=$?
printf '%s\n' "$RESULT"
log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$CODE,\"decision_id\":\"$DECISION\",\"rule\":\"$RULE\",\"dry_run\":$DRY_RUN}"
exit "$CODE"
