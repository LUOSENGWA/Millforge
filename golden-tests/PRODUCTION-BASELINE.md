# 生产基线映射（golden gate 审计锚）

> v1.0 | 2026-10-19 | 悬置问题 #1 闭合文档

## 1. 基线定义与门语义

**生产基线** = `fixtures/production-baseline/` 5 份 SOUL（bizmarket 团队，multi_user 首编基线，9/6 手编 v2.0 + 后续生产热补丁；占位化副本，占位映射见 §5）。

**门语义（重要）**：golden gate 的 diff 对象是**冻结的编译基线**（`baseline/` 目录，编译器对 `fixtures/bizmarket-team.json` + `fixtures/example-biz-team.json` 的确定性输出），**不是**生产基线原文。原因：

- 生产 SOUL 是**上一代协议**（SATCOM v1.0/NMProtocol v3.0 时代手编 + 生产事故热补丁），编译器实现的是**协议层 v1.0**（千锻 8 轮审查冻结）。
- 两代共享同一 DNA（三要素/双通道/声明-验证绑定/权限墙熔断/上下文隔离），但术语与结构已升级（R1-R6 决策类、X4 有界时限、context_refs、decision_log、scorecard）。
- 强制字节级复现 = 把编译器退回旧协议，与 v1.0 冻结定案矛盾。

**因此 gate = 双重门**：
1. **编译确定性门**（CI 自动）：模板/片段/编译器变更 → 编译输出 vs `baseline/` diff，非空 = 必须显式更新基线并说明（协议回归零静默）。
2. **生产溯源门**（人工审计，本文件）：生产基线的每条协议条款必须能映射到新协议落点（§2-§4）；映射缺失 = 协议内容在升级中丢失 = gate 红。协议层每次变更必须重跑本映射。

## 2. Worker 通用条款映射（5 角色共有）

| # | 生产条款（旧） | 新协议落点（v1.0） | 状态 |
|:--:|------|------|:--:|
| W1 | 第一规则：职责边界 + 拒绝必须上报 | `skeleton/worker.md` 铁律 + `fragments/protocol-contract.md`（scope/out_of_scope 契约） | ✅ 吸收（升级为结构化契约） |
| W2 | 群聊 @mention 规则（不 @ = 自言自语） | `fragments/protocol-attention-ux.md` + binding 层（Matrix mention 格式见 bindings/agentteams/README） | ✅ 吸收（binding 特化保留在绑定层） |
| W3 | v2.40 上下文隔离（native = 调度+审查；实现 = spawn） | `skeleton/worker.md` 铁律 #1（编译物显式保留 "v2.40 定案" 出处） | ✅ 吸收 |
| W4 | Spawn 可用性探测（工具列表无 spawn 类工具 → 原生执行） | `fragments/protocol-task-lifecycle.md` spawn 纪律（"不调用不存在的工具，不声称已 spawn" 语义） | ✅ 吸收 |
| W5 | 核心循环（三要素 → 拆解 → spawn → 审查 → 整合） | `skeleton/worker.md` 工作流六步（三要素 + 结构化 acceptance + decision_class） | ✅ 吸收（升级：结构化验收 + 决策类） |
| W6 | spawn 注入上下文五要素（数据路径/目标/禁止/交付契约/数据契约） | `spawn-specs/*.md` + `fragments/protocol-task-lifecycle.md`（context_refs 文件引用 + X4 时限 + return_schema） | ✅ 吸收（升级：长上下文走文件不进消息） |
| W7 | 审查 spawn 产出（自检项；≤3 次重 spawn → 上报） | `skeleton/worker.md` 验收（结构化检查 → 证据入 scorecard；验证者 ≠ 声明者；≤3 次升级 leader） | ✅ 吸收（升级：scorecard 证据链） |
| W8 | 产出交付规则（双通道交付 + MinIO push + TASK_COMPLETED） | `fragments/protocol-task-lifecycle.md`（TASK_COMPLETED 三要素 + 强制 3-5 关键结论）+ `protocol-dual-channel.md` | ✅ 吸收（升级：强制结论 = handoff 原材料） |
| W9 | Spawn 纪律（版本化 3600s 硬线 + 超时杀签名 + 续做重派） | X4 有界时限（通用化，不绑定运行时版本）+ `protocol-task-lifecycle.md` 故障 SOP | ⚠️ 升级（版本钉 → 通用契约；运行时特化细节归 binding） |
| W10 | 团队交接节（writer↔analyst、writer↔designer 数据流） | 实例参数（team.json roles.profile/charter 声明管线）+ `fragments/industry-business.md` | 📋 实例特定（非协议；模板不硬编码成员对） |
| W11 | 角色卡（职责/内容类型/物料类型/审查维度） | 实例参数（team.json profile + domains）+ `skeleton` 域段 | 📋 实例特定 |

## 3. Leader 特有条款映射

