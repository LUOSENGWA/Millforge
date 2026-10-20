# 不变式：Loop 状态机（第 14 原语）

> §10-LOOP 的可检部分。loop 权威状态只存在于 CAP-STATE（task_meta.loop_state）；driver 不维护独立计数器。

## 1. 五阶段状态机

```
 DISPATCH ──spawn 派发成功──▶ EXECUTE
    ▲                          │ X4 有界返回（结构化结果 或 bounded_failure）
    │                          ▼
 RE-PLAN ◀──JUDGE: not_achieved + 有预算 + 有进展── VERIFY（critic 独立验收）
    │                          │
    │                          ├──JUDGE: achieved──▶ STOPPED(success)
    │                          ├──JUDGE: 无进展（convergence_rule）──▶ STOPPED(stalled)
    │                          ├──JUDGE: 预算耗尽──▶ STOPPED(exhausted)
    │                          └──JUDGE: undecidable──▶ 升级（R6）→ 恢复后重 JUDGE
    │
    └── RE-PLAN 超 max_replans ──▶ STOPPED(exhausted)
```

RECORD 是每轮 JUDGE 后的落盘动作（非独立阶段）：{iteration_index, result_refs[], critic_verdict, progress_signal, budget_consumed} append 入 loop history。

## 2. 不变式断言

1. **I-L1** 权威状态单点：loop 的 current_iteration / budget_remaining / phase / last_verdict 只在 CAP-STATE；执行体上下文不是权威来源（driver 唤醒 = 读 + 派生，不记增量）
2. **I-L2**（幂等）同 iteration 同输入重复请求 → ALREADY_RESOLVED（幂等键 = hash(loop_id + iteration_index + action_type + input_fingerprint)）；跨 iteration 同输入 = 不同请求 + "重复输入"告警
3. **I-L3**（达成判定）STOPPED(success) 只能由 stop_condition 谓词/critic 写入 last_verdict=achieved 后派生；driver 不得自行判定达成
4. **I-L4**（有界）iteration_budget 人锁（max_iterations + max_human_touch）；执行体自启 loop / 扩大预算 = 协议违规（golden test 断言：无 human_lock 记录 → loop 不得创建）
5. **I-L5**（反碎片化）同一 goal_ref 下 ≥2 task 且 artifact 依赖链 → 必须共享 loop 容器；>3 个 simple task 互引 → suspected_loop_fragmentation 告警
6. **I-L6**（反灌水）progress_signal 幅度感知（acceptance_delta/score_delta 低于 min_score_delta = 无进展；纯格式变化不计）；连续 low_yield 计入 no_progress_window
7. **I-L7**（X4 依赖）loop 内所有 spawn 必须声明时限 + 有界返回（structured result 或 bounded_failure）；无 X4 的绑定上 loop 不得运行
8. **I-L8**（预算共享）跨团队回流消耗 iteration_budget 共享池（非免费重试）；默认 ≤2 完整回流（full 档人锁 ≤4）
9. **I-L9**（semantic stall）连续 2 次回流指向同一 criterion 且 evidence_fingerprint 无变化 → 立即终止升级（即使预算未耗尽）
10. **I-L10**（人触达聚合）max_human_touch 按 goal_ref 聚合整个 loop；re-plan 本身不触达人（仅 re-plan 需澄清时走 R6 计数）
11. **I-L11**（driver 缺席）driver 崩溃不影响权威状态；调度器继续触发；心跳超声明时限 → 升级；恢复后 driver 从 CAP-STATE 幂等重推导（不重放已记录动作）
12. **I-L12**（native 预算）driver 上下文只保留迭代摘要 {index, verdict, progress_signal, key_refs[]}；全量产物走 review spawn

## 3. 终止动作序（termination_action 有序执行）

| 终态 | 动作序列 |
|------|---------|
| success | emit_artifact → write_decision_record → （跨团队）通知 arbitrator 汇总 |
| exhausted | write_decision_record → escalate(accountable, reason=budget) |
| stalled | write_decision_record → escalate(accountable, reason=semantic_stall/no_progress) |

exhausted/stalled 的后续 = R1 处理（accountable 裁决：继续/终止/重新定义 goal）——不是自动继续。
