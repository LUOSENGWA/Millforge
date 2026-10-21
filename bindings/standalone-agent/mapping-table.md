# 机制 × 运行时映射表（裸 QwenPaw）

> 本文件是 `bindings/standalone-agent/` 映射的**单一事实源**（`README.md`「CAP 映射」为其一致摘要）。
> 通用词纪律：本目录是运行时专名的唯一合法出现面（`core/protocol/00-OVERVIEW.md` §S：核心条文只允许 CAP-* 编号 + 通用词）。

## 1. CAP → 机制映射（8 能力基线）

| 能力 | 裸 QwenPaw 机制 | 不变式满足情况 | 风险/备注 |
|------|----------------|--------------|-----------|
| **CAP-STATE** | 每 agent 本地 JSON 状态文件（`.qwenpaw/` 或工作区）+ 文件锁 CAS | S1 ✅（宿主盘持久）S2 ✅（文件锁；单机每 agent 单写者）S3 ✅（JSONL append）S4 ⚠️ | 宿主盘故障 = 状态全丢；**绑定声明：状态无异地副本**，宿主备份策略由部署方自担 |
| **CAP-STORE** | 本地文件系统 / 共享卷（`storage_adapter: local`） | T1 ✅（客户端 sha256）T2 ✅（本地写 = 同步完成；无异步同步层竞态，T2 执行细则退化）T3 ✅（同对象 JSONL append，本地 POSIX 安全；或链式） | 共享卷并发写必须受单写者目录约定约束（T3 安全前提） |
| **CAP-TIMER** | QwenPaw cron（`qwenpaw cron create --agent-id ...`）+ `timer-derive.sh` 幂等派生 | U1 ✅（due_at 存 CAP-STATE，宿主时钟）U2 ✅（callback 幂等重派生）U3 ✅（判定从状态重算）U4 ⚠️ 粒度 = cron 检查周期（绑定声明，默认 5min，同 agentteams 绑定） | **心跳/cron 只做兜底唤醒，不做实时驱动**（同 agentteams 绑定）；cron 规格见 `../agentteams/cron-spec.md` |
| **CAP-NOTIFY** | `qwenpaw channels send`（控制台/QQ/钉钉/… 按已配通道） | V1 ✅（通知不落状态）V2 ✅（状态在 CAP-STATE 可重建）V3 ⚠️（allowlist 静默丢弃风险，机制同 agentteams 绑定）V4 ✅（message_id 去重）V5 ⚠️（无代码级事件面）V6 ⚠️（delivered ≠ accepted） | V3/V5/V6 缺口 = 与 agentteams 绑定相同的上游缺口；协议不得依赖 gaps 缺失 |
| **CAP-ATTN** | QwenPaw 通道私聊/控制台会话（持久展示面 = 控制台会话 + IM 私聊） | W1 ✅（幂等键写状态）W2 ✅（应答落 CAP-STATE）W3 ✅（timeout_at 存状态，cron 判定）W4 ⚠️（DM 身份 = 通道账号映射（可用））W5 ✅（DM/控制台会话 = 持久展示面：持续存在 + 可回访）W6 ⚠️（单面可用）W7 ✅（结构化选项 + option_id） | 群聊 @mention 不得作 resolve（协议红线 S4）；绑定层 bot 必须引导至 DM/控制台 |
| **CAP-SPAWN** | `spawn_subagent(fork=False)`（fresh session） | X1 ✅（fork=False = 不继承父会话；**生产已验证**；fork=True 违反 X1）X2 ✅（结构化返回）X3 ✅（状态经返回值）X4 ⚠️（无限时强制 = 上游缺口，同 agentteams 绑定） | 上下文隔离：worker native session 只调度+审查，实现全进 spawn；X4 合入前绑定层用 timeout 参数尽力（非强制） |
| **CAP-EXEC** | agent 工作区 shell（python3 标准库） | Y1 ✅ Y2 ✅（退出码语义见 core/scripts 头注释）Y3 ✅ | **pip 一律 venv 版**（同 agentteams 绑定铁律）；脚本随核心分发（不要求运行时重写） |
| **CAP-ROSTER** | roster JSON 文件（agent 配置 + 人类成员） | Z1 ✅（角色权重）Z2 ⚠️（accountable 显式配置，ABSENT 需绑定层显式返回）Z3 ✅（委托链 = 配置变更记录） | 单宿主默认 single_user；multi_user 为退化形态（无跨团队、无 arbitrator） |

**合法性判定**：本绑定当前 = **7.5/8 满足**——8 能力全部由 QwenPaw 原生机制 + 本地文件实现；X1 ✅ 生产已验证；X4 ⚠️ 时限尽力非强制（上游缺口）；CAP-NOTIFY V3/V5/V6 部分满足（与 agentteams 绑定相同的上游缺口）；S4 ⚠️ 宿主盘单点（绑定声明，无异地副本）。**标注为 reference 而非 compliant，直到 X4 时限强制合入 + V3/V5/V6 上游缺口闭合。**

## 2. 机制 → 执行载体（存储层替代 + 触发面）

协议机制 → 执行载体的映射与 agentteams 绑定一致（协议机制不变，替代的只是存储层载体）：

| 层 | agentteams 绑定载体 | 本绑定载体 |
|---|---|---|
| 任务级状态（task meta） | TeamHarness task meta | 每 agent 本地 JSON 状态文件（工作区状态目录） |
| artifact / decision_log | MinIO / RustFS 对象 | 本地文件系统 / 共享卷路径（`storage_adapter: local`） |
| 团队名册 | Team CRD | roster JSON 文件 |
| room / 通知频道 | Matrix Room | QwenPaw 通道（DM / 控制台会话） |
| 调度 | QwenPaw cron（per Worker） | QwenPaw cron（per agent） |
| 异地备份 | MinIO | 无（绑定声明：接受 S4 风险，宿主备份由部署方自担） |

- 触发面：协议层 skill（各 agent 自带 skill）+ `qwenpaw cron` 回调；在树 9 脚本不变（见 `skill-fragments.md` §1）。
- [NO-CARRIER] 缺口：与 agentteams 绑定相同（R5 超时窗 / B-5 停摆计数 / B-6 mismatch 窗口 / decision record 的规划载体未实现）——见 `../agentteams/mapping-table.md` §2.1；实现前按"协议层触发 + 人工兜底"运行。

## 3. 原语映射

| 原语 | 机制 |
|------|------|
| human | 通道账号（roster JSON 人类条目）+ 控制台会话 |
| agent | QwenPaw agent 实例（单宿主多实例） |
| leader | agent 角色实例（编译产物 SOUL.md + fragments） |
| worker | agent 角色实例 + spawn 子执行单元 |
| arbitrator | 不适用（single_user 无集群级协调角色；跨团队 handoff 机制不存在） |
| room | QwenPaw 通道（DM / 控制台会话） |
| project | 不适用（无对象存储项目空间；共享卷可模拟，权限靠目录约定） |
| task | 每 agent 本地 JSON 状态（CAP-STATE） |
| artifact | 本地 / 共享卷文件（路径契约 + 客户端 sha256 指纹） |
| decision node | NMH 文档决策树 + decision_log（本地 `decisions/` 路径） |
| channel | 控制台 / IM 通道 |
| mode | single_user（默认） |
| attention | 通道 DM + 控制台会话 + 状态文件（CAP-ATTN） |
| loop | CAP-STATE loop_state + cron 兜底 + spawn X4（尽力） |
| signal | CAP-STATE event_type（封闭清单）+ 通道消息标记（派生视图） |
