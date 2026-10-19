# 跨团队扩展（仅 single_user 模式）

> v1.0 | 来源: NMProtocol §9（跨团队文档驱动设计定案）
> multi_user 模式下本文件**不存在**（用户隔离）。编译时条件装载：仅 single_user 编译进 arbitrator 身份文件。

## 1. 三条硬约束（设计定案）

1. **文档驱动，不建跨团队群聊**——群聊上下文 = 噪音污染 + 访问控制不对称，LLM 注意力稀缺下唯一正确载体是结构化文档
2. **禁止跨团队直连**——leader 之间不直接通信。所有跨团队信息流经 arbitrator（架构制衡，不是技术限制）
3. **arbitrator 独占 handoff 写作权**——跨团队视角（B 团队需要什么）是 arbitrator 的本职，不是 A 团队 leader 的。leader 只提供原材料（TASK_COMPLETED 附带的关键结论）

## 2. Handoff 格式（三个硬限制）

arbitrator 写：

| 限制 | 值 | 原因 |
|---|---|---|
| 上下文 | ≤3 句 | B 不需要知道 A 怎么做的——只需要前提 |
| 关键决策 | ≤5 条 | 从 A 的产出中提取**对 B 有影响**的结论，不是"A 讨论了什么" |
| 总行数 | ≤50 行 | 超过 = 拆两份 handoff |

```markdown
# Handoff: {A 团队} → {B 团队}
项目: {proj-id} | 日期: {YYYY-MM-DD} | 序号: {N}
原始需求: {brief 路径}
产出: {artifacts/{A}/{文件}}

## 上下文（≤3 句）
{B 需要知道的前提。不写 A 的过程。}

## 关键决策（≤5 条）
1. {主题}: {一句话结论}
   影响: {对 B 的具体影响}

## {B 团队} 需要做什么
- [ ] {可执行任务}

## 约束 & 依赖
- {硬约束，如"此接口已锁定不可改"} / 无 → 写"无"

## 问题？
→ @arbitrator（不要直接找 A 团队）
```

## 3. 两种模式

| 模式 | 语义 | handoff |
|---|---|---|
| **A：并行独立**（"A 和 B 一起评估"） | 两团队独立闭环，arbitrator 汇总 | 无 |
| **B：顺序依赖**（"A 先出 spec，B 基于 spec 做"） | 方向性交付物流转 | 有（序号递增，可多次来回） |

判断：human 说"一起/都看" → A；"先…再…/基于…" → B。

## 4. 失忆防御（arbitrator 写 handoff 的机械流程）

arbitrator 不需要记住项目历史——**三份文件 = 外挂记忆**：
1. 读 **brief**（human 原始需求，NMH 锁定版）→ 恢复需求上下文
2. 读 A leader 的 **TASK_COMPLETED 关键结论**（上一条消息）→ 素材
3. 需要时扫读 **artifact**（只提取对 B 有影响的条目）→ 细节

冷读 → 提取 → 格式化（12K 输入 → 1.5K 输出，8:1 压缩），不依赖深度理解。

## 5. 语义约束（绑定层实现时必须遵守）

- 共享存储（CAP-STORE）上必须有跨团队项目空间：`{proj-id}/brief.md + meta + artifacts/{team}/ + handoffs/`
- 权限：arbitrator 读写，各团队 leader/worker 只读（自己 artifacts/ 目录可写）
- handoff 派发 = 在 B 团队 room @B-leader + 指向 handoff 文档路径（**文档路径 + 一句话任务**，不在消息里复述内容——注意力保护）
- 汇总闭环：全部团队完成 → arbitrator 综合汇报（双通道，§06-3）
