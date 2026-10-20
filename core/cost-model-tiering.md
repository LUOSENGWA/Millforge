# Task 3：协议成本模型 + 分层定案

> 版本: v1.0 | 许可: Apache-2.0
> 来源: DeepSeek 第六轮审查（生产化 + 开源就绪轮，2026-10-18）定案

## 3.1 每机制触发条件审计

| 机制 | 触发 scoping | 是否始终强制 |
|---|---|---|
| **decision_log** | 任何 spawn 执行体（因为 D1/D2/D3 判据可能命中）；但 D1–D3 都不满足时日志可以为空并标注 `no_significant_decisions` | **条件强制**：spawn 必须产出，但内容可以为零条（需显式声明“无显著决策”，不是省略） |
| **contract** | 跨边界并行实现（≥2 个执行体写同一契约面，或 provider/consumer 分离） | **条件强制**：无跨边界则不要求契约 |
| **critic 隔离** | 任何需要验收的 artifact（产出物需要被验收时） | **始终强制**（如果产物有验收环节）；纯只读/研究任务无 artifact 验收时可无 critic |
| **冲突检测 Step 1–3** | 同一 artifact 有 ≥2 份 decision_log | **条件强制**：单 spawn 无并行写 → 跳过 |
| **三段 handoff** | 跨团队 / 跨 Leader 边界 | **条件强制**：团队内部不要求三段格式 |
| **NMH** | 新 spec 或 spec 重大变更 | **条件强制**：已有锁定 spec 的常规任务不需要重新审讯 |
| **R1–R6 聚合** | 决策触及人类输入时 | **条件强制**：Agent 自主范围内的 R4 自动通过 |
| **指纹 / submission fence** | 任何 artifact 持久化 | **始终强制** |
| **声明-验证绑定** | 任何“已推送/已派发”声明 | **始终强制** |

## 3.2 每任务成本预算

**人类触达 = 最稀缺资源**。以下按三档任务估算：

| 档位 | 任务特征 | 额外 spawn 数 | 人类触达次数 | 新增 artifact 数 |
|---|---|---|---|---|
| **Simple**：单 worker 简单任务（如单文件文档修改、单个查询） | 无并行写、无跨边界、decision_class=R4 为主 | 0–1（critic 可选；如果产物无需验收则 0） | 0–1（仅当触发 R6 时） | 1–2（artifact + 可选 decision_log） |
| **Standard**：单团队多 worker 并行（如 SW-01 的 provider/consumer 并行、BIZ-01 分析读并行） | 有并行写、有契约、可能需要 merge | 1–3（merge spawn + 可选受限分类 spawn + critic） | 1–3（NMH spec 锁定 + 可能的 R6 attention + mismatch 澄清） | 4–8（契约 + 2×decision_log + 合并 artifact + critic 报告 + handoff） |
| **Full**：跨团队链路（A 团队→B 团队，Manager 协调） | 所有机制都可能触发 | 3–6（每团队的 merge/critic + Manager 协调） | 2–5（每团队的 NMH + 跨团队 handoff 的 attention + 可能的 R5） | 8–15（每团队的 artifact + 跨团队 handoff + decision record） |

**人类触达预算**（超预算告警）：

| 档位 | 预算 | 超预算含义 |
|---|---|---|
| Simple | ≤1 次 | 超过说明 spec 质量差（歧义多）或任务被错误分类为 simple |
| Standard | ≤3 次 | 超过说明并行写冲突频繁或 critic 与 spec 不一致反复出现 |
| Full | ≤5 次 | 超过说明跨团队 handoff 质量差、契约不稳定、或 R5 重开过多 |

**告警规则**：每档任务在 task meta 中维护 `human_touch_count`；超过预算时在 provenance 中标记 `human_touch_budget_exceeded`，并触发一次自查（不是自动升级，是给 Leader/Manager 的信号：“这个任务的协议开销过高，检查 spec 和契约”）。

## 3.3 分层定案：需要任务复杂度分层吗？

**推荐：引入 simple / standard / full 三档，但分层的作用是“声明哪些机制可条件跳过”，不是“跳过协议核心”。** 分层是**输入参数**（task 创建时由 accountable stakeholder 或 Leader 在 spec 中声明），不是执行者运行时可以自行选择的逃生口。

