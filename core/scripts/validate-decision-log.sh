#!/usr/bin/env bash
# millforge core script: validate-decision-log.sh
# B-1 第 1 层 schema 校验（协议语义的确定性实现，运行时无关）
#
# 输入: <decision.json 路径> [--task-id <id>] [--spawn-id <id>] [--dry-run]
# 输出: stdout JSON {valid: bool, errors[]: {field, rule, message}}
# 退出码: 0=通过; 10=schema 违规; 11=条数超限且含 contract_touch 被截断; 12=文件不可读/JSON 解析失败
# 幂等性: 无副作用（纯校验），可重复执行
# 日志: $HOME/.millforge/logs/validate-decision-log.jsonl
# 实施位置: 父执行体在派发 merge 前调用（见 bindings/）
#
# decision.json schema (schema_version 1.0):
# {
#   "schema_version": "1.0",
#   "task_id": "...",
#   "spawn_id": "...",
#   "truncated": false,
#   "entries": [{
#     "id": "d1",
#     "decision": "...",
#     "rationale": "...",
#     "decision_class": "R1"|"R2"|"R3"|"R4"|"R5"|"R6",
#     "affected_artifacts": ["..."],
#     "contract_touch": false,
#     "assumptions": [{"key": "...", "holds": true}],
#     "type": "...",            # 可选；C-1 封闭枚举，由 type_registry 覆盖
#     "field": "...",           # 可选：artifact 内字段路径
#     "value": "...",           # 可选：规范化值（冲突检测用）
#     "decided_at": "iso8601"
#   }]
# }
set -euo pipefail

DECISION_FILE=""
TASK_ID=""
SPAWN_ID=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task-id) TASK_ID="${2:?}"; shift 2 ;;
    --spawn-id) SPAWN_ID="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) DECISION_FILE="$1"; shift ;;
  esac
done

log() { # $1=json-line
  local dir="${HOME}/.millforge/logs"
  mkdir -p "$dir" 2>/dev/null || true
  printf '%s\n' "$1" >> "${dir}/validate-decision-log.jsonl" 2>/dev/null || true
}

fail() { # $1=exit_code $2=json
  printf '%s\n' "$2"
  log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$1,\"summary\":\"$2\"}"
  exit "$1"
}

if [[ -z "$DECISION_FILE" ]]; then
  fail 12 '{"valid":false,"errors":[{"field":"input","rule":"usage","message":"decision.json path required"}]}'
fi
if [[ ! -r "$DECISION_FILE" ]]; then
  fail 12 "{\"valid\":false,\"errors\":[{\"field\":\"input\",\"rule\":\"file-readable\",\"message\":\"unreadable: $DECISION_FILE\"}]}"
fi

CODE=0
RESULT=$(DECISION_FILE="$DECISION_FILE" TASK_ID="$TASK_ID" SPAWN_ID="$SPAWN_ID" DRY_RUN="$DRY_RUN" python3 - <<'PYEOF'
import json, os, re, sys

path = os.environ["DECISION_FILE"]
expect_task = os.environ.get("TASK_ID", "")
expect_spawn = os.environ.get("SPAWN_ID", "")

errors = []
SUPPORTED = {"1.0"}
CLASSES = {"R1","R2","R3","R4","R5","R6"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")

def err(field, rule, message):
    errors.append({"field": field, "rule": rule, "message": message})

try:
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
except Exception as e:
    err("input", "json-parse", str(e))
    print(json.dumps({"valid": False, "errors": errors}))
    sys.exit(12)

if not isinstance(doc, dict):
    err("input", "json-object", "top-level must be an object")
    print(json.dumps({"valid": False, "errors": errors}))
    sys.exit(12)

sv = doc.get("schema_version")
if sv not in SUPPORTED:
    err("schema_version", "supported-enum", f"got {sv!r}, supported {sorted(SUPPORTED)}")

tid = doc.get("task_id", "")
if not isinstance(tid, str) or not tid:
    err("task_id", "required-nonempty", "missing or empty")
elif expect_task and tid != expect_task:
    err("task_id", "match-arg", f"doc={tid} != --task-id={expect_task}")

sid = doc.get("spawn_id", "")
if not isinstance(sid, str) or not sid:
    err("spawn_id", "required-nonempty", "missing or empty")
elif expect_spawn and sid != expect_spawn:
    err("spawn_id", "match-arg", f"doc={sid} != --spawn-id={expect_spawn}")

entries = doc.get("entries")
if not isinstance(entries, list):
    err("entries", "required-list", "missing or not a list")
    entries = []

truncated = doc.get("truncated", False)
seen_ids = set()
contract_touch_count = 0
for i, e in enumerate(entries):
    p = f"entries[{i}]"
    if not isinstance(e, dict):
        err(p, "object", "entry must be an object"); continue
    eid = e.get("id")
    if not eid or eid in seen_ids:
        err(f"{p}.id", "unique-nonempty", f"id={eid!r}")
    seen_ids.add(eid)
    for fld in ("decision", "rationale"):
        if not isinstance(e.get(fld), str) or not e.get(fld):
            err(f"{p}.{fld}", "required-nonempty", "missing or empty")
    dc = e.get("decision_class")
    if dc not in CLASSES:
        err(f"{p}.decision_class", "enum", f"got {dc!r}, must be one of {sorted(CLASSES)}")
    aa = e.get("affected_artifacts")
    if not isinstance(aa, list) or not all(isinstance(x, str) and x for x in aa):
        err(f"{p}.affected_artifacts", "list-of-nonempty-str", "must be list of non-empty strings")
    if not isinstance(e.get("contract_touch", False), bool):
        err(f"{p}.contract_touch", "bool", "must be boolean")
    if e.get("contract_touch"):
        contract_touch_count += 1
    ass = e.get("assumptions", [])
    if isinstance(ass, list):
        for j, a in enumerate(ass):
            if not isinstance(a, dict) or not a.get("key") or not isinstance(a.get("holds"), bool):
                err(f"{p}.assumptions[{j}]", "assumption-shape", "needs {key: str, holds: bool}")
    if "value" in e and not isinstance(e["value"], (str, int, float, bool, list)):
        err(f"{p}.value", "scalar-or-list", "unsupported value type")
    da = e.get("decided_at")
    if not isinstance(da, str) or not ISO.match(da):
        err(f"{p}.decided_at", "iso8601", f"got {da!r}")

exit_code = 0
if contract_touch_count > 10:
    err("entries", "contract-touch-cap", f"{contract_touch_count} contract_touch entries exceed cap 10; contract-touch entries must never be truncated")
    exit_code = 11
elif len(entries) > 10 and truncated:
    # 截断本身允许，但当超限且存在 contract_touch 条目时 = 被截断风险 = 违规
    if contract_touch_count > 0:
        err("entries", "truncated-with-contract-touch", f"truncated=true with {contract_touch_count} contract_touch entries present")
        exit_code = 11
elif len(entries) > 10 and not truncated:
    err("entries", "cap-without-truncated-flag", f"{len(entries)} entries > 10 without truncated=true")
    exit_code = 10

if errors and exit_code == 0:
    exit_code = 10
print(json.dumps({"valid": not errors, "errors": errors}))
sys.exit(exit_code)
PYEOF
) || CODE=$?
printf '%s\n' "$RESULT"
log "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"exit\":$CODE,\"task_id\":\"${TASK_ID}\",\"spawn_id\":\"${SPAWN_ID}\",\"dry_run\":$DRY_RUN}"
exit "$CODE"
