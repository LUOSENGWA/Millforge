# 运行时专名对照（非规范）

> 版本: v1.0 | 许可: Apache-2.0
> 来源: 自 `core/binding-contract.md` 的 reference mappings 表迁出（按通用词纪律移出核心契约本体）；表内容逐行保留，未重写。
> 范围: 非规范附录——运行时专名仅在本文件与各 `bindings/<runtime>/` 实现文档中出现（见 `core/binding-contract.md` 头注）。

## CAP-STATE

| 运行时 | 实现 | 层级 |
|---|---|---|
| AgentTeams (TeamHarness) | 对象存储中的 project/task meta + decision_log ref；外部一次性定时器（运行时 cron） | L2 |
| Bare QwenPaw | workspace JSON 状态文件 + git 式 append 日志；运行时 cron + HEARTBEAT | L2/L3 |
| claude-code | task 文件 + CLAUDE.md 指针；Task 工具 + ScheduleWakeup | L2 |

## CAP-STORE

| 运行时 | 实现 | 层级 |
|---|---|---|
| AgentTeams | MinIO（对象存储，`mc` CLI）+ 每团队 bucket | L1 |
| Bare QwenPaw | workspace 目录 + 文件同步机制（已声明） | L2 |
| claude-code | 仓库 files/ 目录 + git（指纹 = git hash） | L1 |

## CAP-TIMER

| 运行时 | 实现 | 层级 |
|---|---|---|
| AgentTeams | 运行时 cron（每个超时一个一次性 job；文本自包含） | L2 |
| Bare QwenPaw | 运行时 cron + HEARTBEAT（兜底周期 10–30min） | L2/L3 |
| claude-code | ScheduleWakeup / loop 调度 | L2 |

## CAP-NOTIFY

| 运行时 | 实现 | 层级 |
|---|---|---|
| AgentTeams | Matrix room / DM（channel send） | L1 |
| Bare QwenPaw | channels send（DM）+ room @mention | L1/L3 |
| claude-code | Task 结果消息 + 父会话 | L1 |

## CAP-ATTN

| 运行时 | 实现 | 层级 |
|---|---|---|
| AgentTeams | Matrix DM @human + 运行时一次性定时器 | L2 |
| Bare QwenPaw | DM 通道 + HEARTBEAT 兜底 + 运行时 cron | L2/L3 |
| claude-code | 父会话的 AskUserQuestion（持久展示面；群聊不适用） | L1 |

## CAP-SPAWN

| 运行时 | 实现 | 层级 | X4 |
|---|---|---|---|
| QwenPaw (bare) | `spawn_subagent`（fork=False; background=false） | L1 | ✅（版本化 3600s 硬时限——运行时强制执行；绑定必须声明版本） |
| AgentTeams (Worker) | Worker = CAP-SPAWN 实例（运行时调度 worker 容器） | L1 | ✅（运行时的任务超时；绑定必须声明） |
| claude-code | `Task` 工具（subagent） | L1 | ⚠️（Task 工具无内置时限；绑定须用 ScheduleWakeup + 状态派生补时限；**补充必须确定性（L2），不得行为式（L3）**） |

## CAP-EXEC

| 运行时 | 实现 | 层级 |
|---|---|---|
| QwenPaw (bare) | execute_shell_command（容器本地） | L1 |
| AgentTeams | worker 容器 shell + docker exec（宿主） | L1 |
| claude-code | `Bash` 工具（沙箱） | L1 |

## CAP-ROSTER

| 运行时 | 实现 | 层级 |
|---|---|---|
| AgentTeams | 对象存储中的团队 roster（team.json / agent 配置） | L2 |
| Bare QwenPaw | workspace roster 文件（roster.json） | L2 |
| claude-code | 项目级 roster 文件 | L2 |
