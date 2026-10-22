#!/usr/bin/env bash
# millforge golden-tests/scripts/run-contract-tests.sh
# 场景契约 + 条款静态检查回归（零 LLM，确定性）：
#   M4 并行任务派发场景契约：对 golden-tests/fixtures/parallel-9/ 种子
#      （10 任务 state.json + 7 条 inbox 事件）逐条断言 PD-1..PD-7 七不变式
#      （bindings/agentteams/parallel-dispatch.md）
#   M5 CAP-NOTIFY 分层条款：静态断言 09-GOVERNANCE §8 规范要素在位
#      （tier 声明 / human 3 行人话 / 失败态必须进 human tier / 禁 payload / 禁提问）
set -u
MF="$(cd "$(dirname "$0")/../.." && pwd)"

fail=0
echo "=== M4 parallel-dispatch contract (fixtures/parallel-9) ==="
python3 "$MF/golden-tests/tests/test_parallel_dispatch_contract.py" || fail=1

echo
echo "=== M5 notify-tier clause (09-GOVERNANCE §8, static) ==="
python3 "$MF/golden-tests/tests/test_notify_tier_clause.py" || fail=1

echo
if [ "$fail" -gt 0 ]; then
  echo "CONTRACT TESTS FAILED"
  exit 1
fi
echo "ALL CONTRACT TESTS GREEN"
