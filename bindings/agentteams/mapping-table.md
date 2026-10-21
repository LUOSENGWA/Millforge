# 机制 × 运行时映射表（AgentTeams + QwenPaw）

> 本文件是 `bindings/agentteams/` 映射的**单一事实源**（`README.md` §1 为其一致摘要）。
> 通用词纪律：本目录是运行时专名的唯一合法出现面（`core/protocol/00-OVERVIEW.md` §S：核心条文/契约/模板/测试只允许 CAP-* 编号 + 通用词）。

## 1. CAP → 机制映射（8 能力基线）

| 能力 | AgentTeams/QwenPaw 机制 | 不变式满足情况 | 风险/备注 |
|------|------------------------|--------------|-----------|
| **CAP-STATE** | Worker 容器本地 JSON（`.qwenpaw/workspaces/default/` 下的状态文件）+ 文件锁 CAS；任务级状态另可落 TeamHarness task meta | S1 ✅（本地盘持久）S2 ✅（文件锁；单机单写者）S3 ✅（JSONL append）S4 ⚠️ | 容器重建丢状态 → **状态必须同步 MinIO 备份**（见 `deployment-guide.md` filesync 节）；`mc` 推送确认前不算持久（T2 执行细则） |
| **CAP-STORE** | MinIO / RustFS（S3 兼容），路径寻址；`mc cp` 写入 | T1 ✅（**客户端算 sha256**，ETag 不可当指纹）T2 ✅（S3 read-after-write 强一致 + 同步层 uploaded 回执）T3 ✅（**链式模拟**：`decisions/<task>/<seq>.json` 新对象链，不做同 key append） | 热 key 不做同对象 append（S3 conditional PUT 串行化）；CAP-STATE 不用对象存储 conditional PUT 模拟 CAS（对象级 ≠ 键值级） |
| **CAP-TIMER** | QwenPaw cron（`qwenpaw cron create --agent-id ...`）+ `timer-derive.sh` 幂等派生 | U1 ✅（due_at 存 CAP-STATE，容器时钟）U2 ✅（callback 幂等重派生）U3 ✅（判定从状态重算，不存"已处理"标记）U4 ⚠️ 粒度 = cron 检查周期（绑定声明，默认 5min） | **心跳/cron 只做兜底唤醒，不做实时驱动**；实时驱动 = 事件触发 + 状态机副作用 |
| **CAP-NOTIFY** | QwenPaw `channels send`（QQ/Matrix 频道）+ Matrix Room @mention | V1 ✅（通知不落状态）V2 ✅（状态在 CAP-STATE 可重建）V3 ⚠️ **已知缺陷：allowlist 静默丢弃无 gaps**（#160/#169 生产实证）V4 ✅（message_id 去重）V5 ⚠️ 无代码级事件面V6 ⚠️ delivered ≠ accepted | **V3/V5/V6 缺口为已知实现缺口（后续版本闭合）**；缺口闭合前绑定标注"部分满足"，协议不得依赖 gaps 缺失 |
| **CAP-ATTN** | QwenPaw 频道私聊（DM Room）+ 本地状态文件记录应答 | W1 ✅（幂等键写文件名/状态）W2 ✅（应答落 CAP-STATE）W3 ✅（timeout_at 存状态，cron 判定）W4 ⚠️ **DM 身份 = Matrix user_id 映射（可用）**；群聊 @mention 不得作 resolve（S4）W5 ✅（DM Room = 持久展示面：持续存在+可回访）W6 ⚠️ 无多面同步（单面可用）W7 ✅（结构化选项 + option_id） | 群聊非应答面是**协议红线**（S4），绑定层 bot 必须引导至 DM |
| **CAP-SPAWN** | QwenPaw `spawn_subagent(fork=False)`（fresh session） | X1 ✅（fork=False = 不继承父会话；**fork=True 违反 X1**）X2 ✅（结构化返回）X3 ✅（状态经返回值）X4 ⚠️ **无限时强制 = 上游缺口** | 上下文隔离：worker native session 只调度+审查，实现全进 spawn；X4 合入前绑定层用 timeout 参数尽力（非强制） |
| **CAP-EXEC** | Worker 容器内 shell（`/opt/venv/copaw/bin/python3` + 标准库）；**pip 一律 venv 版**（运行时约束） | Y1 ✅ Y2 ✅（退出码语义见 core/scripts 头注释）Y3 ✅ | 脚本随核心分发（不要求运行时重写）；watchdog **调度部分**是本绑定实现（cron + 状态文件路径），逻辑部分 = 核心参考实现 |
| **CAP-ROSTER** | Team CRD / agent 配置（roster 文件：member_id/role/weight） | Z1 ✅（角色权重）Z2 ⚠️（accountable 显式配置，ABSENT 需绑定层显式返回）Z3 ✅（委托链 = 配置变更记录） | roster 变更 = R1 人锁；allowlist 配置变更必须验证生效（权限墙熔断配套） |

