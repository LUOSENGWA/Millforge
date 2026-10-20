# AgentTeams 参考绑定（reference）

> 千锻核心与 **AgentTeams 编排层**（controller + worker 池）的映射。**本绑定运行时不敏感**：控制面 = AgentTeams；worker 运行时可替换（参考运行时：QwenPaw；亦含 copaw / OpenClaw / Hermes 等）。
> 本绑定是**参考绑定，不是唯一绑定**——协议合法性由 `core/binding-contract.md` 的 8 能力判定，
> 任何运行时满足 8 能力 + 不变式即可构成合法绑定（`bindings/single-agent`、`bindings/coding-cli` 是另两个参考实现）。
> **通用词纪律**：本目录是运行时专名（spawn_subagent / QwenPaw cron / channels send / mc / Matrix / MinIO-RustFS / dashboard）的**唯一合法出现面**。

## 索引（正文文档）

| 文档 | 内容 |
|------|------|
| `mapping-table.md` | CAP→机制映射 + 14 机制×执行载体 + 原语映射（**单一事实源**；本 README §1 为其一致摘要） |
| `skill-fragments.md` | CAP-SPAWN/CAP-EXEC skill 面（在树 9 脚本 + spawn 片段 + 三层审核链） |
| `cron-spec.md` | CAP-TIMER 绑定规格（U1–U4 + 注册/清理 + 兜底唤醒红线） |
| `deployment-guide.md` | 拓扑 + 编译→部署链 + filesync 写后协议 + 失败序列与恢复 |
| `s3-storage.md` | S3 对象存储语义核验（T1–T3）+ CAS 定位 + storage_adapter 枚举 + 8 脚本审计 |

## 1. CAP → 机制映射表

| 能力 | AgentTeams/QwenPaw 机制 | 不变式满足情况 | 风险/备注 |
|------|------------------------|--------------|-----------|
| **CAP-STATE** | Worker 容器本地 JSON（`.qwenpaw/workspaces/default/` 下的状态文件）+ 文件锁 CAS；任务级状态另可落 TeamHarness task meta | S1 ✅（本地盘持久）S2 ✅（文件锁；单机单写者）S3 ✅（JSONL append）S4 ⚠️ | 容器重建丢状态 → **状态必须同步 MinIO 备份**（见 §3 filesync）；`mc` 推送确认前不算持久（T2 执行细则） |
| **CAP-STORE** | MinIO / RustFS（S3 兼容），路径寻址；`mc cp` 写入 | T1 ✅（**客户端算 sha256**，ETag 不可当指纹）T2 ✅（S3 read-after-write 强一致 + 同步层 uploaded 回执）T3 ✅（**链式模拟**：`decisions/<task>/<seq>.json` 新对象链，不做同 key append） | 热 key 不做同对象 append（S3 conditional PUT 串行化）；CAP-STATE 不用对象存储 conditional PUT 模拟 CAS（对象级 ≠ 键值级） |
| **CAP-TIMER** | QwenPaw cron（`qwenpaw cron create --agent-id ...`）+ `timer-derive.sh` 幂等派生 | U1 ✅（due_at 存 CAP-STATE，容器时钟）U2 ✅（callback 幂等重派生）U3 ✅（判定从状态重算，不存"已处理"标记）U4 ⚠️ 粒度 = cron 检查周期（绑定声明，默认 5min） | **心跳/cron 只做兜底唤醒，不做实时驱动**（v2.41 定案）；实时驱动 = 事件触发 + 状态机副作用 |
| **CAP-NOTIFY** | QwenPaw `channels send`（QQ/Matrix 频道）+ Matrix Room @mention | V1 ✅（通知不落状态）V2 ✅（状态在 CAP-STATE 可重建）V3 ⚠️ **已知缺陷：allowlist 静默丢弃无 gaps**（#160/#169 生产实证）V4 ✅（message_id 去重）V5 ⚠️ 无代码级事件面（= PR-UX-2 缺口）V6 ⚠️ delivered ≠ accepted | **V3/V5/V6 缺口 = 上游 PR 线（PR-UX-2/3/4）**；PR 合入前绑定标注"部分满足"，协议不得依赖 gaps 缺失 |
| **CAP-ATTN** | QwenPaw 频道私聊（DM Room）+ 本地状态文件记录应答 | W1 ✅（幂等键写文件名/状态）W2 ✅（应答落 CAP-STATE）W3 ✅（timeout_at 存状态，cron 判定）W4 ⚠️ **DM 身份 = Matrix user_id 映射（可用）**；群聊 @mention 不得作 resolve（S4）W5 ✅（DM Room = 持久展示面：持续存在+可回访）W6 ⚠️ 无多面同步（单面可用）W7 ✅（结构化选项 + option_id） | 群聊非应答面是**协议红线**（S4），绑定层 bot 必须引导至 DM |
| **CAP-SPAWN** | QwenPaw `spawn_subagent(fork=False)`（fresh session） | X1 ✅（fork=False = 不继承父会话；**fork=True 违反 X1**）X2 ✅（结构化返回）X3 ✅（状态经返回值）X4 ⚠️ **无限时强制 = 上游缺口**（PR 线） | v2.40 上下文隔离定案：worker native session 只调度+审查，实现全进 spawn；X4 合入前绑定层用 timeout 参数尽力（非强制） |
| **CAP-EXEC** | Worker 容器内 shell（`/opt/venv/copaw/bin/python3` + 标准库）；**pip 一律 venv 版**（#226 铁律） | Y1 ✅ Y2 ✅（退出码语义见 core/scripts 头注释）Y3 ✅ | 脚本随核心分发（不要求运行时重写）；watchdog **调度部分**是本绑定实现（cron + 状态文件路径），逻辑部分 = 核心参考实现 |
| **CAP-ROSTER** | Team CRD / agent 配置（roster 文件：member_id/role/weight） | Z1 ✅（角色权重）Z2 ⚠️（accountable 显式配置，ABSENT 需绑定层显式返回）Z3 ✅（委托链 = 配置变更记录） | roster 变更 = R1 人锁；allowlist 配置变更必须验证生效（权限墙熔断配套） |

