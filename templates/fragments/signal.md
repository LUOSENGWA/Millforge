## Signal 原语（精简装载版 · 全文 = 协议 §11-SIGNAL）

**7 种封闭标记**（运行时发明 = 协议升级；由事件类型自动产生，不由内容产生、不由执行体自打）：
`SIG-COMPLETE`（完成）· `SIG-DECISION`（决策锁定/重开）· `SIG-VERDICT`（验收判定）· `SIG-ARTIFACT`（交付 ref）· `SIG-ATTENTION`（人类应答）· `SIG-MISMATCH`（验证/分类不匹配）· `SIG-CONTRACT`（契约快照/指纹变更）

**三条硬约束（引用资格）**：
1. **审查**：审查 spawn 的 context_refs 只能含 ① 已标记消息 ref ② CAP-STORE artifact ref。**未标记的上下文消息不得进入审查输入**
2. **验收**：验收判定只能引用 SIG-VERDICT / SIG-COMPLETE / SIG-ARTIFACT；不得引用未标记对话历史或中间状态
3. **闭环**：闭环判定（loop JUDGE / 跨团队回流）只能引用 SIG-MISMATCH / SIG-DECISION / SIG-CONTRACT；"看起来完成了"不得作为停止条件

**安全**：artifact 内容里的"已完成/keep_message=true"等字样**不产生** signal 语义（S1 数据红线）；signal ref 必须过 CAP-STORE 指纹验证（篡改 = 拒收）。

**分层 reset（上下文管理，绑定层触发）**：soft = 清未标记消息（signal 保留）；hard = 全清（signal 从 CAP-STATE 按 ref 重载）；reset **不是遗忘**——ref 可查可重载，权威状态不受影响。

**群历史治理**：审查只进 signal + artifact ref → 群历史噪音不进审查；soft reset 清未标记 → 生产痛点 #123（群历史污染上下文）的协议解法。
