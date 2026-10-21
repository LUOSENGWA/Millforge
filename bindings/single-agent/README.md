# 单 agent 运行时参考绑定（single-agent binding，reference）

> 千锻核心与**单 agent 运行时**（无编排层）的映射。**本绑定对所有单 agent 运行时通用**：产品矩阵 = QwenPaw / OpenClaw / Hermes / …（QwenPaw 为参考产品）。
> 适用场景：单 Docker 宿主、多 QwenPaw agent 实例（无 K8s/Controller/Team CRD）、无 MinIO（本地盘/共享卷做对象存储）。
> 与 `bindings/agentteams` 的差异 = 去掉平台编排层，**全部能力由 QwenPaw 原生机制 + 本地文件承载**。

## 索引（正文文档）

| 文档 | 内容 |
|------|------|
| `mapping-table.md` | CAP→机制映射（8 能力逐项不变式）+ 存储层替代 + 原语映射（**单一事实源**；本 README「CAP 映射」为其一致摘要） |
| `skill-fragments.md` | CAP-SPAWN/CAP-EXEC skill 面（在树 9 脚本 + spawn 片段（生产已验证）+ 三层审核链） |
| `deployment-guide.md` | 拓扑 + 编译→部署链 + 失败序列与恢复 |

## 能力声明（CAP-*）

| CAP | 已实现 | 覆盖等级 | 具体机制（运行时） | 限制 |
|-----|--------|----------|--------------------|------|
| CAP-STATE | ✅ | 完整 | 每 agent 本地 JSON + 文件锁 CAS | 无异地副本（宿主盘单点） |
| CAP-STORE | ✅ | 完整 | 本地文件系统 / 共享卷 + 客户端 sha256 | 无跨节点强一致 |
| CAP-TIMER | ✅ | 完整 | QwenPaw cron | 粒度 = cron 周期 |
| CAP-NOTIFY | ⚠️ | 部分 | `channels send`（控制台/QQ/钉钉…） | V3 静默丢弃风险 / V5 无代码级事件面 |
| CAP-ATTN | ✅ | 完整 | 控制台会话 + IM 私聊持久展示面 | 群聊 @mention 不得 resolve（S4） |
| CAP-SPAWN | ✅ | 完整 | `spawn_subagent(fork=False)` | X4 时限尽力 |
| CAP-EXEC | ✅ | 完整 | agent 容器/宿主 shell | venv pip 约束 |
| CAP-ROSTER | ✅ | 完整 | roster JSON 文件 | 多 human 无协议层隔离 |

## CAP 映射

| 能力 | 机制 | 备注 |
|------|------|------|
| CAP-STATE | 每 agent 本地 JSON 状态文件（`.qwenpaw/` 或工作区）+ 文件锁 CAS | 单宿主无跨节点问题；S4 风险 = 宿主盘故障（绑定声明：状态无异地副本） |
| CAP-STORE | 本地文件系统 / 共享卷（`storage_adapter: local`） | T1 客户端 sha256；T2 本地写 = 同步完成（无异步同步层竞态）；T3 同对象 JSONL append（本地 POSIX 安全）或链式 |
| CAP-TIMER | QwenPaw cron（`qwenpaw cron create --agent-id ...`） | 同 agentteams 绑定 §3.2 cron 规格 |
| CAP-NOTIFY | `qwenpaw channels send`（控制台/QQ/钉钉/… 按已配通道） | V3 静默丢弃风险同 agentteams 绑定（allowlist 机制相同）；V5 无代码级事件面 |
| CAP-ATTN | QwenPaw 通道私聊/控制台会话（持久展示面 = 控制台会话 + IM 私聊） | 群聊 @mention 不得 resolve（S4） |
| CAP-SPAWN | `spawn_subagent(fork=False)` | 同 agentteams 绑定（X4 时限尽力）；spawn 机制**生产已验证** |
| CAP-EXEC | agent 容器/宿主 shell | venv pip 铁律同（QwenPaw 环境） |
| CAP-ROSTER | roster JSON 文件（agent 配置 + 人类成员） | 单宿主通常单 human（single_user）或多 human 各管各 agent（multi_user 退化：无跨团队） |

**模式**：默认 `single_user`（无 arbitrator 角色时跨团队扩展不可用——coordinator 可由任一 leader 承担或人兼任，协议按 §02-MODES 相变处理：无集群级协调角色 = 跨团队 handoff 机制不存在）。

## 与 agentteams 绑定的能力差距

| 面 | agentteams | single-agent |
|----|-----------|--------------|
| 跨团队 handoff | ✅（MinIO 项目空间 + Manager） | ❌（无对象存储项目空间；共享卷可模拟，权限靠目录约定） |
| 多 user 隔离 | Controller + Matrix 权限 | 无（同宿主同权限 = 协议层不保证隔离，部署层自担） |
| 团队/roster 管理 | Team CRD | 手工 roster 文件 |
| 状态异地副本 | MinIO | 无（宿主盘单点） |

**适用判定**：个人实验 / 单团队生产 / 快速验证协议行为 → single-agent 绑定足够（L1-L3 协议层完整可用）；多团队 + 跨团队 handoff + 多 human 隔离 → 上 agentteams。

## 部署

```
1. 编译: millforge compile <team.json> --out /tmp/build/<team>
2. 每个 agent: <role>.soul.md → 该 agent workspace 根 SOUL.md
   + fragments/ spawn-specs/ → workspace protocols/
3. roster 文件 + core/scripts/ → 共享位置（各 agent 可执行路径）
4. cron: 每活跃 task 按 timer-derive 注册
```

无 docker restart 回滚问题（无平台层恢复机制）；SOUL.md 更新即生效（下轮会话）。
