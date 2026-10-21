# 机制 × 运行时映射表（Claude Code / coding-CLI）

> 本文件是 `bindings/coding-cli/` 映射的**单一事实源**（`README.md`「CAP 映射」为其一致摘要）。
> 定位：本绑定是**执行后端**（one-shot coding CLI），缺失的 4 能力（CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER）由**父执行体**提供；§1 表为**组合视角**（本运行时 + 父执行体）。
> 通用词纪律：本目录是运行时专名的唯一合法出现面（`core/protocol/00-OVERVIEW.md` §S）。

## 1. CAP → 机制映射（8 能力基线，组合视角）

| 能力 | 机制 | 不变式满足情况 | 风险/备注 |
|------|------|--------------|-----------|
| **CAP-STATE** | 父执行体提供（本运行时 stateless：one-shot，无跨 run 状态） | S1–S4 委托父执行体（组合 ✅ / 独立 ❌） | 状态机在上层；CLI 只做单步 |
| **CAP-STORE** | coding-runs API（`GET /api/v1/coding-runs`）+ 本地工作区文件 | T1 ✅（产物清单 + 校验和 = 指纹源）T2 ✅（本地 read-after-write 强一致）T3 ✅（链式 / 本地 JSONL，由父 adapter 提供） | SIG-ARTIFACT / 验证指纹 ↔ coding-runs 证据链（验收时指纹比对源） |
| **CAP-TIMER** | 父执行体提供（时限 = 单 run 的 `--max-wall-time`，非调度） | U1–U4 委托父执行体（组合 ✅ / 独立 ❌） | 调度由父执行体 / 上层 runtime 负责 |
| **CAP-NOTIFY** | 父执行体提供 | V1–V6 委托父执行体（组合 ✅ / 独立 ❌） | 无通知面 |
| **CAP-ATTN** | `--approval-mode` 阶梯 + ACP `request_permission` | W2 ✅（人终审记录写父 CAP-STATE）W3 ⚠️（超时判定委托父 CAP-TIMER）W4 ✅（request_permission = 逐操作身份授权）W5 ⚠️（审批提示 = 同步交互面，非可回访持久展示面；持久展示面由父承担）W6 ⚠️（单面）W7 ✅（结构化档位 + 逐操作结构化授权） | 两层互补（10/8 定案）：平台 approval_level（人终审档位）× coder 侧 request_permission（逐操作授权）；千锻闭环 = auto 档 + request_permission（10/13 深挖结论） |
| **CAP-SPAWN** | one-shot 执行（10 flags）+ `--max-wall-time` | **X1 ❌（硬门）** X2 ✅（结构化返回）X3 ✅（独立进程）X4 ✅（**运行时强制**时限，超时 `exit 55`） | X1 非合规声明见 §1.1；X4 = 本绑定参考实现 |
| **CAP-EXEC** | CLI 进程执行（退出码语义：0=成功，55=超时，其他=失败） | Y1 ✅ Y2 ✅ Y3 ✅ | core/scripts/ 9 脚本照常运行（CAP-EXEC 裁决 item 3：本地文件系统是合法 CAP-STORE 实现） |
| **CAP-ROSTER** | 父执行体提供 | Z1–Z3 委托父执行体（组合 ✅ / 独立 ❌） | 单执行体无权重问题 |

### 1.1 CAP-SPAWN X1 非合规声明（硬门）

**本绑定的 CAP-SPAWN 不满足 X1（上下文隔离，硬门）**，理由：

1. 运行时缺少 fork=False 等价的会话隔离原语：其上下文模型 ① 自动向所有会话注入工作区级记忆文件（CLAUDE.md）；② 支持会话持久化与恢复（会话历史，`--resume`）——两者均构成不经 context_refs 的上下文继承路径。
2. one-shot 进程边界不是运行时强制的隔离保证：其隔离依赖调用方始终 one-shot + 干净工作区（调用方纪律），不是运行时强制。
3. 契约要求 X1 由运行时强制（`core/binding-contract.md`：「不满足 X1 的运行时不得作为合法绑定」）。调用方纪律 ≠ 运行时保证 → 硬门不满足。

边界注记：one-shot 调用路径本身 X1 合规（进程级 fresh context），可在父执行体的调用方纪律下作为执行后端使用；但绑定合法性判定按**能力级（运行时强制）**口径 → CAP-SPAWN 不合规。

**合法性判定**：独立视角 = 4/8 能力（部分绑定，作为执行后端合法，见 README）；组合视角（父执行体提供 CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER）= **7/8**——8 能力中 7 项满足，CAP-SPAWN 不满足 X1 硬门（见 §1.1）。**标注为 reference 而非 compliant**（`core/binding-contract.md` §绑定合法性判定 条件 1：X1/X4 硬门）。注：X4 反而是本绑定强项——三个参考绑定中唯一由运行时原生强制的 X4（agentteams 绑定侧仍是尽力）。

## 2. 机制 → 执行载体（协议咬合面，4 项）

| 协议面 | 执行载体 | 状态存哪 | 触发者 |
|---|---|---|---|
| X4 有界性 | one-shot `--max-wall-time`（运行时强制，超时 `exit 55`） | 不适用（无状态；退出码 = 判定） | 运行时超时 |
| SIG-ARTIFACT / 验证指纹 | coding-runs API 产物清单 + 校验和 | 本地工作区文件；ref 记入父 CAP-STATE | 验收流程（父执行体） |
| 人终审 | `--approval-mode` 阶梯 + ACP `request_permission` | 父 CAP-STATE（人终审记录 = SIG-DECISION 事件源） | 逐操作授权 / 终审 |
| 确定性脚本 | core/scripts/ 9 脚本（父执行体调用） | 本地文件（CAP-STORE = 本地文件系统） | 父执行体 skill |

[NO-CARRIER] 缺口 = 4 项父提供能力（CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER）——本绑定不为其提供载体；依赖这 4 能力的协议面（loop driver、attention 路由、计票、熔断）必须由父执行体承载。

## 3. 原语映射

| 原语 | 机制 |
|------|------|
| human | 父执行体通道 + 人终审（审批提示） |
| agent | 父执行体（本运行时是执行后端，不是协议 agent） |
| leader | 不适用（父执行体提供） |
| worker | 本 CLI one-shot 执行（仅执行面） |
| arbitrator | 不适用 |
| room | 不适用 |
| project | 不适用 |
| task | 父执行体 CAP-STATE |
| artifact | coding-runs 产物清单 + 本地工作区文件 |
| decision node | 父执行体 decision_log |
| channel | 不适用（无通知面；父执行体面） |
| mode | 不适用（单执行体） |
| attention | `--approval-mode` 阶梯 + ACP `request_permission`（人终审） |
| loop | 不适用（无 CAP-TIMER） |
| signal | 退出码（0 / 55 / 其他）+ coding-runs 证据链 |
