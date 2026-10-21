# 并行任务派发场景契约（M4）

> 场景能力 = CAP-STATE + CAP-STORE + CAP-TIMER + CAP-NOTIFY + CAP-EXEC + CAP-SPAWN 的**复合能力**：一个控制面并行派发 N 个任务，每任务独立执行体 + 独立工作目录，状态/回执/通知全落盘、可机器验证。
> 本文档是 AgentTeams 线的**绑定片段**（binding fragment）：7 条不变式对运行时不敏感（任何满足 8 能力的绑定都可采纳），每条附 AgentTeams 实锚（file:line，已逐条实读核对）+ 种子证据。
> 可复跑种子：`golden-tests/fixtures/parallel-9/`（10 任务 state.json + 7 条 inbox.jsonl 转换事件，自九任务试点归一化）。
> 可执行断言：`golden-tests/tests/test_parallel_dispatch_contract.py`（`make contract`）。
> 预算口径：默认**无预算**（仅显式声明时强制；见 `core/protocol/10-LOOP.md`）；rc=55 / rc=137 机制保留为零成本兜底。

## 0. 种子数据（fixtures/parallel-9/）

| 任务 | 终态 | exit_code | wall_s | 备注 |
|------|------|-----------|--------|------|
| P2a / P2b / P2e | running | — | — | 在跑：session_id + pid + updated_at 齐备（watchdog 输入） |
| P2c / P2d | blocked-by-gate | — | — | 派发期被拒：无 session_id / pid / started_at（零执行成本） |
| P3b / P3k | done | 0 | 63 / 59 | 正常完成 |
| P4b | failed-budget | 55 | 46 | X4 有界失败（显式预算声明下的 rc=55） |
| P4k | done | 0 | 251 | 正常完成（长任务） |
| P4x | killed | 137 | 30 | 外部 kill，终态照常落盘 |

终态集合（封闭）：`done` / `failed-budget` / `killed` / `blocked-by-gate`；过程态：`running`。

## 1. 七条不变式（PD-1 … PD-7）

### PD-1 唯一真相落盘（CAP-STATE S1/S2/S3）

**不变式**：任务状态是单一真相，必须原子写盘（tmp + rename）且读侧随时可重读；转换事件 append-only（inbox）；面板/通知/watchdog 都是**派生视图**，不是第二数据源。

**AgentTeams 实锚**：
- attention 记录 `{kind, question≤500, attempt, requestedAt, resolved, eventId}` 先写 task state（sync-first：共享存储同步确认后才向调用方报 closed；同步失败 = `retryable: true`，通知保留、状态不炸）——`plugins/teamharness/mcp/server.py:6076–6087`（retryable 块）、`:6215–6227`（记录写入 + `record["eventId"]` 回填）
- 种子证据：`parallel-9/*/state.json` 每任务一份状态文件；`inbox.jsonl` append-only 7 事件；读侧（watchdog/面板）只从盘上派生

### PD-2 派发期冲突闸（新不变式）

**不变式**：派发时若候选任务的 `files_to_touch` 与任一活跃任务相交 → **拒派**（写 `blocked-by-gate` 状态 + inbox 事件，注明原因）；拒绝发生在 spawn 之前，**零执行成本**（不产生 session、不耗 token）。

**AgentTeams 实锚（相邻语义 + 缺口声明）**：
- 派发状态幂等基础：改派走 `_canonical_assignee` 比对——同一 assignee 重派复用既有状态（不产生重复事件），不同 assignee 才是新通知——`plugins/teamharness/mcp/server.py:2994`（函数）、`:5421`（比对，#1324）
- **缺口**：冲突闸本身是协议层派发前闸（本契约新增），AgentTeams 上游无派发期等价物；种子中 2 次正确拒派（P2c/P2d，`detail: "files_to_touch overlap with active task"`）来自控制面派发工具，不在本运行时内。采纳本契约的运行时必须实现该闸（或在绑定声明中显式降级）。

### PD-3 终态先于清理

**不变式**：终态写入 state + inbox **之后**才允许清理（deregister：释放会话/删定时器）；清理失败不致命——真相已在盘上，清理只是视图收敛。

**AgentTeams 实锚**：
- sync-first 同 PD-1：终态/resolved 必须**先落共享存储再通知调用方**；失败路径保留通知并标 `retryable`——`plugins/teamharness/mcp/server.py:6076–6087`
- 清理动作本绑定实现 = 任务终态 → `cron delete`（见 `cron-spec.md`）；顺序红线 = state/inbox 先、cron 后
- 种子证据：5 个终态任务（P3b/P3k/P4b/P4k/P4x）全部 state.json 有 `finished_at` 且 inbox 有对应事件，二者齐备后才发生清理

### PD-4 回执是一等 artifact（CAP-STORE T1/T2/T5）

