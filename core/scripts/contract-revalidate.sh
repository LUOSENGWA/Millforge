#!/usr/bin/env bash
# millforge core script: contract-revalidate.sh
# B-3 契约 pinning 重验触发器（确定性，运行时无关）
#
# 输入: --pinned-ref <ref@semver> --pinned-fingerprint <contract:<type>:<sha256-8>>
#       --returned-fingerprint <...> --compat-report <path> [--dry-run]
# 输出: stdout JSON {diff_class: none|minor|major, action: accept|revalidate|rework, reason}
# 退出码: 0=accept; 30=revalidate（在途 minor=重验非返工）; 31=rework（major 必返工）; 32=兼容性报告缺失/不可读
# 幂等性: 幂等（读 pin + 读返回指纹 + 读报告 + 写日志；重验动作本身由调用方决定）
# 日志: $HOME/.millforge/logs/contract-revalidate.jsonl
# 前置检查: pinned_ref 与 returned 均非空；兼容性报告存在且格式合法
#
# 兼容性报告 schema: {"provider_semver":"x.y.z","consumer_semver":"x.y.z","diff_class":"none|minor|major","changes":[...]}
# C-2 约束: provider/consumer 指纹必须同一 semver 线（major 号一致），否则至少 major。
set -euo pipefail

PINNED_REF=""; PINNED_FP=""; RETURNED_FP=""; REPORT=""; DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pinned-ref) PINNED_REF="${2:?}"; shift 2 ;;
    --pinned-fingerprint) PINNED_FP="${2:?}"; shift 2 ;;
    --returned-fingerprint) RETURNED_FP="${2:?}"; shift 2 ;;
    --compat-report) REPORT="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 32 ;;
  esac
done

log() {
  local dir="${HOME}/.millforge/logs"; mkdir -p "$dir" 2>/dev/null || true
  printf '%s\n' "$1" >> "${dir}/contract-revalidate.jsonl" 2>/dev/null || true
}

fail() {
  printf '%s\n' "$2"
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$1,\"summary\":\"$2\"}"
  exit "$1"
}

if [[ -z "$PINNED_REF" || -z "$PINNED_FP" || -z "$RETURNED_FP" || -z "$REPORT" ]]; then
  fail 32 '{"diff_class":"unknown","action":"none","reason":"missing required arguments"}'
fi
if [[ ! -r "$REPORT" ]]; then
  fail 32 "{\"diff_class\":\"unknown\",\"action\":\"none\",\"reason\":\"compat-report unreadable: $REPORT\"}"
fi

CODE=0
RESULT=$(PINNED_REF="$PINNED_REF" PINNED_FP="$PINNED_FP" RETURNED_FP="$RETURNED_FP" REPORT="$REPORT" python3 - <<'PYEOF'
import json, os, re, sys

env = os.environ
report_path = env["REPORT"]
pinned_ref = env["PINNED_REF"]
pinned_fp = env["PINNED_FP"]
returned_fp = env["RETURNED_FP"]

def out(code, payload):
    print(json.dumps(payload))
    sys.exit(code)

def fp_semver_line(fp):
    # contract:<semver>:<sha256-8>
    m = re.match(r"^contract:(\d+)\.", fp or "")
    return m.group(1) if m else None

try:
    with open(report_path, encoding="utf-8") as f:
        rep = json.load(f)
except Exception as e:
    out(32, {"diff_class": "unknown", "action": "none", "reason": f"compat-report parse failure: {e}"})

dc = rep.get("diff_class")
if dc not in ("none", "minor", "major"):
    out(32, {"diff_class": "unknown", "action": "none", "reason": f"illegal diff_class {dc!r}"})

reasons = []
# 指纹一致 = 无变化（报告应 none；若不一致以报告为准并记录）
if pinned_fp == returned_fp and dc != "none":
    reasons.append("fingerprint equal but report claims change; report wins (pin 陈旧)")
# C-2: 同一 semver 线
pl, rl = fp_semver_line(pinned_fp), fp_semver_line(returned_fp)
if pl and rl and pl != rl:
    if dc != "major":
        dc = "major"
    reasons.append(f"semver line crossed {pl} -> {rl}")
prov = str(rep.get("provider_semver", ""))
cons = str(rep.get("consumer_semver", ""))
pm, cm = prov.split(".", 1), cons.split(".", 1)
if pm and cm and pm[0] != cm[0]:
    if dc != "major":
        dc = "major"
    reasons.append(f"provider/consumer major mismatch {prov} vs {cons}")

if dc == "none":
    out(0, {"diff_class": "none", "action": "accept", "reason": "; ".join(reasons) or "no change"})
elif dc == "minor":
    out(30, {"diff_class": "minor", "action": "revalidate",
             "reason": ("; ".join(reasons) + "; " if reasons else "") + "在途 minor=重验非返工（B-3），重验由调用方触发而非 spawn 自述"})
else:
    out(31, {"diff_class": "major", "action": "rework",
             "reason": ("; ".join(reasons) + "; " if reasons else "") + "major 必返工（B-3）"})
PYEOF
) || CODE=$?
printf '%s\n' "$RESULT"
log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$CODE,\"pinned_ref\":\"$PINNED_REF\",\"dry_run\":$DRY_RUN}"
exit "$CODE"
