#!/usr/bin/env bash
# millforge golden-tests/scripts/run-scripts-tests.sh
# 9 个核心确定性脚本的单元测试（零 LLM，纯确定性断言）
# 用法: bash run-scripts-tests.sh   （需要 bash + python3 标准库）
set -u

SCRIPTS="$(cd "$(dirname "$0")/../../core/scripts" && pwd)"
TMP=$(mktemp -d)
export HOME="$TMP/home"          # 隔离日志
mkdir -p "$HOME/.millforge/logs"
PASS=0; FAIL=0
FAILED_CASES=()

check() { # $1=name $2=expected_code $3=actual_code [extra grep on stdout via $4]
  local name="$1" want="$2" got="$3"
  if [[ "$want" == "$got" ]]; then
    PASS=$((PASS+1)); printf 'ok   %s\n' "$name"
  else
    FAIL=$((FAIL+1)); FAILED_CASES+=("$name (want=$want got=$got)")
    printf 'FAIL %s (want=%s got=%s)\n' "$name" "$want" "$got"
  fi
}

# 运行脚本并取退出码 + stdout
run() { local out code; out=$("$@" 2>/dev/null); code=$?; LAST_OUT="$out"; LAST_CODE=$code; }

echo "=== 1. validate-decision-log.sh ==="
cat > "$TMP/valid.json" <<'EOF'
{"schema_version":"1.0","task_id":"t1","spawn_id":"s1","truncated":false,
 "entries":[{"id":"d1","decision":"use s3","rationale":"cheap","decision_class":"R2",
  "affected_artifacts":["cfg.json"],"contract_touch":false,
  "assumptions":[{"key":"k","holds":true}],"decided_at":"2026-10-19T00:00:00Z"}]}
EOF
run "$SCRIPTS/validate-decision-log.sh" "$TMP/valid.json"; check "valid doc" 0 "$LAST_CODE"
cat > "$TMP/bad.json" <<'EOF'
{"schema_version":"9.9","task_id":"t1","spawn_id":"s1","entries":[
 {"id":"d1","decision":"x","rationale":"","decision_class":"R9","affected_artifacts":[],"decided_at":"nope"}]}
EOF
run "$SCRIPTS/validate-decision-log.sh" "$TMP/bad.json"; check "schema violation" 10 "$LAST_CODE"
python3 - "$TMP/over.json" <<'EOF'
import json,sys
doc={"schema_version":"1.0","task_id":"t","spawn_id":"s","entries":[
 {"id":f"d{i}","decision":"d","rationale":"r","decision_class":"R1","affected_artifacts":["a"],"decided_at":"2026-10-19T00:00:00Z"} for i in range(11)]}
json.dump(doc,open(sys.argv[1],"w"))
EOF
run "$SCRIPTS/validate-decision-log.sh" "$TMP/over.json"; check "11 entries no truncated flag" 10 "$LAST_CODE"
python3 - "$TMP/trunc.json" <<'EOF'
import json,sys
doc={"schema_version":"1.0","task_id":"t","spawn_id":"s","truncated":True,"entries":[
 {"id":f"d{i}","decision":"d","rationale":"r","decision_class":"R1","affected_artifacts":["a"],"contract_touch":(i==0),"decided_at":"2026-10-19T00:00:00Z"} for i in range(11)]}
json.dump(doc,open(sys.argv[1],"w"))
EOF
run "$SCRIPTS/validate-decision-log.sh" "$TMP/trunc.json"; check "truncated with contract_touch" 11 "$LAST_CODE"
echo "not json" > "$TMP/broken.json"
run "$SCRIPTS/validate-decision-log.sh" "$TMP/broken.json"; check "parse failure" 12 "$LAST_CODE"

echo "=== 2. detect-conflict.py ==="
cat > "$TMP/reg.json" <<'EOF'
{"t-s3":{"dimension":"storage"},"t-api":{"dimension":"interface"}}
EOF
cat > "$TMP/ca.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sa","entries":[
 {"id":"d1","decision":"use s3","rationale":"r","decision_class":"R1","affected_artifacts":["store.cfg"],"type":"t-s3","field":"backend","value":"s3","decided_at":"2026-10-19T00:00:00Z"}]}
EOF
cat > "$TMP/cb-nofield.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sb","entries":[
 {"id":"d1","decision":"tune store","rationale":"r","decision_class":"R1","affected_artifacts":["store.cfg"],"decided_at":"2026-10-19T00:00:00Z"}]}
EOF
run python3 "$SCRIPTS/detect-conflict.py" "$TMP/ca.json" "$TMP/cb-nofield.json" --type-registry "$TMP/reg.json"
check "shared-surface only" 22 "$LAST_CODE"
cat > "$TMP/cb-hard.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sb","entries":[
 {"id":"d1","decision":"use nfs","rationale":"r","decision_class":"R1","affected_artifacts":["store.cfg"],"type":"t-s3","field":"backend","value":"nfs","decided_at":"2026-10-19T00:00:00Z"}]}
