#!/usr/bin/env bash
# millforge golden-tests/scripts/run-contract-tests.sh
# M4 并行任务派发场景契约回归（零 LLM，纯数据断言）：
#   对 golden-tests/fixtures/parallel-9/ 种子（10 任务 state.json + 7 条 inbox 事件）
#   逐条断言 PD-1..PD-7 七不变式（bindings/agentteams/parallel-dispatch.md）
set -u
MF="$(cd "$(dirname "$0")/../.." && pwd)"

echo "=== M4 parallel-dispatch contract (fixtures/parallel-9) ==="
if python3 "$MF/golden-tests/tests/test_parallel_dispatch_contract.py"; then
  echo "ALL CONTRACT TESTS GREEN"
else
  echo "CONTRACT TESTS FAILED"
  exit 1
fi
