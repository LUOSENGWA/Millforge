# cron 规格（CAP-TIMER 绑定参数）

> Provenance：运行时绑定审查（第四轮，2026-10-18）+ 流程连续性定案（v2.41）；本文件是 `bindings/agentteams/` 的 CAP-TIMER 绑定规格。通用词纪律见 `README.md` 头注。

## 1. 不变式满足（U1–U4）

| 不变式 | 绑定实现 | 状态 |
|---|---|---|
| **U1** due_at 可持久 | due_at 存 CAP-STATE（`.qwenpaw/workspaces/default/` 状态文件），时钟 = 容器时钟 | ✅ |
| **U2** callback 幂等 | `timer-derive.sh` 幂等派生：重复 callback 只重派生不重复动作 | ✅ |
| **U3** 判定可重算 | 到期判定从状态重算（读 due_at + 当前状态），**不存"已处理"标记** | ✅ |
| **U4** 粒度声明 | 粒度 = cron 检查周期，绑定声明值 = **默认 5min**；due_at 精度 ≤5min 的窗口需在绑定声明中显式标注 | ⚠️（声明项） |

## 2. 注册与清理

```
每个活跃 task 注册（timer-derive.sh 派生）:
  qwenpaw cron create --agent-id <worker> \
    --schedule "every 5m" --task "timer-check" \
    （payload = 运行 timer-derive.sh --task-meta <ref> → 到期动作）
粒度声明: 5 分钟（U4）；due_at 精度 ≤5min 的窗口需声明
清理: task 终态（completed/cancelled）→ cron delete（防孤儿定时器）
```

- 派生幂等 = 容器重建/cron 丢失后，`timer-derive.sh` 从 CAP-STATE 重算并补齐定时器（U3 的运维形态）。
- 孤儿定时器 = 清理遗漏的 cron 会持续唤醒无 task 的检查；task 终态钩子里必须 `cron delete`。

## 3. 红线：兜底唤醒，不做实时驱动（v2.41 定案）

- **心跳/cron 只做兜底唤醒，不做实时驱动。** 实时驱动 = 事件触发（消息到达）+ 状态机副作用（`next_action` 推进）。
- 理由：LLM 是消息驱动而非流程驱动；心跳作为用户消息注入会产生同一 turn 内的注意力冲突与 token 浪费，不可靠。
- cron 的定位：① 到期动作（due_at 到达）② 状态丢失后的兜底重派生 ③ 超时窗判定（R5/B-6 类，规划载体见 `mapping-table.md` §2.1）。
- 周期建议：活跃 task 检查 5min；看门狗类（*/2）在规划载体落地前不启用。

## 4. 失败与恢复

| 失败 | 检测 | 恢复 |
|------|------|------|
| cron 定时器丢失（容器重建） | task 有 due_at 无 cron | `timer-derive.sh` 幂等重派生（U3：判定从状态重算） |
| cron 回调风暴（状态未推进） | 同一 task 连续空唤醒 | 检查 next_action/状态是否被外部消息触发推进；必要时人工 restart worker |
| 时钟漂移（容器重建/宿主机改时区） | due_at 与实际到期偏差 | 判定一律"状态重算"（U3），不依赖单调时钟假设；重建后首轮重派生 |
