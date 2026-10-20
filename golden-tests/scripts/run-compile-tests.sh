#!/usr/bin/env bash
# millforge golden-tests/scripts/run-compile-tests.sh
# 编译器确定性回归（零 LLM）：
#   T1 确定性：同输入编译两次 → 除 provenance 时间戳外逐字节一致
#   T2 行硬门：全部角色 ≤ 预算（超 = 编译器必须 fail）
#   T3 占位符：编译物零残留 {{
#   T4 provenance：头注释含 instance_fp + fragments + recompile
#   T5 触发指针完整性：指针指向文件已部署
#   T6 Validate fail 路径：非法实例（双 accountable / multi_user+coordinator / 未注册域）必须 exit 2
#   T7 Budget fail 路径：预算改 1 行必须 fail（不截断）
#   T8 scrub 词表：编译物无生产专名
set -u
MF="$(cd "$(dirname "$0")/../.." && pwd)"
COMPILE="$MF/compiler/millforge-compile.py"
FIX="$MF/golden-tests/fixtures/example-biz-team.json"
TMP=$(mktemp -d)
PASS=0; FAIL=0; FAILED=()
ok()  { PASS=$((PASS+1)); echo "ok   $1"; }
bad() { FAIL=$((FAIL+1)); FAILED+=("$1"); echo "FAIL $1"; }

python3 "$COMPILE" compile "$FIX" --out "$TMP/a" >/dev/null 2>&1
python3 "$COMPILE" compile "$FIX" --out "$TMP/b" >/dev/null 2>&1

