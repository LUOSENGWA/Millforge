# 部署指南（裸 QwenPaw 绑定专属）

> 本文件是 `bindings/single-agent/` 的部署/运维规格；映射见 `mapping-table.md`。

## 1. 拓扑（本绑定专有名词面）

| 原语 | 部署形态 |
|------|---------|
| agent（leader/worker） | 单 Docker 宿主，多 QwenPaw agent 实例（无 K8s / Controller / Team CRD） |
| state | 每 agent 本地 JSON 状态文件（宿主盘；**无异地副本**——绑定声明） |
| store | 本地文件系统 / 共享卷（`storage_adapter: local`） |
| timer | QwenPaw cron（per agent，`qwenpaw cron create --agent-id ...`） |
| notify / attn | QwenPaw 通道（控制台 / IM，按已配通道） |
| 平台层 | 无（无 MinIO、无 Matrix、无对象存储项目空间） |

## 2. 编译 → 部署链

```
millforge compile <team.json> --out /tmp/build/<team>
  → <role>.soul.md × N          # 身份文件
  → fragments/protocol-*.md     # 协议层
  → fragments/industry-*.md
  → spawn-specs/*.md            # spawn 注入
  → core/scripts/ 9 脚本（随核心分发）
部署（每 agent）:
  1. <role>.soul.md → 该 agent workspace 根 SOUL.md
     + fragments/ spawn-specs/ → workspace protocols/
  2. roster JSON + core/scripts/ → 共享位置（各 agent 可执行路径）
  3. cron: 每活跃 task 按 timer-derive 注册（qwenpaw cron）
  4. 验证: 读回文件 + 行数核对（wc -l）
```

**硬约束**：
- **状态无异地副本**（S4 ⚠️ 绑定声明）：宿主盘是单点；宿主备份策略由**部署方自担**（本绑定不提供平台层备份）。
- **pip 一律 venv 版**（同 agentteams 绑定铁律）——系统 pip 装到错误路径，版本误判是生产事故源。
- 无 docker restart 回滚问题（无平台层恢复机制）；SOUL.md 更新下一个会话生效。
- 共享卷并发写：单写者目录约定（T3 安全前提）。

## 3. 同步层

not applicable——无对象存储异步同步层；本地写 = 同步完成，T2 执行细则退化（无 uploaded 回执要求）。

## 4. 失败序列与恢复

| 失败 | 检测 | 恢复 |
|------|------|------|
| 宿主盘故障（状态全丢） | 宿主监控 / 状态读失败 | 绑定层无法恢复（无异地副本）；依赖宿主备份策略（部署方自担） |
| 状态文件并发写冲突 | CAS CONFLICT | 文件锁 CAS 重试；JSONL append 幂等可重放（S3） |
| cron 定时器丢失（agent 重启） | task 有 due_at 无 cron | `timer-derive.sh` 幂等重派生（U3：判定从状态重算） |
| spawn 挂起无返回 | X4 时限（尽力） | bounded_failure 语义；3 次 → 升级 |
| allowlist 静默拦截 | 消息无错误日志消失 | 对比通道 access 配置（机制同 agentteams 绑定，见 `../agentteams/deployment-guide.md` §4） |
| SOUL.md 更新未生效 | 行为漂移 | 核对 workspace SOUL.md 内容；下一个会话生效（无需 restart） |