**合法性判定**：本绑定当前 = **7.5/8 满足**——CAP-NOTIFY V3/V5/V6 部分满足（上游 PR 线闭合前），CAP-SPAWN X4 尽力非强制。**标注为 reference 而非 compliant，直到 PR-UX-2/3/4 合入 + X4 时限强制落地。**

## 2. 原语映射（§01 每个原语 → 机制）

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

## 3. 部署指南（本绑定专属）

### 3.1 编译 → 部署链

```
millforge compile <team.json> --out /tmp/build/<team>
  → <role>.soul.md × N          # 身份文件（第 0 层）
  → fragments/protocol-*.md     # 第 1 层（触发装载）
  → fragments/industry-*.md
  → spawn-specs/*.md            # 第 2 层（spawn 注入）
  → core/scripts/ 9 脚本（随核心分发，容器内可执行）
部署（每角色）:
  1. docker cp <role>.soul.md → 容器 .qwenpaw/workspaces/default/SOUL.md
     + workspace 根 SOUL.md（双位置！docker restart 后 runtime 会恢复旧文件——restart 后部署，不是前）
  2. fragments/ + spawn-specs/ → 容器工作区 protocols/ 目录（软链接防覆盖）
  3. MinIO 同步：mc cp → 对象存储（filesync 确认 uploaded 回执后才算完成，T2 执行细则）
  4. 验证：docker exec 读回文件 + 行数核对（wc -l，路径作参数）
```

### 3.2 cron 规格（CAP-TIMER 绑定参数）

```
每个活跃 task 注册（timer-derive.sh 派生）:
  qwenpaw cron create --agent-id <worker> \
    --schedule "every 5m" --task "timer-check" \
    （payload = 运行 timer-derive.sh --task-meta <ref> → 到期动作）
粒度声明: 5 分钟（U4）；due_at 精度 ≤5min 的窗口需声明
清理: task 终态（completed/cancelled）→ cron delete（防孤儿定时器）
```

### 3.3 filesync 同步层（CAP-STORE T2 执行细则绑定参数）