# T1 确定性（忽略 provenance 行：compiled 时间戳 + fragments 顺序不变但 sha 恒定 → 实际全一致，仅时间戳行允许差异）
STRIP='grep -v "compiled:"'
if diff <(cat "$TMP/a"/*.soul.md | eval $STRIP) <(cat "$TMP/b"/*.soul.md | eval $STRIP) >/dev/null 2>&1; then
  ok "T1 deterministic (two compiles byte-identical minus timestamp)"
else
  bad "T1 deterministic"
fi

# T2 行硬门
OVER=0
for f in "$TMP/a"/*.soul.md; do
  n=$(grep -c "" "$f")
  base=$(basename "$f" .soul.md)
  case "$base" in
    biz-coordinator) b=500 ;; biz-lead) b=250 ;; *) b=150 ;;
  esac
  if [ "$n" -gt "$b" ]; then OVER=1; echo "  over: $base $n > $b"; fi
done
[ $OVER -eq 0 ] && ok "T2 all roles within line budget" || bad "T2 line budget"

# T3 占位符零残留
R=$(grep -l "{{" "$TMP/a"/*.soul.md 2>/dev/null | wc -l)
[ "$R" -eq 0 ] && ok "T3 zero unresolved placeholders" || bad "T3 placeholders ($R files)"

# T4 provenance
P=$(grep -l "MILLFORGE-COMPILED" "$TMP/a"/*.soul.md | wc -l)
T=$(ls "$TMP/a"/*.soul.md | wc -l)
[ "$P" -eq "$T" ] && grep -q "instance_fp:" "$TMP/a/biz-analyst.soul.md" && grep -q "recompile:" "$TMP/a/biz-analyst.soul.md" \
  && ok "T4 provenance header complete" || bad "T4 provenance"

# T5 触发指针完整性
GAPS=0
for f in "$TMP/a"/*.soul.md; do
  while read -r p; do
    [ -f "$TMP/a/$p" ] || { GAPS=1; echo "  gap: $p"; }
  done < <(grep -oE '(fragments|spawn-specs)/[A-Za-z0-9._-]+\.md' "$f" | sort -u)
done
[ $GAPS -eq 0 ] && ok "T5 all trigger pointers deployed" || bad "T5 pointer gaps"

# T6 Validate fail 路径
python3 - "$FIX" "$TMP/bad1.json" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1])); d["roster"].append({"id":"x","role":"accountable","weight":1.0})
json.dump(d,open(sys.argv[2],"w"))
EOF
python3 "$COMPILE" validate "$TMP/bad1.json" >/dev/null 2>&1 && bad "T6a double accountable rejected" || ok "T6a double accountable rejected (exit!=0)"
python3 - "$FIX" "$TMP/bad2.json" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1])); d["mode"]="multi_user"
json.dump(d,open(sys.argv[2],"w"))
EOF
python3 "$COMPILE" validate "$TMP/bad2.json" >/dev/null 2>&1 && bad "T6b multi_user+coordinator rejected" || ok "T6b multi_user+coordinator rejected"
python3 - "$FIX" "$TMP/bad3.json" <<'EOF'
import json,sys
d=json.load(open(sys.argv[1])); d["roles"][2]["domains"].append("nonexistent-domain")
json.dump(d,open(sys.argv[2],"w"))
EOF
python3 "$COMPILE" validate "$TMP/bad3.json" >/dev/null 2>&1 && bad "T6c unregistered domain rejected" || ok "T6c unregistered domain rejected"

# T7 Budget fail 路径（不截断）
python3 "$COMPILE" compile "$FIX" --out "$TMP/over" --budget-override worker=10 >/dev/null 2>&1
RC=$?
if [ $RC -eq 4 ]; then ok "T7 over-budget fails with exit 4 (no truncation)"; else bad "T7 budget fail (exit=$RC)"; fi
if [ -f "$TMP/over/biz-analyst.soul.md" ]; then bad "T7b over-budget file must not be emitted"; else ok "T7b no truncated output emitted"; fi

# T8 scrub 词表（zh + en 双编译产物）
python3 "$COMPILE" compile "$MF/golden-tests/fixtures/bizmarket-team.json" --out "$TMP/a-en" --lang en >/dev/null 2>&1
SCRUB_WORDS="spawn_subagent|TeamHarness|MinIO|hiclaw|copaw|SGLang"
HITS=$( { grep -lE "$SCRUB_WORDS" "$TMP/a"/*.soul.md 2>/dev/null; grep -lE "$SCRUB_WORDS" "$TMP/a-en"/*.soul.md 2>/dev/null; } | wc -l)
[ "$HITS" -eq 0 ] && ok "T8 no runtime-specific names in compiled output (zh+en)" || bad "T8 scrub hits"

# T9 冻结基线 diff（编译确定性门：模板/片段/编译器变更 → 输出漂移必须显式更新基线）
# 支持 --freeze-baseline：重编译两 fixture 并刷新 baseline/（须人工审查 diff 后 commit）
FREEZE=0
for a in "$@"; do [ "$a" = "--freeze-baseline" ] && FREEZE=1; done
python3 "$COMPILE" compile "$MF/golden-tests/fixtures/bizmarket-team.json" --out "$TMP/c" >/dev/null 2>&1
BD=0
for pair in "example-biz-team:$TMP/a" "bizmarket-team:$TMP/c"; do
  name=${pair%%:*}; outdir=${pair#*:}
  BASE="$MF/golden-tests/baseline/$name"
  if [ $FREEZE -eq 1 ]; then
    mkdir -p "$BASE"
    for f in "$outdir"/*.soul.md; do cp "$f" "$BASE/"; done
    continue
  fi
  if [ ! -d "$BASE" ]; then BD=1; echo "  baseline missing: $name (freeze with review)"; continue; fi
  for f in "$BASE"/*.soul.md; do
    role=$(basename "$f" .soul.md)
    src="$outdir/$role.soul.md"
    if [ ! -f "$src" ]; then BD=1; echo "  missing compiled: $name/$role"; continue; fi
    if ! diff <(grep -v "compiled:" "$f") <(grep -v "compiled:" "$src") >/dev/null; then
      BD=1; echo "  drifted: $name/$role (re-freeze via --freeze-baseline with review)"
    fi
  done
done
if [ $FREEZE -eq 1 ]; then
  ok "T9 baseline re-frozen (review the diff before committing!)"
else
  [ $BD -eq 0 ] && ok "T9 frozen baseline unchanged (protocol regression: zero silent)" || bad "T9 baseline drift"
fi

# T10 生产溯源门（生产基线 5 SOUL 占位化副本 + 映射文档存在；映射缺失=协议内容丢失）
PB="$MF/golden-tests/fixtures/production-baseline"
NPB=$(ls "$PB"/*.soul.md 2>/dev/null | wc -l)
[ "$NPB" -eq 5 ] && [ -f "$MF/golden-tests/PRODUCTION-BASELINE.md" ] \
  && grep -q "重验规程" "$MF/golden-tests/PRODUCTION-BASELINE.md" \
  && ok "T10 production baseline (5 SOULs) + mapping doc present" || bad "T10 production baseline"

echo
echo "PASS=$PASS FAIL=$FAIL"
[ $FAIL -gt 0 ] && { printf 'failed: %s\n' "${FAILED[@]}"; exit 1; }
echo "ALL COMPILE TESTS GREEN"