**反对纯“触发式 scoping 已足够”的理由**：触发式 scoping 的问题在于“触发判定”本身需要成本——Leader 需要判断“这个任务是否跨边界”“是否有并行写”，这些判断可能出错（误判为 simple 而跳过 decision_log）。分层把判定前移到 spec 创建期，由人类锁定，执行者不能中途降级。

**支持分层的理由**：如果协议成本与任务风险不匹配，执行者会用脚投票绕过协议（例如把跨边界任务拆成两个“单团队”任务来避免 contract）。分层提供合法的降级路径，但降级必须显式声明并记录，而不是隐式绕过。

### 分层的具体规则

| 机制 | simple 可否降级 | standard | full | 理由 |
|---|---|---|---|---|
| **指纹 / submission fence** | ❌ **不可降** | 强制 | 强制 | 完整性基础，降级 = 静默丢数据 |
| **provenance** | ❌ **不可降** | 强制 | 强制 | 审计基础，降级 = 不可追溯 |
| **验收绑定（critic 或等价验证）** | ⚠️ 可简化为“单次验证”，但不可省略 | 强制 | 强制 | 无验收 = 声明即事实 |
| **人锁 spec（NMH 或显式 spec 锁定）** | ❌ **不可降**（可简化审讯轮次，但 spec 必须被人类确认） | 强制 | 强制 | 需求权不可委托给 Agent |
| **decision_log** | ✅ 可降为“空日志 + `no_significant_decisions` 声明” | 强制（D1–D3） | 强制 | 无并行写时 D3 不满足，日志可为空但必须显式 |
| **contract** | ✅ 可跳过（无跨边界时本来就不要求） | 跨边界时强制 | 强制 | 条件触发 |
| **冲突检测 Step 1–3** | ✅ 可跳过（单 spawn 无冲突） | 并行写时强制 | 强制 | 条件触发 |
| **三段 handoff** | ✅ 可跳过（团队内部） | 跨团队时强制 | 强制 | 条件触发 |
| **R1–R6 聚合** | ✅ R4 自动通过；R1/R2/R5/R6 仍按规则 | 强制 | 强制 | R1 等不可逆决策不可降 |

**你的预判验证**：你说“不可降清单 = 指纹 / provenance / 验收绑定 / 人锁 spec”——**基本正确，但需修正一处**：验收绑定在 simple 档可以**简化**为“单次验证”（例如由父 Worker 做一次声明-验证检查），而不是必须独立 critic。完全省略验收绑定是不可接受的（那样就退化为“声明即事实”）。其余三条完全不可降。

**分层不是逃生口的强制机制**：

1. 档位声明由**人类在 spec 创建时锁定**（NMH 或显式确认），Leader 不能自行降级。
2. 执行期如果发现实际复杂度高于声明（例如 simple 任务出现了并行写）→ 必须发出 `complexity_mismatch` 事件，按 B-10 的 saga 补偿逻辑处理，而不是继续按 simple 跑。
3. provenance 记录档位和任何降级决策；golden test 包含“simple 档任务是否被正确限制在 simple 机制内”的检查。

## 3.4 自检：成本模型是否假设只有特定运行时才有的度量

| 度量 | 数据来源 | 是否只用 CAP-* |
|---|---|---|
| human_touch_count | CAP-STATE 的 attention resolve 事件计数 + NMH 锁定事件 | ✅ 从 CAP-STATE 事件流派生 |
| spawn_count | CAP-SPAWN 的创建事件 | ✅ |
| artifact_count | CAP-STORE 的 write 事件 | ✅ |
| 超预算告警 | provenance 标记，由编译器/协议层根据 CAP-STATE 事件派生 | ✅ 不依赖 dashboard 统计 |

**结论**：成本模型完全从 CAP-STATE 事件流派生，不依赖任何特定运行时的 dashboard 统计。dashboard 只是这些事件的可视化视图，不是数据源。


## 多 Critic 预算注记（第八轮 2026-10-19）

多 critic 投票的 N 个 critic = N 个 fresh spawn，**全部计入 spawn 预算**（无折扣）。
超预算时**不降级为纯单 critic**——降级路径 = "单 critic + 强制 dissent + 人锁验收"
（人必须显式确认单 critic 结论）。详见 `core/protocol/05-NMA.md` §7 成本集成。