**合法性判定**：本绑定当前 = **7.5/8 满足**——CAP-NOTIFY V3/V5/V6 部分满足（缺口闭合前），CAP-SPAWN X4 尽力非强制。**标注为 reference 而非 compliant，直到缺口闭合 + X4 时限强制落地。**

## 2. 机制 → 执行载体映射（14 机制）

**映射原则**：每个机制的"执行载体"必须是机制地图中已存在的具体组件（taskflow 动作 / server.py / watchdog cron / QwenPaw cron / 心跳 / skill 脚本 / MinIO 文件）。**状态存储位置优先选 task meta 或 MinIO 文件**；Matrix 只作通知，不作状态。凡载体缺失标 [NO-CARRIER]，并给出最小可行载体方案。

| 机制 | 执行载体 | 状态存哪 | restart 幸存 | 触发者 |
|---|---|---|---|---|
| **R2 加权多数计票** | skill 脚本 `aggregate-vote.sh`（Leader 侧）+ task meta 的 `attention[]` 中已收集的投票 | task meta：`attention[].votes[]`（每票含 `user_id` / `weight` / `decision_class` / `received_at`） | ✅（task meta 持久化在 taskflow 存储） | 协议层触发（attention 超时或收到足够票数时） |
| **R5 重开 + 24h/4h 超时窗** | **[NO-CARRIER]** → 方案：`nmh-watchdog.sh` 新增模式 `reopen-window`（cron */2 检查 `reopen_requested_at` + `decision_class` → 超时降权） | task meta：`decision_nodes[].lock` 内 `{locked_by, locked_at, reopen_requested_at, reopen_status}`；task-context.json 镜像 `pending_reopens[]` | ✅（task meta + 状态文件） | watchdog cron |
| **R6 attention 路由 + 30min/2h 超时** | taskflow `request_attention`（已承载 kind/超时/幂等）；**multi_user 路由需二次路由**（见 Task 4） | task meta：`attention[]` 现有字段 + 新增 `routing` 子字段 `{accountable, cc[], routed_at, timeout_class}` | ✅（server.py 持久化 attention[]） | Worker/Leader 调用 taskflow；超时由 watchdog 或 QwenPaw cron 检查 |
| **B-1 decision_log 三层 schema 校验** | 第 1 层：skill 脚本 `validate-decision-log.sh`（父 Worker 派发 **验收前** 执行，不在 spawn 返回时——spawn 是 LLM，不能自我校验）；第 2 层：`detect-conflict.py`（Task 2-2）；第 3 层：critic 验收脚本检查指纹 | MinIO：`decisions/<task_id>/<spawn_id>.decision.json`（权威）；task meta：`decision_logs[]` 只存 `{ref, sha256_8, validated: bool}` 索引 | ✅（MinIO + task meta 索引） | 父 Worker skill 在合并前调用；第 3 层由 critic 调用 |
| **B-2 冲突检测 Step 1–3 纯函数** | Python 脚本 `detect-conflict.py`（无 LLM，纯字段比对） | 输出候选冲突对到 MinIO：`decisions/<task_id>/conflict-candidates.json`；task meta：`merge_state: {candidates_ref, resolved: bool}` | ✅（MinIO 文件） | 父 Worker skill 在 B-1 第 1 层通过后调用 |
| **B-3 重验（semver + 指纹 + 兼容性报告）** | skill 脚本 `contract-revalidate.sh`（比较 `contract_ref@semver` 与返回指纹 + 读取兼容性报告 artifact） | task meta：`contract_state: {pinned_ref, pinned_fingerprint, returned_fingerprint, diff_class, revalidated: bool}`；MinIO：兼容性报告路径 | ✅（task meta + MinIO） | 父 Worker 验收前调用；或 critic 第 3 层发现指纹不匹配时回退调用 |
| **B-5 attention_stall_count 熔断计数** | **[NO-CARRIER] 直接计数** → 方案：`nmh-watchdog.sh` 新增模式 `attention-stall`（cron */2 扫描 `attention[]` 中连续 timeout 且 resolved=false 的条目）；计数写入 task meta | task meta：`attention_stall_count`（int）+ `attention_stall_level`（normal / escalated / frozen）；task-context.json 镜像 `attention_stall` | ✅（task meta + 状态文件） | watchdog cron |
| **B-6 verification_mismatch 计数 + 24h 窗口** | **[NO-CARRIER]** → 方案：`nmh-watchdog.sh` 新增模式 `mismatch-window`（cron */2 检查 `verification_mismatch[]` 的 `opened_at` → 24h 超时维持原 spec） | task meta：`verification_mismatch[]`（每项 `{criterion_id, critic_alternative, opened_at, status}`）+ `verification_mismatch_count` | ✅（task meta + 状态文件） | critic 通过 NMA 评分卡写入；watchdog 检查超时 |
| **B-10 decision_class_mismatch + saga 补偿** | 事件写入：Leader/Worker skill 脚本 `emit-class-mismatch.sh`；补偿指令生成：`saga-compensate.py`（读 dependency graph + 正向操作日志 → 反向补偿序列） | task meta：`decision_class_mismatches[]` + `saga_compensation: {required: bool, directive_ref}`；MinIO：补偿指令 `saga/<task_id>/compensation.json` | ✅（task meta + MinIO） | 执行期 Agent 发现误分类时调用 emit 脚本；`saga-compensate.py` 由协议层/Leader 触发 |
| **C-3 locked_spec_consistency_check** | **两层方案**（见 Task 2-7）：① 规则层：`consistency-check.py` 做**字段级/枚举级**二元比对（`acceptance_criteria` 若为结构化字段）；② LLM 层：仅当规则层无法判定（自然语言 acceptance）时，调用一个**受限分类 spawn**（不是自由生成，只输出 `{contradict: true/false, criterion_id, reason}`） | task meta：`r6_responses[]` 中每条含 `{response_id, consistency_check: {result, checked_by, checked_at}}`；被拒收的回答标记 `rejected_by_consistency: true` | ✅（task meta） | R6 回答写回前由协议层/skill 调用；LLM 分类 spawn 由父 Worker 派发 |
| **C-2 contract_snapshot 写回** | R6 回答写回 task state machine 时，skill 脚本 `write-contract-snapshot.sh` 同步写入 | task meta：`contract_snapshot: {contract_ref, fingerprint, checked_at}`；task-context.json 镜像 | ✅（task meta） | R6 回答写回流程（协议层/skill） |
| **G8 聚合结果写回 schema** | `write-aggregation-result.sh`（Task 2-8 计票脚本的写回部分） | task meta：`aggregation_result: {decision_id, rule_applied, votes[], outcome, dissent[], decided_at}`；task-context.json 镜像 `last_aggregation` | ✅（task meta） | 计票完成后由协议层/skill 写回 |
| **decision record 写入** | skill 脚本 `write-decision-record.sh`（append-only 到 MinIO JSONL）；task meta 只存 `decision_record_ref` | MinIO：`decisions/<task_id>/record.jsonl`（每行一条：`{decision_id, type, actor, outcome, dissent[], locked_by, overridden_by[], timestamp}`） | ✅（MinIO append-only） | 任何决策动作（R1–R6）完成后由协议层/skill 调用 |

