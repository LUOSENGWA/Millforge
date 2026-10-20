# Task 5：最终自对抗——生产第 1 周会撞上的 3 处

> 版本: v1.0 | 许可: Apache-2.0
> 来源: DeepSeek 第六轮审查（生产化 + 开源就绪轮，2026-10-18）定案

## 5.1 协议自身版本化：在飞任务的 task meta 字段兼容

**问题**：协议 v1.0 → v1.1 演进时（例如新增 `decision_status` 子状态、修改 `attention[]` 的字段），在飞任务的 task meta 是 v1.0 结构，新核心脚本期望 v1.1 字段。混跑会发生什么？

**为什么 6 轮没抓到**：前五轮聚焦“机制是否存在”，没有审“机制升级时在飞任务的状态兼容”。binding-contract 定义了能力，但没定义**版本迁移语义**。

**修复**：

```
核心条文追加（协议版本化）：
1. task meta 必须包含 `protocol_version` 字段（写入于任务创建时）。
2. 核心脚本在读取 task meta 前，必须检查 protocol_version：
   - 若 == 当前版本 → 正常执行。
   - 若 < 当前版本 → 按注册的升级函数（upgrade_vX_to_vY）
     就地迁移；迁移是确定性的，不依赖 LLM。
   - 若 > 当前版本（旧核心读新状态）→ 拒绝执行，报
     `PROTOCOL_VERSION_TOO_OLD`，不静默降级。
3. 升级函数随核心分发（core/scripts/upgrade/）；每个大版本必须
   提供从上一版本的迁移路径。
4. 在飞任务的协议版本**不随全局升级自动变更**；新任务用新版本，
   旧任务完成后再标记 deprecated。绑定必须支持至少两个版本的
   核心脚本并存（版本路由由 `protocol_version` 决定）。
```

**归属**：核心条文 + core/scripts/upgrade/。绑定层负责版本路由（调用哪个版本的脚本）。

## 5.2 native 上下文预算：X1 保护 spawn，谁保护 native？

**问题**：CAP-SPAWN 的 X1 保证 spawn 是 fresh context，但父 Worker 的 native 会话承担调度 + 审查 + 合并裁决 + B-2 Step 5 冲突裁决 + critic 协调——这些工作会持续膨胀 native 上下文。生产第一周就会遇到 native session 因上下文过长而 compaction，丢失早期决策。

**为什么 6 轮没抓到**：前五轮把注意力放在 spawn 隔离（v2.40 的正确修复），默认 native 只做“调度+审查”；但第四轮 B-2 把冲突裁决放回 native（Step 5），加上 critic 在 native 审核全量产物，native 的实际负载远超“调度+审查”。

**修复（绑定规则 + 核心约束）** ：

```
核心条文追加（native 上下文预算）：
“承载调度/审查/裁决的执行体（native session）必须声明其上下文
预算，并在预算接近上限时触发结构化驱逐（structured eviction）——
优先驱逐已完成子任务的详细日志，保留：决策记录引用、未决
冲突列表、当前 task 的 acceptance_criteria。驱逐不得丢失
CAP-STATE 中的权威状态。”

绑定规则（参考绑定）：
1. native session 的上下文使用率 ≥60% → 触发 compaction 预警
   （60% 预警阈值为长时 agent 运行时的成熟模式）；
   ≥80% → 强制结构化驱逐。
2. 驱逐策略：保留 attention 未决项、当前 task spec、critic 未决
   mismatch；驱逐已合并 spawn 的完整 decision_log（只留 ref）。
3. 每次驱逐写入 provenance（evicted_refs[], tokens_saved）。
4. 如果 native 需要读多份 decision_log 做裁决，裁决输入必须
   来自 merge spawn 的摘要，不是 native 直接读全量日志（B-2
   Step 5 已经是这个模式，但需要在 native 预算规则中显式化）。
```

**来源依据**：长时 agent 会话的 compaction 是已知问题；既有长时 agent 运行时的 60% 阈值和结构化驱逐（priority regions，低优先级先驱逐）是成熟模式。协议只要求“声明预算 + 结构化驱逐 + 不丢权威状态”，具体阈值是绑定参数。

## 5.3 人类缺席的长任务：owner 休假一周，委托链操作路径顺不顺？

**问题**：R1 不可逆决策全部阻塞 2h×N；Z3 委托链虽然存在，但“owner 休假”场景下，委托的**发起**、**代理权限范围**、**休假期间的批量委托**、**回来后如何审计代理决策**——这些操作路径在协议中没有细化。