EOF
run python3 "$SCRIPTS/detect-conflict.py" "$TMP/ca.json" "$TMP/cb-hard.json" --type-registry "$TMP/reg.json"
check "hard-conflict same field diff value" 20 "$LAST_CODE"
cat > "$TMP/cb-asm.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sb","entries":[
 {"id":"d1","decision":"assume no replication","rationale":"r","decision_class":"R1",
  "affected_artifacts":["store.cfg"],"assumptions":[{"key":"replication","holds":false}],"decided_at":"2026-10-19T00:00:00Z"}]}
EOF
cat > "$TMP/ca-asm.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sa","entries":[
 {"id":"d1","decision":"assume replication","rationale":"r","decision_class":"R1",
  "affected_artifacts":["store.cfg"],"assumptions":[{"key":"replication","holds":true}],"decided_at":"2026-10-19T00:00:00Z"}]}
EOF
run python3 "$SCRIPTS/detect-conflict.py" "$TMP/ca-asm.json" "$TMP/cb-asm.json" --type-registry "$TMP/reg.json"
check "assumption-conflict" 21 "$LAST_CODE"
cat > "$TMP/cb-dim.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sb","entries":[
 {"id":"d1","decision":"redefine interface","rationale":"r","decision_class":"R1",
  "affected_artifacts":["store.cfg"],"type":"t-api","decided_at":"2026-10-19T00:00:00Z"}]}
EOF
run python3 "$SCRIPTS/detect-conflict.py" "$TMP/ca.json" "$TMP/cb-dim.json" --type-registry "$TMP/reg.json"
check "type-dimension mismatch = hard" 20 "$LAST_CODE"
cat > "$TMP/cd-none.json" <<'EOF'
{"schema_version":"1.0","task_id":"t","spawn_id":"sd","entries":[
 {"id":"d1","decision":"x","rationale":"r","decision_class":"R1","affected_artifacts":["other.md"],"decided_at":"2026-10-19T00:00:00Z"}]}
EOF
run python3 "$SCRIPTS/detect-conflict.py" "$TMP/ca.json" "$TMP/cd-none.json" --type-registry "$TMP/reg.json"
check "no overlap" 0 "$LAST_CODE"

echo "=== 3. contract-revalidate.sh ==="
cat > "$TMP/rep-none.json" <<'EOF'
{"provider_semver":"1.2.0","consumer_semver":"1.2.0","diff_class":"none","changes":[]}
EOF
run "$SCRIPTS/contract-revalidate.sh" --pinned-ref "c@1.2.0" --pinned-fingerprint "contract:1.2.0:abc12345" --returned-fingerprint "contract:1.2.0:abc12345" --compat-report "$TMP/rep-none.json"
check "none=accept" 0 "$LAST_CODE"
cat > "$TMP/rep-minor.json" <<'EOF'
{"provider_semver":"1.3.0","consumer_semver":"1.3.0","diff_class":"minor","changes":["added field"]}
EOF
run "$SCRIPTS/contract-revalidate.sh" --pinned-ref "c@1.2.0" --pinned-fingerprint "contract:1.2.0:abc12345" --returned-fingerprint "contract:1.3.0:def67890" --compat-report "$TMP/rep-minor.json"
check "minor=revalidate" 30 "$LAST_CODE"
cat > "$TMP/rep-major.json" <<'EOF'
{"provider_semver":"2.0.0","consumer_semver":"2.0.0","diff_class":"major","changes":["removed field"]}
EOF
run "$SCRIPTS/contract-revalidate.sh" --pinned-ref "c@1.2.0" --pinned-fingerprint "contract:1.2.0:abc12345" --returned-fingerprint "contract:2.0.0:aaa00001" --compat-report "$TMP/rep-major.json"
check "major=rework" 31 "$LAST_CODE"
run "$SCRIPTS/contract-revalidate.sh" --pinned-ref "c@1.2.0" --pinned-fingerprint "contract:1.2.0:abc12345" --returned-fingerprint "contract:1.3.0:def67890" --compat-report "$TMP/missing.json"
check "missing report" 32 "$LAST_CODE"
run "$SCRIPTS/contract-revalidate.sh" --pinned-ref "c@1.2.0" --pinned-fingerprint "contract:1.2.0:abc12345" --returned-fingerprint "contract:2.0.0:aaa00001" --compat-report "$TMP/rep-none.json"
check "semver line cross forces major" 31 "$LAST_CODE"

echo "=== 4. attention-stall.sh ==="
NOW="2026-10-19T12:00:00Z"
ATT_3STALE='[
 {"id":"a1","status":"open","opened_at":"2026-10-19T09:00:00Z","due_at":"2026-10-19T10:00:00Z","votes":[]},
 {"id":"a2","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T11:00:00Z","votes":[]},
 {"id":"a3","status":"open","opened_at":"2026-10-19T11:00:00Z","due_at":"2026-10-19T11:30:00Z","votes":[]}]'