**不变式**：终态任务必须产出**结构化回执**：`status` 枚举 + `exit_code` + `wall_s`（+ `files_to_touch` / receipt ref / worktree / tokens 视绑定能力）；`self_check` 逐验收项；`known_gaps` 显式声明。回执可寻址、可指纹、机器可验——**有界失败（rc=55/137）也是一等终态**，不是错误码。

**AgentTeams 实锚**：
- coding-runs 读契约（run 记录：status / exit_code / wall 可经 API 读取，一个 API 一个面板）——`agentteams-controller/internal/server/http.go:162–163`（`GET /api/v1/coding-runs`、`GET /api/v1/coding-runs/{taskID}/runs/{run}`，#1365/#1381）
- 假完成护栏（回执必须诚实：无产出回合标「本回合无产出」而非「已完成」）——`plugins/agentteams-matrix-channel/agentteams_matrix/channel.py:4510`（#1320）
- 任务 artifact 端点（回执可寻址面）——`agentteams-controller/internal/server/http.go:151`
- 种子证据：5 个已执行终态任务全部带 `exit_code` + `wall_s`；P4b `rc=55`（预算有界失败）、P4x `rc=137`（killed）

### PD-5 通知 3 行指针化（CAP-NOTIFY；分层条款见 `core/protocol/09-GOVERNANCE.md` §8）

**不变式**：任务转换通知 = 固定 3 行（任务标识 + 终态 + 指针），**无 payload**（不内联产出内容）、**无需回复**、**禁止提问**；完整内容一律读 state / 回执获得（指针化）。human tier 固定 3 行人话格式，失败态必须同入 human tier（不静默）。

**AgentTeams 实锚（现状 + 缺口）**：
- 现状：`_send_attention_notification` 单路径 Matrix 文本，**内联 question≤500**（payload 化、提问式——违反本不变式的两处）——`plugins/teamharness/mcp/server.py:5205`；幂等 txn `attention-{task_id}-{kind}-{attempt}`——`:5253`
- **缺口**：AgentTeams 通知现为「提问 + 内联预览」形态，未收敛到 3 行指针化分层格式；本绑定在 `compliance.json` / README §4 声明该缺口，上游收敛前协议不得假设通知可携带完整 payload

### PD-6 watchdog 兜底（CAP-TIMER U3/U5）

**不变式**：watchdog 周期（绑定声明粒度）扫盘：`updated_at` 超时且 pid 存活 = **stall**（人类可见告警）；pid 已死且状态非终态 = **crash**（重派或升级）。判定由确定性脚本从 CAP-STATE 派生（幂等重派生，U3），不得依赖「记住上次检查」。

**AgentTeams 实锚**：
- 项目事件 feed（只读转换历史，watchdog 可交叉核对 state 与历史是否一致）——`agentteams-controller/internal/server/http.go:156`（`GET /api/v1/projects/{id}/events`，#1233）
- `timer-derive.sh`（核心参考实现，CAP-TIMER U3 幂等重派生）+ 本绑定 cron 周期 = 扫描粒度声明（`cron-spec.md`，默认 5min，U4）
- 种子证据：running 任务（P2a/P2b/P2e）全部带数值 `pid` + `updated_at`（watchdog 两输入齐备）；终态任务 inbox `ts` == state `finished_at`（转换可派生、可对账）

### PD-7 隔离 = 自建 worktree（CAP-SPAWN X1）

**不变式**：每任务运行在**自建 worktree**（独立分支 + 独立目录）；执行体 fresh context（不继承父对话历史，X1 硬门）；跨任务可见性只经 state / 回执（磁盘），不共享工作目录。

**AgentTeams 实锚**：
- 每任务唯一 `session_id`（种子：8 个已 spawn 任务 = 8 个不同 UUID）+ fresh-session 机制（本绑定 CAP-SPAWN = `fork=False`，见 `README.md` §1；fork=True 违反 X1）
- worktree 的创建工具（`git worktree add`）与分支命名 = **绑定参数**（控制面派发工具实现细节）；X1 上下文隔离语义 = 协议层。种子数据只承载可验证部分（session_id 唯一性）

## 2. 采纳判据（对任何运行时）

1. PD-1…PD-7 逐条实现，或在 `compliance.json` gaps 中显式声明降级（未声明 = 非法绑定，见 `core/binding-contract.md`）
2. 种子夹具可复跑：`golden-tests/fixtures/parallel-9/` 上的 `test_parallel_dispatch_contract.py` 全绿
3. 终态集合封闭于 §0；新增终态必须先改本文档 + 夹具 + 测试（禁止运行时私加状态）

## 3. 与 M5（通知分层）的接口

PD-5 是**指针化格式**约束；`core/protocol/09-GOVERNANCE.md` §8 是 **tier 声明**约束（machine / agent / human）。两者正交：同一条转换事件按 tier 投不同面，每个面的 payload 都必须满足 PD-5（3 行、无 payload、无提问）。