### 2.1 [NO-CARRIER] 载体缺口（规划中，未实现）

| 缺口机制 | 最小载体（规划） | 为什么不用其他 |
|---|---|---|
| R5 超时窗 | `nmh-watchdog.sh` 新 cron 模式 | QwenPaw cron 可做但增加平台耦合；心跳粒度 30min 太粗（R5 可逆窗 4h，30min 检查可接受；但 watchdog */2 已有基础设施，复用成本最低） |
| B-5 stall 计数 | `nmh-watchdog.sh` 新模式 | taskflow 无"扫描 task meta 并计数"的动作；上游 PR 可加但非必需 |
| B-6 mismatch 窗口 | `nmh-watchdog.sh` 新模式 | 同上 |
| decision record | MinIO append-only JSONL + skill 写脚本 | 放 task meta 会撑爆 meta；Matrix 不可靠 |

> **在树状态**：上表载体中，`aggregate-vote.sh` / `validate-decision-log.sh` / `detect-conflict.py` / `contract-revalidate.sh` / `attention-stall.sh` / `verification-mismatch-window.sh` / `saga-compensate.py` / `consistency-check.py` / `timer-derive.sh` 已在树（`core/scripts/`，9 件）；`nmh-watchdog.sh` / `emit-class-mismatch.sh` / `write-contract-snapshot.sh` / `write-aggregation-result.sh` / `write-decision-record.sh` 为规划载体，**尚未实现**，实现前相关机制只能按"协议层触发 + 人工兜底"运行。