ATT_1FRESH='[{"id":"a1","status":"open","opened_at":"2026-10-19T11:00:00Z","due_at":"2026-10-19T13:00:00Z","votes":[]}]'
ATT_HUMAN='[
 {"id":"a1","status":"resolved","opened_at":"2026-10-19T09:00:00Z","due_at":"2026-10-19T10:00:00Z","resolved_at":"2026-10-19T11:00:00Z","resolved_by":"human","votes":[]},
 {"id":"a2","status":"open","opened_at":"2026-10-19T08:00:00Z","due_at":"2026-10-19T09:00:00Z","votes":[]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$ATT_3STALE" "$TMP/m3.json"
run "$SCRIPTS/attention-stall.sh" --task-meta "$TMP/m3.json" --now "$NOW"; check "3 stale=freeze" 41 "$LAST_CODE"
python3 -c "import json;json.dump({'task_id':'t1','decision_status':'open','attention':$ATT_3STALE[:2]},open('$TMP/m2.json','w'))"
run "$SCRIPTS/attention-stall.sh" --task-meta "$TMP/m2.json" --now "$NOW"; check "2 stale=escalate" 40 "$LAST_CODE"
python3 -c "import json;json.dump({'task_id':'t1','decision_status':'open','attention':$ATT_1FRESH},open('$TMP/m1.json','w'))"
run "$SCRIPTS/attention-stall.sh" --task-meta "$TMP/m1.json" --now "$NOW"; check "1 fresh=watch" 0 "$LAST_CODE"
python3 -c "import json;json.dump({'task_id':'t1','decision_status':'open','attention':$ATT_HUMAN},open('$TMP/mh.json','w'))"
run "$SCRIPTS/attention-stall.sh" --task-meta "$TMP/mh.json" --now "$NOW"; check "human response resets" 0 "$LAST_CODE"
run "$SCRIPTS/attention-stall.sh" --task-meta "$TMP/nope.json" --now "$NOW"; check "meta missing" 42 "$LAST_CODE"

echo "=== 5. verification-mismatch-window.sh ==="
MM_OPEN='[{"criterion_id":"c1","opened_at":"2026-10-19T11:00:00Z","window_hours":24,"status":"open"}]'
MM_EXPIRED='[{"criterion_id":"c1","opened_at":"2026-10-18T00:00:00Z","window_hours":24,"status":"open"}]'
MM_3R='[{"criterion_id":"c1","opened_at":"2026-10-19T09:00:00Z","window_hours":24,"status":"expired"},
        {"criterion_id":"c1","opened_at":"2026-10-19T10:00:00Z","window_hours":24,"status":"expired"},
        {"criterion_id":"c1","opened_at":"2026-10-19T11:00:00Z","window_hours":24,"status":"open"}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"verification_mismatch\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$MM_OPEN" "$TMP/mm1.json"
run "$SCRIPTS/verification-mismatch-window.sh" --task-meta "$TMP/mm1.json" --now "$NOW"; check "open young=none" 0 "$LAST_CODE"
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"verification_mismatch\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$MM_EXPIRED" "$TMP/mm2.json"
run "$SCRIPTS/verification-mismatch-window.sh" --task-meta "$TMP/mm2.json" --now "$NOW"; check "expired=50" 50 "$LAST_CODE"
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"verification_mismatch\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$MM_3R" "$TMP/mm3.json"
run "$SCRIPTS/verification-mismatch-window.sh" --task-meta "$TMP/mm3.json" --now "$NOW"; check "3 rounds=freeze" 51 "$LAST_CODE"
run "$SCRIPTS/verification-mismatch-window.sh" --task-meta "$TMP/nope.json" --now "$NOW"; check "meta missing" 52 "$LAST_CODE"

echo "=== 6. saga-compensate.py ==="
cat > "$TMP/event.json" <<'EOF'
{"event_id":"ev1","task_id":"t1","from_class":"R4","to_class":"R1","detected_at":"2026-10-19T11:00:00Z",
 "reason":"mismatch detected","affected_op_ids":["op1","op2"]}
EOF
cat > "$TMP/graph.json" <<'EOF'
{"nodes":[{"id":"n1","op_ids":["op1"]},{"id":"n2","op_ids":["op2"]}],"edges":[["n1","n2"]]}
EOF
cat > "$TMP/fops.json" <<'EOF'
[{"op_id":"op1","operation":"write_file","inputs":{"p":"a"},"executed_at":"2026-10-19T10:00:00Z","committed":true,"external_side_effect":false,"reversible":true,"expected_state_after":"a written"},
 {"op_id":"op2","operation":"run_build","inputs":{"p":"a"},"executed_at":"2026-10-19T10:30:00Z","committed":false,"external_side_effect":false,"reversible":true,"expected_state_after":"built"}]
EOF
run python3 "$SCRIPTS/saga-compensate.py" --task-id t1 --class-mismatch-event "$TMP/event.json" --dependency-graph "$TMP/graph.json" --forward-ops "$TMP/fops.json" --out "$TMP/saga/c.json"
check "compensate ok" 0 "$LAST_CODE"
grep -q '"rollback_possible": true' <<<"$LAST_OUT" && echo "ok   rollback_possible=true" && PASS=$((PASS+1)) || { echo "FAIL rollback_possible"; FAIL=$((FAIL+1)); FAILED_CASES+=("saga rollback_possible"); }
grep -q '"reclassify_to": "R1"' <<<"$LAST_OUT" && echo "ok   reclassify R1" && PASS=$((PASS+1)) || { echo "FAIL reclassify"; FAIL=$((FAIL+1)); FAILED_CASES+=("saga reclassify"); }
# 幂等命中
run python3 "$SCRIPTS/saga-compensate.py" --task-id t1 --class-mismatch-event "$TMP/event.json" --dependency-graph "$TMP/graph.json" --forward-ops "$TMP/fops.json" --out "$TMP/saga/c.json"
check "idempotent hit" 0 "$LAST_CODE"
grep -q '"idempotent_hit": true' <<<"$LAST_OUT" && echo "ok   idempotent_hit" && PASS=$((PASS+1)) || { echo "FAIL idempotent_hit"; FAIL=$((FAIL+1)); FAILED_CASES+=("saga idempotent"); }
# 不可逆外部副作用 → 60
cat > "$TMP/fops-irr.json" <<'EOF'
[{"op_id":"op1","operation":"publish","inputs":{"p":"a"},"executed_at":"2026-10-19T10:00:00Z","committed":true,"external_side_effect":true,"reversible":false,"expected_state_after":"published"},
 {"op_id":"op2","operation":"run_build","inputs":{"p":"a"},"executed_at":"2026-10-19T10:30:00Z","committed":false,"external_side_effect":false,"reversible":true,"expected_state_after":"built"}]
EOF
run python3 "$SCRIPTS/saga-compensate.py" --task-id t1 --class-mismatch-event "$TMP/event.json" --dependency-graph "$TMP/graph.json" --forward-ops "$TMP/fops-irr.json" --out "$TMP/saga/c2.json"
check "committed irreversible external=60" 60 "$LAST_CODE"
run python3 "$SCRIPTS/saga-compensate.py" --task-id t1 --class-mismatch-event "$TMP/event.json" --dependency-graph "$TMP/nope.json" --forward-ops "$TMP/fops.json"
check "graph missing=61" 61 "$LAST_CODE"
cat > "$TMP/fops-gap.json" <<'EOF'
[{"op_id":"op1","operation":"write_file","inputs":{"p":"a"},"executed_at":"2026-10-19T10:00:00Z","committed":true,"external_side_effect":false,"reversible":true,"expected_state_after":"a written"}]
EOF
run python3 "$SCRIPTS/saga-compensate.py" --task-id t1 --class-mismatch-event "$TMP/event.json" --dependency-graph "$TMP/graph.json" --forward-ops "$TMP/fops-gap.json"
check "coverage gap=62" 62 "$LAST_CODE"

echo "=== 7. consistency-check.py ==="
cat > "$TMP/crit.json" <<'EOF'
[{"criterion_id":"k1","description":"error grouping","structured":{"field":"error_grouping","allowed_values":["http_status"],"forbidden_values":["business_type"]}}]
EOF
cat > "$TMP/r6-ok.json" <<'EOF'
{"text":"group by http status","structured":{"error_grouping":"http_status"}}
EOF
cat > "$TMP/r6-bad.json" <<'EOF'
{"text":"group by business type","structured":{"error_grouping":"business_type"}}
EOF
cat > "$TMP/r6-free.json" <<'EOF'
{"text":"we will group errors somehow, TBD"}
EOF
IH=$(python3 -c "
import hashlib
h=hashlib.sha256()
for p in ['$TMP/r6-free.json','$TMP/crit.json']:
    h.update(open(p,'rb').read())
print(h.hexdigest()[:16])")
cat > "$TMP/llm-neutral.json" <<EOF
{"input_hash":"$IH","contradict":false,"criterion_id":"k1","reason":"无法判定"}
EOF
cat > "$TMP/llm-contradict.json" <<EOF
{"input_hash":"$IH","contradict":true,"criterion_id":"k1","reason":"按业务类型分组违反 HTTP 分组锁定"}
EOF
cat > "$TMP/llm-stale.json" <<'EOF'
{"input_hash":"deadbeef","contradict":true,"criterion_id":"k1","reason":"x"}
EOF
run python3 "$SCRIPTS/consistency-check.py" --r6-response "$TMP/r6-ok.json" --locked-criteria "$TMP/crit.json"
check "structured consistent=0" 0 "$LAST_CODE"
run python3 "$SCRIPTS/consistency-check.py" --r6-response "$TMP/r6-bad.json" --locked-criteria "$TMP/crit.json"
check "forbidden value=70" 70 "$LAST_CODE"
run python3 "$SCRIPTS/consistency-check.py" --r6-response "$TMP/r6-free.json" --locked-criteria "$TMP/crit.json" --mode strict
check "unstructured strict=71" 71 "$LAST_CODE"
run python3 "$SCRIPTS/consistency-check.py" --r6-response "$TMP/r6-free.json" --locked-criteria "$TMP/crit.json" --llm-result "$TMP/llm-neutral.json"
check "llm neutral=71" 71 "$LAST_CODE"
run python3 "$SCRIPTS/consistency-check.py" --r6-response "$TMP/r6-free.json" --locked-criteria "$TMP/crit.json" --llm-result "$TMP/llm-contradict.json"
check "llm contradict=70" 70 "$LAST_CODE"
run python3 "$SCRIPTS/consistency-check.py" --r6-response "$TMP/r6-free.json" --locked-criteria "$TMP/crit.json" --llm-result "$TMP/llm-stale.json"
check "llm stale hash=71" 71 "$LAST_CODE"

echo "=== 8. aggregate-vote.sh ==="
AV_PASS='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":2.0,"choice":"approve","received_at":"2026-10-19T10:30:00Z"},
          {"user":"u2","weight":1.0,"choice":"defer","received_at":"2026-10-19T10:40:00Z"}]}]'
