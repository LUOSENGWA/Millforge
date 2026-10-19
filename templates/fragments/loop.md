## Loop 原语（精简装载版 · 全文 = 协议 §10-LOOP）

**定位**：goal 锁定 → 迭代（派发→独立验证）→ 达成?停:重规划，预算内运行。Loop 包含 task 不等同 task——迭代内 task 仍走 R1-R6/NMH/critic。

**loop_spec（人锁，执行体不得自启/扩预算）**：goal_ref（已人锁 spec）/ stop_condition（**外部可判定二元条件**，不得是"模型声明完成"）/ iteration_budget{max_iterations, max_human_touch（goal_ref 聚合）} / convergence_rule{no_progress_window, progress_signal（**幅度感知**：acceptance_delta/score_delta——不是"有变化"）} / re_plan_rule{max_replans} / termination_action[]。

**五阶段（CAP-STATE 驱动，driver 幂等派生）**：
```
DISPATCH（fresh spawn，X4 时限）→ EXECUTE（结构化返回；self_reported_status 是数据非结论）
→ VERIFY（critic 独立验收，不是父自验）→ JUDGE（achieved→停 / 有预算有进展→重规划 /
无进展→stalled+升级 / 预算尽→exhausted+升级 / undecidable→R6 升级）→ RECORD（append 历史，不进 driver 上下文）
```

**Driver 纪律**（你是 loop 范围的 accountable orchestrator）：
1. 权威状态只在 CAP-STATE——你每次唤醒**幂等重推导** next_action，不记增量、不依赖会话记忆
2. 你**不得自行判定 stop_condition 达成**（达成 = 谓词/critic 写入后才读）
3. native 上下文只留迭代摘要 {index, verdict, progress_signal, key_refs[]}；全量产物走 review spawn
4. 你崩溃不影响权威状态（调度器继续触发 + 升级）

**反绕过（硬规则）**：
- 反碎片化：同 goal_ref ≥2 task 有 artifact 依赖 → 必须共享 loop 容器；simple 档需 fragmentation_justification
- 反灌水：单次变化量 < min_substantive_change → low_yield 降权；连续 low_yield 计入 no_progress_window
- 跨团队回流（仅 single_user）：≤{{max_reflow}} 次共享预算池；**连续 2 次回流同 criterion 同指纹 = semantic stall 立即终止**（即使预算未耗尽）

**档位**：simple 不启用（局部重试 ≤3→升级）｜ standard 条件启用（多轮才收敛）｜ full 默认（goal 需迭代）+ 跨团队反馈环强制。