| # | 生产条款（旧） | 新协议落点（v1.0） | 状态 |
|:--:|------|------|:--:|
| L1 | 入口双通道（IM 直连 + 频道 Bot 等价） | 实例参数（roster + binding 通道配置） | 📋 实例特定 |
| L2 | 铁律：禁止自己实现 | `skeleton/leader.md` 铁律 | ✅ 吸收 |
| L3 | 铁律：缺人必报（不自己消化/不冒名汇报） | `skeleton/leader.md` 铁律 + `protocol-governance.md` | ✅ 吸收 |
| L4 | 铁律：汇报核实（确认执行人 + 产出真实） | `protocol-governance.md`（验证者 ≠ 声明者；汇报核实） | ✅ 吸收 |
| L5 | 铁律：声明-验证绑定（说了 ≠ 做了） | `skeleton/leader.md` 铁律 #3（编译物保留） | ✅ 吸收 |
| L6 | 铁律：权限墙熔断（≥2 次 → ≤30s 切 DM） | `protocol-fuse.md`（fuse_threshold/fuse_window 实例参数） | ✅ 吸收 |
| L7 | 铁律：先汇报再确认（session 可能在确认后结束） | `protocol-dual-channel.md` + `protocol-task-lifecycle.md`（闭环顺序） | ✅ 吸收 |
| L8 | NMH 审讯锁定（探索/锁定双模式 + 七问自检 + nmh-docs 实时写入） | `fragments/protocol-nmh.md`（旧为 skill 装载，新为片段指针装载——机制升级，内容同源） | ✅ 吸收（装载机制 skill→片段） |
| L9 | 建项目群（项目注册 + invite 两样 + joined_members 验证） | binding 层（TeamHarness projectflow/roomflow）+ `protocol-governance.md`（项目生命周期） | 📋 binding 特定（正链细节归绑定层 README） |
| L10 | 派发三查（@mention 三要素 + 不离开群） | `protocol-task-lifecycle.md`（派发三要素） | ✅ 吸收 |
| L11 | 改派三步回查（event ID 幂等签名） | `protocol-task-lifecycle.md` 派发纪律 + binding 已知问题（平台 txn 去重签名） | ⚠️ 部分（通用纪律吸收；平台 bug 签名归 binding 层） |
| L12 | spec 必须全文（禁止指代式摘要进 spec 参数） | `protocol-task-lifecycle.md`（spec = 全文契约；context_refs 升级：引用的是文件不是指代句） | ✅ 吸收（升级） |
| L13 | 一条消息一个动作 | `protocol-task-lifecycle.md` 派发纪律 | ✅ 吸收 |
| L14 | T+X 硬线 = 一次性 cron（不依赖心跳自唤醒；cron text 自包含） | `protocol-task-lifecycle.md` 定时点纪律 + binding（cron CLI 形态）+ `scripts/timer-derive.sh`（派生 T+X） | ✅ 吸收（升级：派生脚本化） |
| L15 | 交付纪律（>2KB 分块写 + 交付必须 @ 请求人 + 验证证据） | `protocol-task-lifecycle.md` 交付契约 | ✅ 吸收 |
| L16 | DAG 登记（plan_dag 任务可视化） | binding 层（工作台插件正源） | 📋 binding 特定 |
| L17 | 验收与汇总（先汇报再确认） | 同 L7 | ✅ 吸收 |
| L18 | 应对审核（NMA 结构化审查） | `fragments/protocol-nma.md` | ✅ 吸收 |
| L19 | spawn 规则（v2.40 隔离） | 同 W3 | ✅ 吸收 |
| L20 | @ 格式铁律（完整 MXID 四种 mention 格式） | binding 层（Matrix mention 格式规范，bindings/agentteams/README） | 📋 binding 特定 |

## 4. Critic 特有条款映射

| # | 生产条款（旧） | 新协议落点（v1.0） | 状态 |
|:--:|------|------|:--:|
| C1 | 独立性（不受 lead 干预；审的人 ≠ 派活验收的人） | `protocol-governance.md`（利益分离）+ `skeleton/critic.md` | ✅ 吸收 |
| C2 | 五维度审查（目标/受众/质量/数据/合规） | 角色卡（实例 profile）+ `protocol-nma.md`（Checklist 模式） | 📋 实例特定（维度清单）+ ✅ 机制吸收 |
| C3 | 驳回 ≤3 次 → 人类介入；僵持 ≥2 轮 → 仲裁 | `protocol-nma.md`（驳回预算 + 升级链）+ `protocol-governance.md` | ✅ 吸收 |
| C4 | 不代改（只出意见） | `skeleton/critic.md` 铁律 | ✅ 吸收 |

## 5. 占位化映射（fixture 与生产的对照）

| fixture 占位 | 生产原值类别 | 说明 |
|------|------|------|
| `bizmarket-*` / `bizmarket` | 团队名 + 角色 ID 前缀 | 实例参数 |
| `@human-owner` | 人类责任人 MXID localpart | roster 条目 |
| `matrix.example.org` | 私有 Matrix 服务端点 | 拓扑 |
| `<gpu-node>` / `<port>` | GPU 节点名 + 文生图服务端口 | 拓扑 |
| `shared/users/human-owner/` | MinIO 人类用户路径段 | 实例参数 |
| `owner` | 人类责任人称呼 | 实例参数 |
| `platform-incident C1..C7/P3..P15` | 内部事故案卷编号 | 事故签名（内容保留，编号去内部化） |
| `历史事故` | 内部事故日期 | 时间脱敏 |

保留（公开产品名，非实例机密）：QwenPaw / spawn_subagent / Matrix / MinIO / mc / TeamHarness / agentteams-controller:6167（公开产品标准服务名+端口）/ SATCOM（协议前身名，出处标注）/ SDXL-turbo（公开模型）/ QwenPaw 2.2 3600s（公开产品版本行为）。

## 6. 重验规程

协议层（core/protocol 13 篇 / invariants / fragments）任何变更 → 重跑本映射：逐条确认 ✅ 吸收条款的落点仍存在、⚠️/📋 条款的边界未漂移。映射新增条款必须同步更新本文件。本文件缺失或条款无落点 = 生产溯源门红。