AV_REJECT='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":1.0,"choice":"approve","received_at":"2026-10-19T10:30:00Z"},
          {"user":"u2","weight":3.0,"choice":"reject","received_at":"2026-10-19T10:40:00Z"}]}]'
AV_TIE='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":1.0,"choice":"approve","received_at":"2026-10-19T10:30:00Z"},
          {"user":"u2","weight":1.0,"choice":"reject","received_at":"2026-10-19T10:40:00Z"}]}]'
AV_TO='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T11:00:00Z","reversible":false,"rule":"R5","locker":"u1","votes":[]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_PASS" "$TMP/av1.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/av1.json" --decision-id d1 --rule R2 --now "$NOW"; check "pass" 0 "$LAST_CODE"
grep -q '"outcome": "pass"' <<<"$LAST_OUT" && echo "ok   outcome=pass" && PASS=$((PASS+1)) || { echo "FAIL outcome pass"; FAIL=$((FAIL+1)); FAILED_CASES+=("av pass outcome"); }
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_REJECT" "$TMP/av2.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/av2.json" --decision-id d1 --rule R2 --now "$NOW"; check "reject" 0 "$LAST_CODE"
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_TIE" "$TMP/av3.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/av3.json" --decision-id d1 --rule R2 --now "$NOW"; check "tie=80" 80 "$LAST_CODE"
grep -q '"next": "escalate"' <<<"$LAST_OUT" && echo "ok   tie next=escalate" && PASS=$((PASS+1)) || { echo "FAIL tie escalate"; FAIL=$((FAIL+1)); FAILED_CASES+=("tie escalate"); }
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_TO" "$TMP/av4.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/av4.json" --decision-id d1 --rule R5 --now "$NOW"; check "R5 irreversible timeout=81" 81 "$LAST_CODE"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/nope.json" --decision-id d1 --rule R2 --now "$NOW"; check "meta missing=82" 82 "$LAST_CODE"
# 幂等：--out 写后再跑
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_PASS" "$TMP/av5.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/av5.json" --decision-id d1 --rule R2 --now "$NOW" --out "$TMP/agg/d1.R2.json"
check "first write=0" 0 "$LAST_CODE"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/av5.json" --decision-id d1 --rule R2 --now "$NOW" --out "$TMP/agg/d1.R2.json"
check "idempotent out=0" 0 "$LAST_CODE"
grep -q '"idempotent_hit": true' <<<"$LAST_OUT" && echo "ok   agg idempotent_hit" && PASS=$((PASS+1)) || { echo "FAIL agg idempotent"; FAIL=$((FAIL+1)); FAILED_CASES+=("agg idempotent"); }