## 3. 原语映射

| 原语 | 机制 |
|------|------|
| human | Matrix 用户（roster 中的人类条目，如 `@human-a`/`@human-b`）+ IM 通道 |
| agent | QwenPaw Worker 容器（`python3 -m copaw_worker.run_copaw_app app`，qwenpaw runtime） |
| leader | Worker 角色实例（skeleton/leader 编译产物部署到 `.qwenpaw/workspaces/default/`） |
| worker | Worker 角色实例 + spawn 子执行单元 |
| arbitrator | Manager 容器（`agentteams-manager`，qwenpaw runtime，仅 single_user） |
| room | Matrix Room（team room / project room / DM Room） |
| project | TeamHarness project + MinIO 项目空间 `{proj}/brief.md+meta+artifacts/` |
| task | TeamHarness task + task meta（CAP-STATE） |
| artifact | MinIO 对象（路径契约 + 客户端 sha256 指纹） |
| decision node | NMH 文档决策树 + decision_log（MinIO `decisions/`） |
| channel | QQ 原始通道 / 控制台 |
| mode | single_user（生产现状：一个 human 一个集群） |
| attention | DM Room + 状态文件（§CAP-ATTN） |
| loop | CAP-STATE loop_state + cron 兜底 + spawn X4 |
| signal | CAP-STATE event_type（封闭清单）+ 频道消息标记（派生视图） |

## 4. NMA 消息类型 → 执行载体（Part A 通信层）

| NMA type | 本绑定载体 | 状态 |
|----------|-----------|------|
| `DELEGATE` | taskflow `delegate_task`（`spec` + `assignedTo` + `taskId` + `projectId`） | ✅ 在树 |
| `ACK` | taskflow `ack_task` | ✅ 在树 |
| `PROGRESS` | taskflow `report_progress`（不改状态、不通知 leader） | ✅ 在树 |
| `COMPLETE` | taskflow `submit_task`（`summary` + `deliverables`）+ SIG-COMPLETE | ✅ 在树 |
| `QUERY` | 无结构化载体（taskflow 明确排除 direct questions）→ 群聊文本 | ⚠️ 缺口：结构化 QUERY 需新增动作（或用 `request_attention(kind=other)` 过渡） |
| `DECISION_REQUEST` | taskflow `request_attention`（kind=decision）+ CAP-ATTN W7 | ✅ 在树 |
| `HANDOFF` | `07-HANDOFF` 文档 + 共享存储 handoff 文件（无 API） | ✅ 文档载体 |
| `ESCALATE` | taskflow `request_attention`（kind=escalation） | ✅ 在树 |

**字段落点与缺口**：`taskId` / `projectId` = 动作参数；`refs[]` ≈ `deliverables` / artifact ref。`message_id` 无独立参数——幂等由动作层保证（`submit_task` 的 `submissionId` 身份 + 任务态校验）；`deadline` / `deadline_fallback` 无载体（由 CAP-TIMER 外部兜底）。

## 5. NMH §8 执行期随时问 → 载体

| 条款 | 载体 | 状态 |
|------|------|------|
| 结构化决策请求（options / recommendation / impact / deadline） | taskflow `request_attention`（kind=decision；payload 结构由调用约定，非 schema 强制） | ✅ 在树（选项结构非强制） |
| 持久展示面（W5） | DM Room（W5 已满足）；dashboard 待办第二面 | ✅ DM / ⚠️ dashboard 面缺口（见 README §4） |
| 代码级事件（V5） | 事件订阅面 | ⚠️ 缺口（V5 未实现，见 README §4） |
| 应答写 CAP-STATE → 从状态恢复 | `request_attention` `payload.resolved=true` 关闭记录 + 任务态重读 | ✅ 在树 |
| 超时兜底 | CAP-TIMER（due_at + cron 判定） | ✅ 在树（无 deadline 字段，CAP-TIMER 外部兜底） |