- 容器工作区 ↔ MinIO 的同步 = push_loop（异步）+ startup mirror_all
- **写后协议（竞态防护）**：write → 等 ≥45-60s（验证磁盘 + push uploaded 日志）→ 才允许 restart/消费（2026-09 JEV 实证：写后快速 restart 被 mirror_all 回滚）
- uploaded 回执 = push 日志 `push uploaded .../<file>` 行（绑定层轮询）

### 3.4 失败序列与恢复（T5 生产实证）

| 失败 | 检测 | 恢复 |
|------|------|------|
| Worker 容器异常（Internal error） | docker logs ERROR | restart → 重派（3 次 → 升级）；**pydantic 版本过旧 = workspace 启动失败**（venv pip 查版本，#176） |
| 状态写 MinIO 未确认 | push 日志无 uploaded | 不消费 ref（T2）；重推 + 确认 |
| allowlist 静默拦截 | 消息无错误日志消失 | 对比 agent.json access control（#160/#169）；restart 后验证 allow_from 含 human |
| cron 定时器丢失（容器重建） | task 有 due_at 无 cron | timer-derive 幂等重派生（U3：判定从状态重算） |
| spawn 挂起无返回 | X4 时限（尽力） | bounded_failure 语义；3 次 → 升级 |
| restart 后 SOUL.md 回滚 | 文件 mtime/行数 | 双位置重部署（restart 后） |

## 4. 上游 PR 线（本绑定的缺口闭合）

| PR | 闭合的缺口 | 状态 |
|----|------------|------|
| PR-UX-4 delivery_report V3 | CAP-NOTIFY V3 gaps 可见（allowlist 静默丢弃可观测） | 底稿待审 |
| PR-UX-2 事件面（代码级订阅） | CAP-NOTIFY V5 | 底稿待审 |
| PR-UX-3 多通道适配 | CAP-NOTIFY V6 delivered/accepted 区分 | 底稿待审 |
| PR-UX-1 dashboard 待办 | CAP-ATTN W5 持久展示面（第二面） | 底稿待审 |
| PR-UX-5 IM 卡片（可选） | W6 多面关闭 | 可选 |
| （X4 时限强制） | CAP-SPAWN X4 | 待立项 |

**合入序**：UX-4 → UX-2 → UX-3 → UX-1 → UX-5（依赖序）。

### 4.1 平台线（区别于 UX 线：TeamHarness filesync + AgentTeams 平台层）

| Issue | 闭合的缺口 | 状态 |
|----|------------|------|
| TH-1 filesync 启动 mirror 覆盖 | CAP-STATE S4 不可静默丢失（§3.3 写后 45–60s 协议目前是人工兜底） | 已提交（#1391） |
| AT-1 Worker 入会路径 | 任务可达性（房间成员=任务可见性；create-project.sh 凭据代 join 凭证缺失即死胡同） | 已提交（#1390） |
| AT-2 create-project.sh --team 展开 | 建群拉人铁律（全队入会；目前 Manager 每次手工展开 roster） | 已提交（#1389） |
| AT-3 allowlist 默认排除人类 + 双系统字段方言互搏 | CAP-NOTIFY V3 生成侧（零信号静默丢弃；集群当前靠 permissive 兜底"安全"） | 已提交（#1388） |
| AT-4 镜像未 pin pydantic | 运行时可启动性（2026-07 生产事故：qwenpaw 用 2.12 独有 API，镜像解析 2.11.1 → workspace 启动级联失败） | 已提交（#1392） |

**与 UX 线的关系**：AT-3 是 UX-4 `gaps[]` 的生成侧根因（生成器不把人类写进 allowlist，delivery_report 也枚举不出"谁该在不在"）；提 issue 序建议：AT-3 → TH-1 → AT-1 → AT-2 → AT-4。

## 5. S3 不敏感核验（MinIO → RustFS 迁移）

- fingerprint = **客户端 SHA-256**（ETag 不是内容哈希，多段上传 ETag 是分片哈希的哈希）
- 32 并发 `If-None-Match: *` PUT 验证 exactly-one-winner（迁移前必测）
- append = 链式新对象（不做同 key append）
- 8 核心脚本**零对象存储 CLI 调用**（只处理本地文件/stdin/stdout；I/O 全由 CAP-STORE adapter 负责）
- 迁移后 golden test 全量回归（decision_log/contract/handoff 行为一致性）