echo "=== 9. timer-derive.sh ==="
TD='{"task_id":"t1","dispatched_at":"2026-10-19T10:00:00Z","completed_at":null,
 "attention":[{"id":"a1","status":"open","opened_at":"2026-10-19T11:00:00Z","due_at":"2026-10-19T12:00:00Z","votes":[]}],
 "verification_mismatch":[{"criterion_id":"c1","opened_at":"2026-10-19T11:00:00Z","window_hours":24,"status":"open"}]}'
python3 -c "import json,sys;json.dump(json.loads(sys.argv[1]),open(sys.argv[2],'w'))" "$TD" "$TMP/td.json"
run "$SCRIPTS/timer-derive.sh" --task-meta "$TMP/td.json"
check "timer derive ok" 0 "$LAST_CODE"
for n in "attention-due:a1" "mismatch-due:c1:0" "staleness-alert" "stale-cleanup"; do
  grep -q "$n" <<<"$LAST_OUT" && echo "ok   timer $n" && PASS=$((PASS+1)) || { echo "FAIL timer $n"; FAIL=$((FAIL+1)); FAILED_CASES+=("timer $n"); }
done
python3 -c "import json,sys;json.dump({'task_id':'t2','attention':[]},open(sys.argv[1],'w'))" "$TMP/td2.json"
run "$SCRIPTS/timer-derive.sh" --task-meta "$TMP/td2.json"
check "empty meta=0" 0 "$LAST_CODE"
run "$SCRIPTS/timer-derive.sh" --task-meta "$TMP/nope.json"
check "meta missing=90" 90 "$LAST_CODE"

