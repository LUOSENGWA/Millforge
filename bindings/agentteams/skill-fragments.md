# skill 片段（CAP-SPAWN / CAP-EXEC 绑定实现）

> Provenance：运行时绑定审查（第四轮，2026-10-18）定案 + v2.40 上下文隔离定案 + 在树 `core/scripts/` 实测（9 件）。本文件是 `bindings/agentteams/` 的 skill 面规格。通用词纪律见 `README.md` 头注。
> 甄别注记：底稿（第四轮）中 B-5/B-6 标注 [NO-CARRIER]、规划 `nmh-watchdog.sh` 新模式；在树实测两者已是独立脚本（`attention-stall.sh` / `verification-mismatch-window.sh`）。本文件以在树为准，底稿规划仅存 `mapping-table.md` §2.1。

## 1. 在树脚本清单（core/scripts/，9 件）

脚本随核心分发（不要求运行时重写）；退出码语义见各脚本头注释（CAP-EXEC Y2）。

| 脚本 | 机制 | 绑定触发面 |
|------|------|-----------|
| `aggregate-vote.sh` | R2 加权多数计票 | Leader 侧 skill；attention 超时或收到足够票数时触发 |
| `validate-decision-log.sh` | B-1 第 1 层 schema 校验 | 父 Worker skill **验收前**执行（spawn 返回时不执行——spawn 是 LLM，不能自我校验） |
| `detect-conflict.py` | B-2 冲突检测 Step 1–3（无 LLM，纯字段比对） | 父 Worker skill，B-1 第 1 层通过后调用；候选冲突对写 MinIO `decisions/<task_id>/conflict-candidates.json` |
| `contract-revalidate.sh` | B-3 重验（semver + 指纹 + 兼容性报告） | 父 Worker 验收前调用；或 critic 第 3 层发现指纹不匹配时回退调用 |
| `attention-stall.sh` | B-5 attention stall 检测 | cron 扫描面（见 `cron-spec.md`）；计数写 task meta `attention_stall_count` |
| `verification-mismatch-window.sh` | B-6 verification_mismatch 计数 + 24h 窗口 | cron 扫描面；24h 超时维持原 spec |
| `saga-compensate.py` | B-10 saga 补偿指令生成 | 读 dependency graph + 正向操作日志 → 反向补偿序列；由协议层/Leader 触发 |
| `consistency-check.py` | C-3 规则层一致性（字段级/枚举级二元比对） | R6 回答写回前调用；规则层无法判定时才升级受限分类 spawn |
| `timer-derive.sh` | CAP-TIMER 幂等派生 | `qwenpaw cron` 回调 payload；见 `cron-spec.md` |

**8 核心脚本 I/O 纪律**：只处理本地文件 / stdin / stdout，**不得调用任何对象存储 CLI**（`mc` 等）；对象存储 I/O 全由 CAP-STORE adapter 负责（`rustfs-migration.md` §4 审计表）。

## 2. spawn 片段（CAP-SPAWN，v2.40 上下文隔离定案）

- **worker native session = 调度 + 审查，不执行任何实现工作。** 所有实现工作进 `spawn_subagent(fork=False)`（fresh session，不继承父会话——**fork=True 违反 X1**）。
- 结构化返回（X2）；状态经返回值传递（X3），父 session 不读子 session 上下文。
- X4（时限强制）= 上游缺口（PR 线）；合入前绑定层用 timeout 参数尽力（非强制），挂起无返回按 `bounded_failure` 语义处理，3 次升级。
- 三层缓存协同（绑定层事实）：MinIO artifacts（spawn 读上下文）→ 运行时 offload（执行中落盘）→ 模型服务端 KV Cache（硬件兜底）。

## 3. 审核链片段（B-1 三层校验，顺序不可换）

```
spawn 返回
  → 第 1 层: validate-decision-log.sh（schema 字段校验，父 Worker 验收前）
  → 第 2 层: detect-conflict.py（纯字段比对，输出候选冲突对）
  → 第 3 层: critic 验收脚本检查指纹（权威 = MinIO decisions/<task_id>/<spawn_id>.decision.json；
             task meta 只存 {ref, sha256_8, validated} 索引）
```

- 校验不放 LLM：第 1/2 层是确定性脚本；唯一 LLM 参与 = C-3 规则层判不出时的**受限分类 spawn**（只输出 `{contradict, criterion_id, reason}`，不是自由生成）。
- 校验不放 spawn 返回时刻：spawn 是 LLM，自我校验无效——校验由**父 Worker 验收前**执行。

## 4. 心跳/cron 片段

一行指针：兜底唤醒语义、注册/清理、U1–U4、红线 = 见 `cron-spec.md`。skill 面只负责提供 cron 回调 payload（`timer-derive.sh` / `attention-stall.sh` / `verification-mismatch-window.sh`）。

## 5. 规划载体（未实现，勿引用为现行）

`nmh-watchdog.sh`（R5 reopen-window 模式）/ `emit-class-mismatch.sh` / `write-contract-snapshot.sh` / `write-aggregation-result.sh` / `write-decision-record.sh`——见 `mapping-table.md` §2.1。实现前对应机制按"协议层触发 + 人工兜底"运行。
