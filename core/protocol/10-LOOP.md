# Loop 原语（第 14 原语）

> v1.0 | 来源: 第七轮 Loop 专轮（全采纳含 4 处修正）
> **定位**：Loop 有自己的 spec（goal_ref/stop_condition/budget/convergence_rule）、自己的生命周期（迭代）、自己的 driver（accountable orchestrator）；它可以**包含** task，但不等同 task。
> Loop 是上层容器：迭代内的 task 仍走 R1-R6 决策聚合、NMH spec 锁定、critic 验收。Loop 只负责**在预算内重复调用这些机制，直到 stop_condition 达成或预算耗尽**。
> **为什么不是状态机扩展**：迭代不是生命周期阶段，是同一生命周期内的重复执行；扩态会污染任务状态机契约，"迭代中/执行中"区分对适配器无意义。

## 1. loop_spec

```
loop_spec = {
  loop_id:                     # CAP-STATE 生成的唯一标识
  goal_ref: CAP-STORE ref,     # 指向已人锁的 spec artifact（NMH 锁定）
  stop_condition: {            # 必须外部可判定的二元条件，不得是模型主观声明
    kind: "deterministic" | "rubric_threshold" | "composite",
    predicate_ref: CAP-STORE ref,   # 确定性谓词/评分卡引用
    threshold?: number            # rubric_threshold 时必填
  },
  iteration_budget: {
    max_iterations: int,       # 硬上限，必须由人锁定
    max_human_touch: int,      # 整个 loop 的人类触达上限（含 R6/NMH/mismatch），非每迭代
    max_total_spawns?: int,    # 迭代内 spawn 总数上限（可选）
    token_budget?: int         # 绑定层可声明（可选）
  },
  convergence_rule: {
    no_progress_window: int,   # 连续 N 次无进展 → 终止（独立于 max_iterations 的第二道刹车）
    progress_signal: "acceptance_delta" | "fingerprint_change" | "score_delta",
    stagnation_action: "freeze_escalate"   # 不允许"继续烧预算"
  },
  re_plan_rule: {
    enabled: bool,
    max_replans: int,          # 硬上限（通常 ≤ max_iterations/2）
    replan_trigger: "stop_condition_unreachable" | "verification_feedback"
  },
  termination_action: [        # 终止动作（有序）
    {action: "write_decision_record", ref: ...},
    {action: "escalate", to: "accountable", reason: ...},   # exhausted/stalled
    {action: "emit_artifact", ref: ...}                     # success
  ],
  protocol_version: string
}
```

**关键约束**：
- `stop_condition` **不得是"模型声明完成"**——模型可以提交完成声明，但只是候选，必须被外部谓词验证
- `iteration_budget` 必须由人锁定（NMH 或显式确认），执行者**不得自启 loop、不得扩大预算**（Loop 是预算放大器）
- `no_progress_window` 独立于 `max_iterations` 更早触发（迭代不单调改进，更多迭代不保证收敛）

## 2. 迭代五阶段（全部由 CAP-STATE 驱动）

```
1. DISPATCH：driver 从 CAP-STATE 读 loop 状态，构造本迭代 task spec
   （goal_ref + 上迭代 mismatch 证据 ref + 约束增量），
   经 CAP-SPAWN 派发 fresh 子执行单元（X1 硬隔离，不继承父历史）
2. EXECUTE：子执行单元在 X4 时限内返回结构化结果
   {artifact_refs[], decision_log_ref, self_reported_status}
   —— self_reported_status 是数据，不是验收结论
3. VERIFY：由 critic（独立于子执行单元）验收，不是父执行体自验
   —— 五条款"验证者 ≠ 声明者"在 loop 内同样适用
   判定: achieved / not_achieved / undecidable
4. JUDGE：driver 读 critic 结果 + 收敛信号，派生 next_action：
   - achieved → STOP(success)
   - not_achieved + 有预算 + 有进展 → RE-PLAN → 下一迭代
   - not_achieved + 有预算 + 无进展（命中 convergence_rule）→ STOP(stalled) + 升级
   - not_achieved + 预算耗尽 → STOP(exhausted) + 升级
   - undecidable → 升级（R6 attention），不自行判定
5. RECORD：driver 写 {iteration_index, result_refs[], critic_verdict,
   progress_signal, budget_consumed} 入 CAP-STATE + loop history（append-only）
   —— driver 不把迭代历史留在自己上下文
```

**re-plan spawn 的 context_refs**（四项缺一不可）：
```
[mismatch_evidence_ref,      # critic 本次反馈
 spec_ref,                   # 人锁 goal
 previous_artifact_ref,      # 上迭代产物（供参考非供复制）
 convergence_trajectory_ref] # 前 N 次进展信号序列（防重复无效路径）
```

## 3. Driver 语义

