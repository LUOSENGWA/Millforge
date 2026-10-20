## 任务生命周期（精简装载版 · 全文 = 协议 §06-LIFECYCLE）

**递归拆解**（每层 mini-编排者，循环同构）：收到任务 → 判来源（human=NMH / Agent=三要素校验）→ 确认理解 → 拆解 → 派发下一层 → 验收整合 → 回报上级。

**派发三要素**（缺任一项 = 派发无效，接收方有权退回）：任务目标 / 验收标准 / 交付位置。

**TASK_COMPLETED（强制格式）**：
```
@{leader} TASK_COMPLETED: {task-id}
产出: {artifact 路径}
关键结论（3-5 条，一句话一条）:
1. ...
```
**关键结论是强制项**——验收原材料 + handoff 原材料 + 失忆防御。刚完成时总结三句是顺手的事，事后补不出来。

**双通道汇报**：项目 room 完整汇报（归档底线：结论/产出路径/遗留/下一步）+ 原始通道一句话通知（送达底线：完成 + 关键结论 + room 指针）。单团队 = 原始通道即底线。

**回复纪律（room 噪音控制）**：只 @mention 需要对方行动的（handoff/blocker/direct question/依赖）；纯确认消息（谢谢/收到）→ 不回复（防 ping-pong）；完成报告发出后停止，等新任务。

**故障 SOP（编排者不代干活）**：
```
Worker 异常（Internal error/context exceeded/无响应>2min）
 Step 0: 停手——绝不自己打开 artifact 代做
 Step 1: restart 该 worker
 Step 2: 等待 → 重新派发相同任务
 Step 3: 3 次仍失败 → 升级 human（附三次尝试记录）
质量不行 ≠ 故障 → 走 NMA 审核链，不 restart
```

**Worker 上下文隔离**：native session 只调度+审查；实现全进 fresh spawn（文件读上下文→文件写产出→销毁）。上下文超限 = 隔离被违反或 spawn 上下文过大，先查文件引用链。

**状态机副作用（L1/L2，不靠自觉）**：TASK_COMPLETED 基线发出 = 提交成功的机制副作用；超时判定 = CAP-STATE 字段 + CAP-TIMER；冲突/计票/一致性 = 确定性脚本。系统正确性只依赖 L1/L2。
