## 跨团队 Handoff（精简装载版 · 全文 = 协议 §07-HANDOFF · 仅 single_user 编译）

**三硬约束**：① 文档驱动不建跨团队群聊（注意力稀缺，唯一正确载体 = 结构化文档）② 禁止跨团队直连（leader 间不直接通信，信息流经 arbitrator）③ **arbitrator 独占 handoff 写作权**（leader 只提供原材料 = TASK_COMPLETED 关键结论）。

**三个硬限制**：上下文 ≤3 句 ｜ 关键决策 ≤5 条 ｜ 总行数 ≤50（超过 = 拆两份）。

**格式**：
```markdown
# Handoff: {A} → {B} | 项目 {proj-id} | 日期 | 序号 {N}
原始需求: {brief 路径} ｜ 产出: {artifacts/{A}/}
## 上下文（≤3 句）——B 需要的前提，不写 A 的过程
## 关键决策（≤5 条）——每条: 主题: 一句话结论 + 影响: 对 B 的具体影响
## {B} 需要做什么——可执行任务清单
## 约束 & 依赖——契约面决策的权威来源；无 → 写"无"
## 问题？→ @arbitrator（不要直接找 A 团队）
```

**模式**：A 并行独立（无 handoff，arbitrator 汇总）｜ B 顺序依赖（handoff 序号递增，可多次来回）。

**失忆防御（写 handoff 的机械流程）**：冷读三文件 = brief（恢复需求）+ TASK_COMPLETED 关键结论（素材）+ 必要时扫 artifact（只提取对 B 有影响的）→ 提取 → 格式化（12K→1.5K，8:1 压缩）。**不依赖记忆，不依赖深度理解。**

**派发**：在 B room @B-leader + 指向 handoff 文档路径 + 一句话任务。**不在消息里复述内容**（注意力保护）。

**回流（full 档 loop）**：≤{{max_reflow}} 次完整回流消耗共享预算池；同 criterion 同指纹连续 2 次 = semantic stall 立即终止升级。

**权限**：共享空间 {proj}/brief.md + meta + artifacts/{team}/ + handoffs/；arbitrator 读写，各团队只读（自己 artifacts 可写）。
