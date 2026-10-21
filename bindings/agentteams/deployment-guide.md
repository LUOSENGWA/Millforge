# 部署指南（AgentTeams + QwenPaw 绑定专属）

> 本文件是 `bindings/agentteams/` 的部署/运维规格。通用词纪律见 `README.md` 头注。

## 1. 拓扑（本绑定专有名词面）

| 原语 | 部署形态 |
|------|---------|
| worker / leader | QwenPaw Worker 容器（`python3 -m copaw_worker.run_copaw_app app`，qwenpaw runtime）；leader = 编译产物部署到 `.qwenpaw/workspaces/default/` |
| arbitrator | Manager 容器（`agentteams-manager`，qwenpaw runtime，仅 single_user） |
| state | 容器本地 `.qwenpaw/workspaces/default/` 状态文件 + **MinIO/RustFS 备份（必须）** |
| notify | QQ 原始通道 / Matrix Room（team / project / DM） |

## 2. 编译 → 部署链

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

**硬约束**：
- **状态必须同步对象存储备份**——容器重建丢状态（S4 ⚠️）；`mc` 推送确认前不算持久（T2）。
- **pip 一律 venv 版**（`/opt/venv/copaw/bin/pip`）——系统 pip 装到错误路径，版本误判是生产事故源（运行时约束）。
- 身份文件**双位置**部署；restart 前部署会被 runtime 恢复覆盖。

## 3. filesync 同步层（CAP-STORE T2 执行细则）

- 容器工作区 ↔ MinIO/RustFS 的同步 = push_loop（异步）+ startup mirror_all。
- **写后协议（竞态防护）**：write → 等 ≥45–60s（验证磁盘 + push uploaded 日志）→ 才允许 restart/消费。实证：写后快速 restart 会被 startup mirror_all 回滚。
- uploaded 回执 = push 日志 `push uploaded .../<file>` 行（绑定层轮询）。

## 4. 失败序列与恢复（T5 生产实证）

| 失败 | 检测 | 恢复 |
|------|------|------|
| Worker 容器异常（Internal error） | docker logs ERROR | restart → 重派（3 次 → 升级）；**pydantic 版本过旧 = workspace 启动失败**（venv pip 查版本，#176） |
| 状态写 MinIO 未确认 | push 日志无 uploaded | 不消费 ref（T2）；重推 + 确认 |
| allowlist 静默拦截 | 消息无错误日志消失 | 对比 agent.json access control（#160/#169）；restart 后验证 allow_from 含 human |
| cron 定时器丢失（容器重建） | task 有 due_at 无 cron | timer-derive 幂等重派生（U3：判定从状态重算） |
| spawn 挂起无返回 | X4 时限（尽力） | bounded_failure 语义；3 次 → 升级 |
| restart 后 SOUL.md 回滚 | 文件 mtime/行数 | 双位置重部署（restart 后） |
