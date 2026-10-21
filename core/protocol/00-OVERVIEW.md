# 千锻（Millforge）协议总则

> 版本: v1.0 | 许可: Apache-2.0
>
> **通用词纪律（核心层铁律）**：本目录（含 schemas/、invariants/、scripts/、compiler/、templates/、golden-tests/）
> 只允许 **CAP-\* 能力编号 + 通用词**（子代理/subagent、父执行体、主会话、持久展示面、运行时调度器、
> 对象存储、通知通道、决策记录、状态存储、定时器）。运行时专有 API 名（spawn_subagent、QwenPaw cron、
> channels send、mc、dashboard 具体组件、Matrix、MinIO/RustFS 等）**只允许出现在 `bindings/` 层**。

## 1. 定位

千锻是**多 Agent 协作的协议层**：运行时无关的语义契约 + 确定性执行实现 + 编译器。
运行时（TeamHarness、裸 QwenPaw、claude-code 等）通过 `binding-contract.md` 的 8 能力声明绑定，
协议不依赖任何特定运行时的存在。

## 2. 设计原则（不可妥协）

| # | 原则 |
|---|------|
| P1 | **注意力稀缺是系统核心**——不是信息不够，是噪音太多。1M 上下文也会失忆。跨层信息走文件/引用，不走对话上下文 |
| P2 | **文件即契约**——不靠 Agent"记得说了什么"，靠写入文件。口头承诺在协议里不存在 |
| P3 | **声明-验证绑定**——任何"已完成/已发送/已创建"声明之前，同一轮内必须先有对应工具调用且成功。文本输出和工具调用是两条通道 |
| P4 | **约束越靠底层越可靠**——代码级硬约束（能力门控）> 确定性脚本 > 行为软约束。能用底层就不用上层 |
| P5 | **分层可靠性**——每条规则必须标注落层（L1 平台内置 / L2 确定性脚本 / L3 行为层）。系统正确性只允许依赖 L1/L2；L3 只做质量增强 |
| P6 | **容量够 ≠ 注意力够**——长上下文注意力 U 形分布；常驻内容受行硬门约束，冷路径按需装载 |
| P7 | **自研胶水最小化**——平台已有机制一律复用；自研组件必须能回答"平台为什么没有" |
| P8 | **协议是编译物，不是手写稿**——Agent 的 SOUL/身份文件由模板+实例参数编译生成；LLM 只能贡献有界、校验、人可见的字段。同输入同输出，否则标准化死亡 |

## 3. 文档地图

| 文件 | 内容 |
|------|------|
| 01-PRIMITIVES | 15 原语 + 角色不变量 |
| 02-MODES | 部署模式（single_user / multi_user 相变） |
| 03-DECISIONS | 决策类 R1-R6 + decision_log + 类型封闭（B-1/B-10/C-1） |
| 04-NMH | 人↔Agent 协作探索协议 |
| 05-NMA | Agent 间结构化通信 + 同行审查协议 + 多 critic 投票（MC-1~10） |
| 06-LIFECYCLE | 任务生命周期契约（递归拆解/完成信号/双通道/故障 SOP/熔断） |
| 07-HANDOFF | 跨团队扩展（仅 single_user） |
| 08-CONTRACT | 契约 pinning + spec 结构化（B-3/C-2/B-9） |
| 09-GOVERNANCE | 投票/裁决/状态映射（B-4/B-5/B-8/C-3） |
| 10-LOOP | Loop 原语（第 14 原语） |
| 11-SIGNAL | signal 原语（第 15 原语） |
| 12-REDLINES | 红线 + 可靠性分层 + 注意力装载 |
| ../binding-contract.md | 8 能力接口（CAP-STATE/STORE/TIMER/NOTIFY/ATTN/SPAWN/EXEC/ROSTER） |
| ../schemas/ | JSON Schema（10 个） |
| ../invariants/ | 状态机不变式 |
| ../scripts/ | 8 确定性脚本 + timer-derive（协议语义的确定性实现） |

## 4. 版本策略

- 语义变更 = minor；原语增删 / 模式定义变更 = major
- 绑定版独立版本化，声明"兼容 Millforge v1.x"
- 旧版本文档归档不删除（审计链）
- protocol_version 字段出现在 spec/loop_spec/decision_log 等结构物中，升级不静默

## 5. 不做的（边界）

- 不改框架代码——协议是叠加层；发现框架 bug → 上游 issue+PR
- 不建新存储引擎——文件即数据库（CAP-STORE 承载）
- 不做自动合并/冲突解决——锁定后不可改，冲突走裁决/升级
- 不强制全通信结构化——日常对话不需要协议
- 不做跨用户团队通信（multi_user）——隔离是设计不是缺陷
- 不设计前端可视化——协议产出是可视化数据源，前端是独立工程
- 不用定时器/心跳做实时驱动——定时器只适合兜底恢复；实时驱动走事件触发 + 状态机副作用（L1/L2）
