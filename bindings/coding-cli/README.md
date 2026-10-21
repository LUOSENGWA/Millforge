# 编程 CLI 参考绑定（coding-cli binding，reference）

> 千锻核心与**编程 CLI**（one-shot coding agent）的映射。**本绑定对所有编程 CLI 通用**：产品矩阵 = Claude Code / QwenCode / OpenCode / Codex CLI / …（Claude Code 为参考产品）；X1 逐产品判定。
> 最薄的绑定：无团队/room/loop driver，只承载 **task + spawn + 验收证据链** 三件套。
> 适用场景：单任务级编码工作（spec → 有界执行 → 结构化返回 → 指纹验收），作为更大编排的**执行后端**，不承载 NMH/NMA 全流程。

## 索引（正文文档）

| 文档 | 内容 |
|------|------|
| `mapping-table.md` | CAP→机制映射（组合视角，8 能力逐项不变式）+ X1 非合规声明 + 合法性判定 7/8（**单一事实源**；本 README「CAP 映射」为其一致摘要） |
| `skill-fragments.md` | CAP-SPAWN/CAP-EXEC skill 面（spawn 面 X1 声明 + 验收证据链 + 审批档位纪律） |
| `deployment-guide.md` | 拓扑 + 调用链 + 失败序列与恢复 |

## 能力声明（CAP-*）

| CAP | 已实现 | 覆盖等级 | 具体机制（运行时） | 限制 |
|-----|--------|----------|--------------------|------|
| CAP-STATE | ❌ | 声明降级 | 状态由父执行体持有（one-shot 无跨 run 状态） | 不可独立承载需要状态的面 |
| CAP-STORE | ✅ | 完整 | coding-runs API + 本地工作区文件 + 校验和 | 本地强一致 |
| CAP-TIMER | ❌ | 声明降级 | 单 run `--max-wall-time`（非调度） | 调度由父执行体 |
| CAP-NOTIFY | ❌ | 声明降级 | 无 | 通知由父执行体 |
| CAP-ATTN | ✅ | 完整 | `--approval-mode` 阶梯 + ACP `request_permission` | — |
| CAP-SPAWN | ✅ | 完整 | one-shot 执行（10 flags）+ `--max-wall-time` | X1 不满足（无会话隔离）→ reference 而非 compliant |
| CAP-EXEC | ✅ | 完整 | CLI 进程执行（退出码语义） | — |
| CAP-ROSTER | ❌ | 声明降级 | 无 | 单执行体 |

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

**合法性判定**：4/8 能力 = **部分绑定（partial binding）**——作为执行后端合法（X4 参考实现 + 证据链 + 人终审阶梯齐全），不得独立承载需要 CAP-STATE/TIMER/NOTIFY/ROSTER 的协议面（loop driver、attention 路由、计票、熔断）。组合视角（父执行体补全缺失 4 能力）= **7/8**——CAP-SPAWN 不满足 X1 硬门（无 fork=False 等价的会话隔离原语）→ 标注为 reference 而非 compliant（声明见 `mapping-table.md` §1.1）。

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
父执行体（AgentTeams worker / standalone-agent runtime）
  → 构造 task spec（core/schemas/spec.schema.json）
  → 调 coding-CLI（one-shot，flags 含 --max-wall-time + --approval-mode）
  → exit 0: 读 coding-runs 证据链 → 指纹验证（CAP-STORE T2）→ 验收
  → exit 55: bounded_failure（记 decision_log，≤3 次升级）
  → 其他: 失败（同上）
```

本绑定无 SOUL.md 部署（CLI 无身份文件概念）；协议约束通过 **task spec + 调用参数 + 父执行体身份文件** 三处承载。
