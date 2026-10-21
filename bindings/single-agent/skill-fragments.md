# skill 片段（CAP-SPAWN / CAP-EXEC 绑定实现）

> 本文件是 `bindings/single-agent/` 的 skill 面规格；映射见 `mapping-table.md`。
> 通用词纪律：本目录是运行时专名的唯一合法出现面（`core/protocol/00-OVERVIEW.md` §S）。

## 1. 在树脚本清单（core/scripts/，9 件）

脚本随核心分发（不要求运行时重写）；退出码语义见各脚本头注释（CAP-EXEC Y2）。

| 脚本 | 机制 | 绑定触发面（本绑定） |
|------|------|-----------|
| `aggregate-vote.sh` | R2 加权多数计票 | leader 侧 agent skill；attention 超时或收到足够票数时触发 |
| `validate-decision-log.sh` | B-1 第 1 层 schema 校验 | 父 agent skill **验收前**执行（spawn 返回时不执行——spawn 是 LLM，不能自我校验） |
| `detect-conflict.py` | B-2 冲突检测 Step 1–3（无 LLM，纯字段比对） | 父 agent skill，B-1 第 1 层通过后调用；候选冲突对写 `decisions/<task_id>/conflict-candidates.json`（本地路径） |
| `contract-revalidate.sh` | B-3 重验（semver + 指纹 + 兼容性报告） | 父 agent skill 验收前调用；或 critic 第 3 层发现指纹不匹配时回退调用 |
| `attention-stall.sh` | B-5 attention stall 检测 | `qwenpaw cron` 扫描面（规格见 `../agentteams/cron-spec.md`）；计数写 task meta `attention_stall_count`（本地 JSON） |
| `verification-mismatch-window.sh` | B-6 verification_mismatch 计数 + 24h 窗口 | `qwenpaw cron` 扫描面；24h 超时维持原 spec |
| `saga-compensate.py` | B-10 saga 补偿指令生成 | 读 dependency graph + 正向操作日志 → 反向补偿序列；由协议层/leader 触发 |
| `consistency-check.py` | C-3 规则层一致性（字段级/枚举级二元比对） | R6 回答写回前调用；规则层无法判定时才升级受限分类 spawn |
| `timer-derive.sh` | CAP-TIMER 幂等派生 | `qwenpaw cron` 回调 payload；见 `../agentteams/cron-spec.md` |

**8 核心脚本 I/O 纪律**：只处理本地文件 / stdin / stdout，**不得调用任何对象存储 CLI**——本绑定无对象存储，I/O = 本地文件系统 / 共享卷（合法 CAP-STORE 实现）。

## 2. spawn 片段（CAP-SPAWN，生产已验证）

- **worker native session = 只调度 + 审查，不执行任何实现工作。** 所有实现工作进 `spawn_subagent(fork=False)`（fresh session，不继承父会话——**fork=True 违反 X1**）。
- 该机制在本绑定运行时**生产已验证**（X1 ✅）。
- 结构化返回（X2）；状态经返回值传递（X3），父 session 不读子 session 上下文。
- X4（时限强制）= 上游缺口（同 agentteams 绑定，上游缺口）；合入前绑定层用 timeout 参数尽力（非强制），挂起无返回按 `bounded_failure` 语义处理，3 次升级。

## 3. 审核链片段（B-1 三层校验，顺序不可换）

```
spawn 返回
  → 第 1 层: validate-decision-log.sh（schema 字段校验，父 agent 验收前）
  → 第 2 层: detect-conflict.py（纯字段比对，输出候选冲突对）
  → 第 3 层: critic 验收脚本检查指纹（权威 = 本地 `decisions/<task_id>/<spawn_id>.decision.json`；
             task meta 只存 {ref, sha256_8, validated} 索引）
```

- 校验不放 LLM：第 1/2 层是确定性脚本；唯一 LLM 参与 = C-3 规则层判不出时的**受限分类 spawn**（只输出 `{contradict, criterion_id, reason}`，不是自由生成）。
- 校验不放 spawn 返回时刻：spawn 是 LLM，自我校验无效——校验由**父 agent 验收前**执行。

## 4. 心跳/cron 片段

一行指针：兜底唤醒语义、注册/清理、U1–U4、红线 = 与 agentteams 绑定相同（见 `../agentteams/cron-spec.md`）。skill 面只负责提供 cron 回调 payload（`timer-derive.sh` / `attention-stall.sh` / `verification-mismatch-window.sh`）。
