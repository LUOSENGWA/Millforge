# 原语集（15 原语）

> v1.0
> 语义只在这里定义一次。绑定层只能映射（原语 → 具体机制），不能重定义。

| 原语 | 定义 | 备注 |
|------|------|------|
| `human` | 人类用户。系统的最终决策者与学习者 | 一个集群可有多个 human（多用户模式） |
| `agent` | LLM 驱动的协作单元 | 有角色（role） |
| `leader` | 团队编排者：理解任务、拆解、派发、验收、汇报 | 一个团队一个 |
| `worker` | 执行者：领原子任务、产出交付件、报告阻塞 | 可含特殊 Worker（critic = 专职审核） |
| `arbitrator` | 仲裁者：决策僵持（🏳️）升级对象；单用户模式下兼跨团队协调者 | 模式依赖（§02-MODES） |
| `room` | 多人通信空间：team room / task room（项目群）/ DM | 结构化通信的主载体 |
| `project` | 有 ID 的工作单元，拥有计划、依赖、验收进度 | 状态由机制层管理（CAP-STATE） |
| `task` | project 内的原子工作项，有 spec / 交付目录 / 状态机 | 派发与验收的单位 |
| `artifact` | 任务产出文件（文档/代码/数据） | 存放在对象存储（CAP-STORE），有路径契约 |
| `decision node` | NMH/NMA 决策树的一个节点，有状态标记 | 锁定后不可改，可演化 |
| `channel` | human 与 Agent 的原始通信通道（IM/邮件/控制台） | 双通道汇报的"原始通道" |
| `mode` | 部署模式：`single_user` / `multi_user` | 决定 arbitrator 形态与跨团队扩展可用性 |
| `attention` | 人类注意力请求：R6 决策/升级/澄清的载体，有应答持久化与超时语义 | 第 13 原语；依赖 CAP-ATTN |
| `loop` | 目标驱动迭代容器：goal 锁定 → 迭代（派发→独立验证）→ 达成?停:重规划，预算内运行 | 第 14 原语（§10-LOOP）；包含 task，不等同 task |
| `signal` | 关键消息的协议标记：赋予事件"可被审查/验收/闭环引用"的资格 | 第 15 原语（§11-SIGNAL）；不产生新存储形态 |

**能力依赖**：
- `attention` → CAP-ATTN（幂等/应答持久化/超时归 CAP-TIMER/身份可信）
- `loop` → CAP-STATE（权威状态）+ CAP-TIMER（兜底唤醒）+ CAP-SPAWN（X2 结构化返回 + X4 有界性）
- `signal` → CAP-STATE（event_type 字段）+ CAP-STORE（ref 指纹验证）

## 角色不变量（所有绑定必须遵守）

- `leader` ≠ `worker`——派给 leader 的任务 = 项目级任务（需要建 room/project），不是 DM 一个任务就完
- `worker` 不拆解、不派发给其他 worker（特殊 worker 除外：critic 只审不做）
- `arbitrator`（单用户模式）不做 worker 的活——编排者不是实现者（故障 SOP 见 §06-LIFECYCLE 6.6）
- **`leader` ≡ `arbitrator` 功能对齐**：两者是同一编排者角色种类，功能核心相同 = 任务拆解/派发/验收 + 同行审查 + 闭环汇报；差异只有**管辖范围**（团队 vs 集群）与**存在条件**（arbitrator 仅 single_user 存在）。同一套协议，只差管辖范围
- **验证者 ≠ 声明者**（五条款核心）：任何产出方的验收不能由自己完成。critic 独立 fresh 上下文（CAP-SPAWN X1）
- **accountable 单点**：每个 project/loop/decision 有且仅有一个 accountable stakeholder（CAP-ROSTER Z2），委托链可查询（Z3），不得集体持锁
