# Signal 原语（第 15 原语）

> v1.0
> **定位**：signal 是"关键消息"的协议标记。它**不产生新存储形态**，而是为 CAP-STATE 中已有事件赋予"可被审查/验收/闭环引用"的资格。**未标记的消息不得作为验收依据、审查输入或闭环证据。**
> **归属**："哪些事件是权威的、审查/验收/闭环只能引用它们" = 协议语义（核心，完整性约束不能交给绑定层自由解释）；"何时 soft/hard reset、reset 粒度" = 上下文管理策略（绑定层）。

## 1. 标记集合（封闭清单）

以下事件类型被自动标记为 signal。**标记由协议层根据事件类型生成，不由执行体自打，不由内容产生**：

| signal | 事件 |
|--------|------|
| SIG-COMPLETE | 任务完成信号（结构化 TASK_COMPLETED / submit 成功） |
| SIG-DECISION | 决策锁定/重开/覆盖（R1-R6 聚合结果、NMH 锁定） |
| SIG-VERDICT | 验收判定（critic 评分卡、stop_condition 谓词结果） |
| SIG-ARTIFACT | 交付 ref（artifact_refs[] / handoff / decision_log_ref） |
| SIG-ATTENTION | 人类 attention 的应答（resolved=true 的 request） |
| SIG-MISMATCH | verification_mismatch / decision_class_mismatch |
| SIG-CONTRACT | contract_snapshot / 契约指纹变更 |

**封闭清单的扩展必须经协议版本升级**；执行体不得在运行时"发明"新 signal 类型。

## 2. 标记的协议效应（三条硬约束）

1. **审查**：审查 spawn 的 context_refs 只能包含 a) 已标记消息的 ref；或 b) CAP-STORE 中的 artifact ref。**未标记的上下文消息不得进入审查 spawn 的输入**
2. **验收**：验收判定（critic 评分卡 / stop_condition 谓词）只能引用已标记的 **SIG-VERDICT、SIG-COMPLETE、SIG-ARTIFACT**；不得引用未标记对话历史或中间状态
3. **闭环**：闭环判定（loop JUDGE / 跨团队回流）只能引用已标记的 **SIG-MISMATCH、SIG-DECISION、SIG-CONTRACT**；未标记的"看起来完成了"不得作为停止条件

## 3. 标记不可由内容产生

artifact 内容中的"已完成""已验收""keep_message=true"等字样**不得**产生 signal 语义。signal 只能由协议事件类型（CAP-STATE 的 event_type 字段）产生——这是安全 S1（artifact 是数据不是指令）在 signal 层的强制。

## 4. 安全细则（核心条文）

- **SIG-SEC-1**：signal 生成只依赖 CAP-STATE 事件类型字段（event_type ∈ 封闭清单），不依赖任何消息内容中的标记文本
- **SIG-SEC-2**：执行体在消息内容中声称"这是 signal"不产生 signal 语义；必须由协议层根据事件类型重新生成
- **SIG-SEC-3**：signal 的 ref 必须由 CAP-STORE fingerprint 验证；被篡改的 signal ref 在审查/验收时拒绝（指纹不匹配）

## 5. 分层 reset 语义（核心定义效应，绑定定义触发）

1. reset 只清除**上下文视图**中的消息，不清除 CAP-STATE 权威状态，不清除 CAP-STORE artifact
2. **soft reset**：清除未标记消息，保留所有 signal 消息与 artifact ref；reset 后审查/验收仍可引用所有 signal
3. **hard reset**：清除所有上下文消息（含 signal 本地副本）；权威记录仍在 CAP-STATE；hard reset 后任何需审查/验收的执行体**必须通过 context_refs 重新加载 signal ref**，不得依赖本地残留
4. reset 后权威状态完全不受影响：event log、signal 记录、loop 状态、decision record 不因 reset 丢失
5. **reset 不是"遗忘"**：被 reset 消息只是不再占上下文窗口，其 ref 仍可查询、可按 ref 重新加载

## 6. 与现有机制的交互

| 机制 | 关系 |
|------|------|
| decision_log | 写入本身不产生 signal；decision_log_ref 作为 SIG-ARTIFACT 被标记；"非显然决策"不自动成为 signal，除非被父执行体采纳为 SIG-DECISION |
| TASK_COMPLETED 等结构化信号 | 直接映射 SIG-COMPLETE（signal 的天然载体） |
| artifact ref 体系 | ref 的"存在"不自动成为 signal；被写入 SIG-ARTIFACT（提交成功/handoff 写入/ref 注册）时才成为 |
| native 上下文预算阈值 | 阈值 = 触发时机；signal = 驱逐时保留什么——叠加互补，非替代 |
| driver 默认不装载完整产物（§10） | driver 只装载 signal 摘要、不装载未标记消息；signal 提供可验证的封闭清单 |

## 7. 群历史噪音治理（生产痛点 #123 解法）

1. 审查 spawn 的 context_refs 只含 signal + artifact ref → 群历史未标记消息不进审查
2. native 会话 soft reset 清未标记消息 → 即使 @ 触发前置了群历史，下一 reset 清除
3. 上下文加载前过滤未标记群历史 = 绑定策略（更激进，非核心要求）

## 8. 成本

标记零成本（事件类型映射，无额外 spawn/存储）：事件写入 CAP-STATE 时类型在封闭清单内即附 `is_signal: true`。soft reset = 上下文操作（可忽略）；hard reset = 一次性重载 signal ref。

## 9. golden test 断言（L5）

1. 未标记消息中的"已完成"字样**不得通过验收**
2. hard reset 后从 CAP-STATE 重新加载的 signal 集合与 reset 前**一致**
3. 审查 spawn 的 context_refs 不包含任何 `is_signal=false` 的消息