echo "=== 10. PR-3 断言补全 ==="
# 断言值均实测自 core/scripts/ 与 core/schemas/ 当前输出（零 LLM，python3 标准库 only）
SCHEMAS="$(cd "$(dirname "$0")/../../core/schemas" && pwd)"

# 10.1 R5 锁定者迟到降权（B-4：权重 2.0→1.0，非默认同意）
AV_R5DEMO='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R5","locker":"u1",
 "votes":[{"user":"u1","weight":2.0,"choice":"approve","received_at":"2026-10-19T15:00:00Z"}]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_R5DEMO" "$TMP/pr3-1.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/pr3-1.json" --decision-id d1 --rule R5 --now "2026-10-19T16:00:00Z"
check "R5 late locker=0" 0 "$LAST_CODE"
grep -q '"demoted": true' <<<"$LAST_OUT" && echo "ok   R5 demoted=true" && PASS=$((PASS+1)) || { echo "FAIL R5 demoted"; FAIL=$((FAIL+1)); FAILED_CASES+=("R5 demoted"); }
grep -q '"weight": 1.0' <<<"$LAST_OUT" && echo "ok   R5 weight demoted 1.0" && PASS=$((PASS+1)) || { echo "FAIL R5 weight"; FAIL=$((FAIL+1)); FAILED_CASES+=("R5 weight"); }
grep -q '"approve": 1.0' <<<"$LAST_OUT" && echo "ok   R5 sums approve=1.0" && PASS=$((PASS+1)) || { echo "FAIL R5 sums"; FAIL=$((FAIL+1)); FAILED_CASES+=("R5 sums"); }

# 10.2 R5 可逆窗口超时 = wait（非默认同意；对比已有不可逆 81/block 用例）
AV_R5TO='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T11:00:00Z","reversible":true,"rule":"R5","locker":"u1","votes":[]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_R5TO" "$TMP/pr3-2.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/pr3-2.json" --decision-id d1 --rule R5 --now "2026-10-19T18:00:00Z"
check "R5 reversible timeout=0" 0 "$LAST_CODE"
grep -q '"outcome": "timeout"' <<<"$LAST_OUT" && echo "ok   R5 timeout outcome" && PASS=$((PASS+1)) || { echo "FAIL R5 timeout"; FAIL=$((FAIL+1)); FAILED_CASES+=("R5 timeout"); }
grep -q '"next": "wait"' <<<"$LAST_OUT" && echo "ok   R5 timeout next=wait" && PASS=$((PASS+1)) || { echo "FAIL R5 wait"; FAIL=$((FAIL+1)); FAILED_CASES+=("R5 wait"); }

# 10.3 R2 defer 记 dissent（不计分母；1:1 平 → 80）
AV_R2DEFER='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":1.0,"choice":"approve","received_at":"2026-10-19T10:10:00Z"},
          {"user":"u2","weight":5.0,"choice":"defer","received_at":"2026-10-19T10:20:00Z"},
          {"user":"u3","weight":1.0,"choice":"reject","received_at":"2026-10-19T10:30:00Z"}]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_R2DEFER" "$TMP/pr3-3.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/pr3-3.json" --decision-id d1 --rule R2 --now "$NOW"