1. loop 权威状态**只存在于 CAP-STATE**（current_iteration, budget_remaining, convergence_trajectory, last_verdict, phase）——任何执行体上下文都不是权威来源
2. driver = 该 loop 范围的 **accountable orchestrator**（团队 loop → leader；跨团队 → arbitrator；单执行体局部 → 其父执行体）。身份由 CAP-ROSTER accountable 查询确定，**不由执行体自声明**
3. driver 每次唤醒从 CAP-STATE **幂等重推导** next_action——不依赖会话记忆、不维护独立计数器、重复唤醒产生相同结果
4. driver 崩溃/缺席不影响权威状态；CAP-TIMER 以持久化 next_check_at 兜底唤醒；缺席超声明时限 → 升级
5. driver **不得自行判定 stop_condition 达成**——达成判定来自谓词/critic 写入 CAP-STATE 后才被读取

**native 上下文预算（修正第六轮）**：driver 的 native 上下文只保留迭代摘要（{index, verdict, progress_signal, key_refs[]}），**默认不装载**完整产物；需看全量 → 派发 review spawn。

## 4. 触发档位

| 档位 | 启用规则 |
|------|---------|
| **simple** | **不启用**。局部重试走有界失败环（≤3 → 升级） |
| **standard** | **条件启用**：stop_condition 为 rubric_threshold 或多轮才收敛（如多文件并行后的集成验证）；纯确定性单次任务不启用 |
| **full** | **默认启用**（goal 需迭代达成时）；跨团队反馈环强制走 Loop 预算与 driver 语义 |

**启用必须人锁**（accountable stakeholder 显式确认 iteration_budget 与 stop_condition）。

## 5. 跨团队反馈环（Loop 特殊形态，仅 single_user）

1. **回流预算**：handoff 消费方验收不通过 → 回流生产团队迭代。默认 ≤2 次完整回流（full 档可人锁至 ≤4）
2. 每次回流 = 一次新迭代，**消耗 iteration_budget（共享预算池，非免费重试）**
3. **防 ping-pong 语义停滞检测**（比较语义指纹非轮数）：每次回流 mismatch 必带 acceptance_criterion_id + evidence_fingerprint；连续 2 次指向同一 criterion 且指纹无变化 → **semantic stall，立即终止升级（即使预算未耗尽）**；A→B→A 交替但每次不同 criterion → 可继续至预算上限，每轮记录新 criterion 证据
4. 超预算/semantic stall → 按 R1 处理，accountable 裁决（继续/终止/重新定义 goal）

## 6. 反绕过规则（核心条文）

**反碎片化**（拆 N 个 simple 逃避 loop 预算）：
1. 同一 goal_ref 下 ≥2 个 task 且 artifact 引用形成依赖链 → **必须共享一个 loop 容器**，消耗同一 iteration_budget
2. 创建 simple 档 task 须声明 `fragmentation_justification`（"独立可交付且无 artifact 依赖"）；无正当理由 → 归类为 loop 内迭代
3. 检测：CAP-STATE 按 goal_ref 聚合，>3 个 simple task 互相引用 → `suspected_loop_fragmentation` 告警

**反灌水**（每次迭代做最小改动摊薄成本）：
1. progress_signal **必须幅度感知**，不得是"有变化"二元信号：acceptance_delta（新通过 criterion 数，0=无进展）/ score_delta（低于 min_score_delta=无进展）/ fingerprint_change（必须伴随语义差异，纯格式变化不计）
2. no_progress_window 计数基于幅度感知信号；连续 N 次低于阈值 → stalled
3. 单次 artifact 变化量 < min_substantive_change（域片段声明）→ 标 `low_yield`，收敛轨迹降权，连续 low_yield 计入 no_progress_window

## 7. 与其他定案的修正关系

- **修正 W1 幂等键**：`hash(loop_id + iteration_index + action_type + input_fingerprint)`；loop 外 task 用 `hash(task_id + 0 + action_type + input_fingerprint)` 兼容；同 iteration 同输入 = 重复请求返回 ALREADY_RESOLVED；跨 iteration 同输入 = 不同请求 + "重复输入"告警
- **修正人类触达预算**：max_human_touch 按 **goal_ref 聚合**（整个 loop），re-plan 本身不触达人（仅 re-plan 需澄清时走 R6）
- **新增 CAP-SPAWN X4 有界性**：spawn 必须声明时限内有界返回（结构化结果或有界失败 `{bounded_failure: true, reason, partial_refs?}`）；**不满足 X4 的运行时不是合法绑定**（否则 iteration_budget 与 CAP-TIMER 失去意义）

## 8. 运行时驱动（核心不要求，绑定层实现）

核心只要求 CAP-SPAWN X2+X4、CAP-STATE/CAP-TIMER 驱动。运行时是否自带内部 loop 是绑定层的事。
通用 driver 形态 = **外部调度器（运行时调度器/定时器）+ CAP-STATE 幂等派生脚本**：
触发 → 读 CAP-STATE → 派生 next_action → CAP-SPAWN（X4 时限）→ 写回 CAP-STATE → 注册下次触发。
driver 缺席 → 调度器继续触发 → 检测心跳超时限 → 升级。
