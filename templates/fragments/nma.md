## NMA（结构化通信 + 同行审查，精简装载版 · 全文 = 协议 §05-NMA）

**Part A 通信**：派发/回报/查询/交接一律走结构化消息（`DELEGATE/ACK/PROGRESS/COMPLETE/QUERY/DECISION_REQUEST/HANDOFF/ESCALATE`），必填 `message_id/task_id/from/to/type/refs[]/status`；**内容给 ref 不内联**；每条落 CAP-STATE；ACK 必回（超时 = 异常）；终态任务不再收消息。自由文本不是协作载体。

**Part B 审查——触发**：Worker 交付件属需审核类别（代码/配置/方案/文档）｜ 显式请求审核 ｜ 项目验收前终审。

**审核方 ≠ 被审核方**（角色实例表定；谁审谁 = 违规）。human 同行在场 → 先给人审（Agent 审核是替代不是补充）。

**双模式**（判断：产出能否用命令验证？）：

**Checklist 验票**（代码/配置/可验证产出）：
```
审核方发 [C{n}] {检查什么} — 命令: {cmd} — 预期: {result} — 🔓
被审方逐条 🟢 执行贴输出 → ✅（附证据）
审核方 🔵 独立验证（只限外部可验证面：API/对象存储可读/公开文档；做不了 = ❌ 注明，不假装）
全 ✅ = 通过 ｜ ❌ 有实质问题 = ⚠️ 驳回（附理由）
```
三要素缺一 = 无效条目。**隔离边界**：审核方不进被审方 workspace 执行命令。

**同行审查**（文档/方案/设计）：
```
[R{n}] {位置} — {质疑} — 严重度: 阻断/建议/提问 — 🔓
被审方逐条回应（接受改/不接受说理由/求澄清）→ ✅/⚠️/🏳️
全 ✅ = 通过 ｜ ⚠️ = 改后复审 ｜ 🏳️ = 升级
```

**升级（🏳️）**：single_user → arbitrator；multi_user → leader（方向性僵持 → 建议当事人 human 直接谈）。升级内容 = 双方立场 + 分歧点 + 依据。**不升级情绪，只升级事实。**

**多 Critic（critical_delivery + R1 + 异构池满足时）**：N fresh 独立实例（≥2 模型族）/ 独立 verdict + dissent ≥1 假设 / 严格多数 / 平票不重投直接升级 / 少数意见保留 / 打回按投票轮计 mismatch。

**B-6 死环防护**：mismatch = 规格澄清通道（24h accountable 裁决窗口）；超时 = 维持原 spec + critic 记 dissent 且**仍出评分卡**；同 criterion 3 轮 → 冻结升级 human；**critic 是质量信号不是否决权，终裁 = human**。

**禁止**：假验证 ｜ 静默驳回 ｜ 越界改被审产出 ｜ 无理由锁定。