**为什么 6 轮没抓到**：Z3 只定义了“委托链可查询”，默认委托是逐次、显式的；没有审“长期缺席”这个最现实的场景。

**修复**：

```
核心条文追加（CAP-ROSTER Z3 执行细则）：
1. accountable stakeholder 可以设置**时间受限的批量委托**：
   delegation = {delegatee, scope: decision_class[], valid_from,
   valid_until, max_uses?}。valid_until 到期自动失效，不依赖
   手动撤销。
2. 委托必须在 NMH 或显式确认中记录；Agent 不得自行发起委托。
3. 休假场景：owner 在休假前设置 delegation，覆盖 R1/R2/R5/R6，
   valid_until = 返回日期；delegatee 的决策写入 decision record，
   标记 `via_delegation: true`。
4. owner 返回后，必须审阅 delegation 期间的 decision record；
   未审阅前，delegation 标记为 `pending_owner_review`，但
   不影响已执行决策的有效性（决策不因事后审阅而失效）。
5. 如果 owner 未设置 delegation 且缺席 → 按 B-5/R6 超时规则：
   R1 阻塞，升级 project owner；project owner 也缺席 →
   arbitrator 冻结。不自动放行。
```

**归属**：核心条文（CAP-ROSTER Z3 扩展）+ 绑定的 roster 存储实现批量委托。

**来源依据**：治理约束的决策权框架强调 “whose constraints count” 必须有明确规则；SRE 的 freeze-exit 也要求“engineering lead and product owner together”才能解冻——长期缺席必须有预授权的代理机制，否则系统停摆。

## 5.4 附：时钟问题（你列的第四点）

**问题**：U4 声明单调时钟，但多容器各有时钟；`timeout_at` 由谁写、以谁的时钟为准？

**修复**：

```
CAP-TIMER U1 修订（补充时钟权威）：
“timeout_at 必须由 CAP-STATE 写入，使用 CAP-STATE 所在时钟源的
时间；定时器触发时，比较的‘now’也必须来自同一时钟源，或通过
一次性时钟偏移校正（NTP 同步状态可查询）对齐。任何执行体不得
用本地墙钟直接判定超时。”
```

**归属**：核心条文（U1 补充）+ 绑定实现（单机部署时 CAP-STATE 和定时器共享时钟；分布式部署时需 NTP 或逻辑时钟对齐）。


# 自检汇总

| Task | 自检问题 | 结果 |
|---|---|---|
| **Task 1** | UX 是否在 8 能力 + 2 新不变式下成立？ | 成立；参考绑定 PR 是绑定层实现，不是核心要求 |
| **Task 2** | 安全章节是否泄漏组件名？ | 无运行时专名；机制矩阵只引用 CAP-* 和协议规则 |
| **Task 3** | 成本模型是否只从 CAP-STATE 派生？ | 是；human_touch_count / spawn_count / artifact_count 均来自 CAP-STATE 事件流 |
| **Task 4** | CAP-STORE T1–T3 在 S3 下是否全部可实现？ | T1 客户端哈希；T2 强一致 + conditional PUT；T3 链式 append 模拟。CAP-STATE 不建议用对象存储 CAS |
| **Task 5** | 3 个问题是否是“第一周就会撞上、6 轮没覆盖”？ | 版本化 / native 上下文 / 长期缺席委托 / 时钟——都是生产运维面，前五轮未细化 |


**与第一至五轮冲突标注**：

- **修正第五轮 PR-A 裁决**：第五轮说“PR-A 降级为 skill 二次路由”；本轮按新定案，attention 送达质量是核心要求，参考绑定应实现完整 UX（PR-UX-1~5），PR-A 的“路由扩展”并入 PR-UX-1/3。
- **修正第五轮 CAP-STORE T3**：明确 append 可以用“新对象链式”模拟，不要求同对象 JSONL 追加；S3 上不推荐同 key 并发 append。
- **修正第四轮 F-1**：“push 确认”抽象为 CAP-STORE T2 的执行细则（同步层确认后才返回），不绑定特定对象存储的 push 日志；同步层是绑定参数，确认语义是核心。
- **修正第三轮 B-5**：blocked/frozen 映射到既有 BLOCKED + decision_status 子状态（第四轮已定），本轮补充“长期缺席走 delegation 或 project owner 升级”，不新增状态。
