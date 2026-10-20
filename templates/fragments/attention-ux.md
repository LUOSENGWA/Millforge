## Attention UX（持久展示面应答 · 精简装载版 · 全文 = CAP-ATTN W1-W7 + 12-REDLINES S4）

**应答面质量（W5）**：每个 attention 请求必须至少一个**持久展示面**——超时前持续存在、可主动回访、应答可身份验证。
- ✅ 持久展示面：IM 私聊 bot / dashboard 待办列表 / 专用审批页 / 控制台通知
- ❌ **群聊 @mention 不是**（消息被淹没、无法回访、身份不可靠）
- 通道信任低于持久展示面要求的 → 只能通知，不能 resolve

**应答语义**：
- 人类在群聊表达意愿 → 引导至持久展示面显式 resolve（bot 回复"请在私聊/审批页确认"）
- resolve 必校验 responder 身份（运行时 member_id 映射；payload 自声明角色无效）
- kind=decision + options → 应答必须回传 **option_id**（W7 结构化），自由文本选择 = 拒收
- 多面关闭（W6）：任一面 resolve → 其他面轮询/事件同步关闭（视图行为，不改权威状态）

**超时（CAP-TIMER 判定，W3）**：可逆 30min / 不可逆 2h（阻塞不自动通过）；R5 重开窗口 24h/4h；到期动作 = 派生（读 CAP-STATE 重算），不是"定时器里存的标记"。

**幂等（W1/S5）**：重复 resolve 返回首次结果；幂等键含 task_id + request_id + responder_id + action；跨 task 重放 = 拒收。

**你的义务**（作为发起方）：
1. 发起 attention 时给出 选项（结构化，每项含后果摘要）+ 明确 route_to（roster 验证）+ timeout_at
2. 收到 delivery_report 含 gaps（accountable 不可达）→ 立即通知 + 按超时规则走，不假装已送达
3. 人类应答后 → 写 CAP-STATE（resolved + surface + 时间戳）+ 派生后续动作；**R6 回答带 contract_snapshot**（C-2）