check "R2 defer tie=80" 80 "$LAST_CODE"
grep -q '"outcome": "tie"' <<<"$LAST_OUT" && echo "ok   defer tie outcome" && PASS=$((PASS+1)) || { echo "FAIL defer tie"; FAIL=$((FAIL+1)); FAILED_CASES+=("defer tie"); }
grep -q '"abstain": 5.0' <<<"$LAST_OUT" && echo "ok   defer sums abstain=5.0" && PASS=$((PASS+1)) || { echo "FAIL defer abstain"; FAIL=$((FAIL+1)); FAILED_CASES+=("defer abstain"); }
grep -q '"reason": "abstain"' <<<"$LAST_OUT" && echo "ok   defer dissent=abstain" && PASS=$((PASS+1)) || { echo "FAIL defer dissent"; FAIL=$((FAIL+1)); FAILED_CASES+=("defer dissent"); }
grep -q '"counted": false' <<<"$LAST_OUT" && echo "ok   defer not in denominator" && PASS=$((PASS+1)) || { echo "FAIL defer counted"; FAIL=$((FAIL+1)); FAILED_CASES+=("defer counted"); }

# 10.4 signal_event.schema.json（stdlib 手写校验：required + event_type 封闭清单；取值读自 schema 文件，不硬编码第二份清单）
cat > "$TMP/validate-signal.py" <<'EOF'
import json, sys
schema = json.load(open(sys.argv[1]))
doc = json.load(open(sys.argv[2]))
errs = []
for k in schema.get("required", []):
    if k not in doc:
        errs.append("missing required: " + k)
if "event_type" in doc and doc["event_type"] not in schema["properties"]["event_type"]["enum"]:
    errs.append("event_type not in closed list")
if errs:
    print("; ".join(errs))
    sys.exit(1)
print("ok")
EOF
python3 - "$SCHEMAS/signal_event.schema.json" "$TMP/sig-valid.json" <<'EOF'
import json, sys
schema = json.load(open(sys.argv[1]))
doc = {"event_id":"e1","task_id":"t1","event_type":schema["properties"]["event_type"]["enum"][0],
       "is_signal":True,"ref":"art:1","fingerprint":"fp:abc123","occurred_at":"2026-10-19T12:00:00Z"}
json.dump(doc, open(sys.argv[2], "w"))
EOF
run python3 "$TMP/validate-signal.py" "$SCHEMAS/signal_event.schema.json" "$TMP/sig-valid.json"
check "signal valid=0" 0 "$LAST_CODE"
python3 - "$SCHEMAS/signal_event.schema.json" "$TMP/sig-nosig.json" <<'EOF'
import json, sys
schema = json.load(open(sys.argv[1]))
doc = {"event_id":"e1","task_id":"t1","event_type":schema["properties"]["event_type"]["enum"][0],
       "ref":"art:1","fingerprint":"fp:abc123","occurred_at":"2026-10-19T12:00:00Z"}
json.dump(doc, open(sys.argv[2], "w"))
EOF
run python3 "$TMP/validate-signal.py" "$SCHEMAS/signal_event.schema.json" "$TMP/sig-nosig.json"
check "signal missing is_signal=1" 1 "$LAST_CODE"
python3 - "$SCHEMAS/signal_event.schema.json" "$TMP/sig-fake.json" <<'EOF'
import json, sys
schema = json.load(open(sys.argv[1]))
doc = {"event_id":"e1","task_id":"t1","event_type":"SIG-FAKE",
       "is_signal":True,"ref":"art:1","fingerprint":"fp:abc123","occurred_at":"2026-10-19T12:00:00Z"}
json.dump(doc, open(sys.argv[2], "w"))
EOF
run python3 "$TMP/validate-signal.py" "$SCHEMAS/signal_event.schema.json" "$TMP/sig-fake.json"
check "signal event_type not in list=1" 1 "$LAST_CODE"

# 10.5 scorecard.schema.json（schema 级载体断言：critic_model_family 可选，单 critic 缺省合法）
cat > "$TMP/validate-scorecard.py" <<'EOF'
import json, sys
schema = json.load(open(sys.argv[1]))
doc = json.load(open(sys.argv[2]))
errs = []
for k in schema.get("required", []):
    if k not in doc:
        errs.append("missing required: " + k)
if "verdict" in doc and doc["verdict"] not in schema["properties"]["verdict"]["enum"]:
    errs.append("verdict not in enum")
item_required = schema["properties"]["items"]["items"]["required"]
for i, it in enumerate(doc.get("items", [])):
    for k in item_required:
        if k not in it:
            errs.append("items[%d] missing required: %s" % (i, k))
if errs:
    print("; ".join(errs))
    sys.exit(1)
print("ok")
EOF
cat > "$TMP/sc-valid.json" <<'EOF'
{"task_id":"t1","reviewer":"r2","verdict":"pass","critic_model_family":"family-a",
 "items":[{"id":"C1","what":"check a exists","command":"ls a","expected":"a exists","status":"pass"}]}
