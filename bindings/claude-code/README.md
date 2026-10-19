# Claude Code（coding-CLI）参考绑定（reference）

> 千锻核心与 **coding-CLI（one-shot coding agent）** 运行时的映射。
> 最薄的绑定：无团队/room/loop driver，只承载 **task + spawn + 验收证据链** 三件套。
> 适用场景：单任务级编码工作（spec → 有界执行 → 结构化返回 → 指纹验收），作为更大编排的**执行后端**，不承载 NMH/NMA 全流程。

## CAP 映射（只实现 4/8 能力 = 合法部分绑定）

| 能力 | 机制 | 备注 |
|------|------|------|
| **CAP-SPAWN** | one-shot 执行（10 flags）+ `--max-wall-time` | **X4 有界性 = 参考实现**：运行时强制时限，超时 `exit 55`（bounded_failure 语义的直接实现）——这是 8 能力中**唯一由运行时原生强制**的 X4（AgentTeams 绑定侧 X4 仍是尽力） |
| **CAP-EXEC** | CLI 进程执行（退出码语义：0=成功，55=超时，其他=失败） | Y1/Y2/Y3 ✅；core/scripts/ 9 脚本可直接作为该 CLI 的调用方 |
| **CAP-STORE** | coding-runs API（`GET /api/v1/coding-runs`）+ 本地工作区文件 | **SIG-ARTIFACT/验证指纹 ↔ coding-runs 证据链**：run 的产物清单 + 校验和 = artifact ref 的指纹源；read-after-write 本地强一致 |
| **CAP-ATTN** | `--approval-mode` 阶梯 + ACP `request_permission` | 两层互补（10/8 定案）：平台 approval_level（人终审档位）× coder 侧 request_permission（逐操作授权）；**千锻闭环 = auto 档 + request_permission**（10/13 深挖结论） |
| CAP-STATE | ❌ 无任务级持久状态（one-shot 无跨 run 状态） | 绑定声明：状态由**调用方（父执行体）持有**——CLI 只做单步，状态机在上层 |
| CAP-TIMER | ❌ 无（时限 = 单 run 的 --max-wall-time，非调度） | 调度由父执行体/上层 runtime 负责 |
| CAP-NOTIFY | ❌ 无 | 同上 |
| CAP-ROSTER | ❌ 无 | 单执行体无权重问题 |

**合法性判定**：4/8 能力 = **部分绑定（partial binding）**——作为执行后端合法（X4 参考实现 + 证据链 + 人终审阶梯齐全），不得独立承载需要 CAP-STATE/TIMER/NOTIFY/ROSTER 的协议面（loop driver、attention 路由、计票、熔断）。父执行体补全缺失 4 能力时，组合整体 = 合法绑定。

## 三处协议咬合（绑定层事实）

| # | 协议面 | 机制咬合 |
|---|--------|---------|
| 1 | **X4 有界性** | one-shot timeout + `--max-wall-time` → `exit 55` = bounded_failure（运行时强制执行，X4 语义的参考实现） |
| 2 | **SIG-ARTIFACT / 验证指纹** | `GET /api/v1/coding-runs` 产物清单 + 校验和 = artifact 证据链（验收时指纹比对源） |
| 3 | **attention / 人终审** | `--approval-mode` 阶梯 + ACP request_permission（两层互补：平台档位 × 逐操作授权） |

## 审批档位纪律（critical_delivery 硬约束）

- **simple 档**：默认 `--yolo`（执行层审批旁路）可接受
- **critical_delivery（R1 类）**：**禁止 yolo**——必须 `auto 档 + request_permission` 或人锁（10/13 风险注：`--yolo` 默认 = 执行层审批旁路，关键交付不可旁路）
- 人终审记录 = SIG-DECISION 事件源（父执行体写 CAP-STATE）

## 部署/调用

```
父执行体（AgentTeams worker / bare-qwenpaw agent）
  → 构造 task spec（core/schemas/spec.schema.json）
  → 调 coding-CLI（one-shot，flags 含 --max-wall-time + --approval-mode）
  → exit 0: 读 coding-runs 证据链 → 指纹验证（CAP-STORE T2）→ 验收
  → exit 55: bounded_failure（记 decision_log，≤3 次升级）
  → 其他: 失败（同上）
```

本绑定无 SOUL.md 部署（CLI 无身份文件概念）；协议约束通过 **task spec + 调用参数 + 父执行体身份文件** 三处承载。