EOF
run python3 "$TMP/validate-scorecard.py" "$SCHEMAS/scorecard.schema.json" "$TMP/sc-valid.json"
check "scorecard valid with family=0" 0 "$LAST_CODE"
python3 -c "import json;d=json.load(open('$TMP/sc-valid.json'));d.pop('critic_model_family');json.dump(d,open('$TMP/sc-nofamily.json','w'))"
run python3 "$TMP/validate-scorecard.py" "$SCHEMAS/scorecard.schema.json" "$TMP/sc-nofamily.json"
check "scorecard no critic_model_family=0" 0 "$LAST_CODE"
python3 -c "import json;d=json.load(open('$TMP/sc-valid.json'));d.pop('critic_model_family');d.pop('verdict');json.dump(d,open('$TMP/sc-noverdict.json','w'))"
run python3 "$TMP/validate-scorecard.py" "$SCHEMAS/scorecard.schema.json" "$TMP/sc-noverdict.json"
check "scorecard missing verdict=1" 1 "$LAST_CODE"

# 10.7 reject 时少数 approve 记 dissent（minority）
AV_R2MIN='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":1.0,"choice":"approve","received_at":"2026-10-19T10:10:00Z"},
          {"user":"u2","weight":3.0,"choice":"reject","received_at":"2026-10-19T10:20:00Z"}]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_R2MIN" "$TMP/pr3-7.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/pr3-7.json" --decision-id d1 --rule R2 --now "$NOW"
check "reject minority=0" 0 "$LAST_CODE"
grep -q '"outcome": "reject"' <<<"$LAST_OUT" && echo "ok   reject outcome" && PASS=$((PASS+1)) || { echo "FAIL reject outcome"; FAIL=$((FAIL+1)); FAILED_CASES+=("reject outcome"); }
grep -q '"user": "u1"' <<<"$LAST_OUT" && echo "ok   dissent user u1" && PASS=$((PASS+1)) || { echo "FAIL dissent u1"; FAIL=$((FAIL+1)); FAILED_CASES+=("dissent u1"); }
grep -q '"reason": "minority"' <<<"$LAST_OUT" && echo "ok   dissent reason minority" && PASS=$((PASS+1)) || { echo "FAIL dissent minority"; FAIL=$((FAIL+1)); FAILED_CASES+=("dissent minority"); }

# 10.8 blocked 态 defer 计入分母（B-5：defer 把 would-be pass 翻成 tie → 80）
AV_B5='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":1.0,"choice":"approve","received_at":"2026-10-19T10:10:00Z"},
          {"user":"u2","weight":5.0,"choice":"defer","received_at":"2026-10-19T10:20:00Z"}]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"blocked\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_B5" "$TMP/pr3-8.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/pr3-8.json" --decision-id d1 --rule R2 --now "$NOW"
check "blocked defer counted=80" 80 "$LAST_CODE"
grep -q '"blocked_no_abstain": true' <<<"$LAST_OUT" && echo "ok   blocked_no_abstain=true" && PASS=$((PASS+1)) || { echo "FAIL b5 flag"; FAIL=$((FAIL+1)); FAILED_CASES+=("b5 flag"); }
grep -q '"counted": true' <<<"$LAST_OUT" && echo "ok   defer counted=true" && PASS=$((PASS+1)) || { echo "FAIL b5 counted"; FAIL=$((FAIL+1)); FAILED_CASES+=("b5 counted"); }
grep -q '"abstain": 5.0' <<<"$LAST_OUT" && echo "ok   b5 abstain in denominator" && PASS=$((PASS+1)) || { echo "FAIL b5 abstain"; FAIL=$((FAIL+1)); FAILED_CASES+=("b5 abstain"); }
grep -q '"reason": "abstain-counted(blocked)"' <<<"$LAST_OUT" && echo "ok   b5 dissent abstain-counted" && PASS=$((PASS+1)) || { echo "FAIL b5 dissent"; FAIL=$((FAIL+1)); FAILED_CASES+=("b5 dissent"); }

# 10.9 非法 choice = 82
AV_ILLEGAL='[{"id":"d1","status":"open","opened_at":"2026-10-19T10:00:00Z","due_at":"2026-10-19T14:00:00Z","reversible":true,"rule":"R2",
 "votes":[{"user":"u1","weight":1.0,"choice":"maybe","received_at":"2026-10-19T10:10:00Z"}]}]'
python3 -c "import json,sys;json.dump({\"task_id\":\"t1\",\"decision_status\":\"open\",\"attention\":json.loads(sys.argv[1])},open(sys.argv[2],\"w\"))" "$AV_ILLEGAL" "$TMP/pr3-9.json"
run "$SCRIPTS/aggregate-vote.sh" --task-meta "$TMP/pr3-9.json" --decision-id d1 --rule R2 --now "$NOW"
check "illegal choice=82" 82 "$LAST_CODE"

echo
echo "=================================================="
echo "PASS=$PASS FAIL=$FAIL"
if [[ $FAIL -gt 0 ]]; then
  printf 'failed: %s\n' "${FAILED_CASES[@]}"
  exit 1
fi
echo "ALL SCRIPT TESTS GREEN"
