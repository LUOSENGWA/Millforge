# 如何新增一个运行时绑定

> 绑定 = 千锻核心与某个运行时之间的映射层。核心只认 **CAP-*** 能力编号；绑定负责说明"这个运行时用什么机制满足它"。

## 1. 先选形态（三选一）

| 形态 | 目录 | 适用 | 产品示例 |
|---|---|---|---|
| **orchestrated** | `bindings/agentteams/` | 有控制面 + worker 池的编排平台 | AgentTeams（worker 运行时任意） |
| **single-agent** | `bindings/single-agent/` | 无编排层的单 agent 运行时 | QwenPaw / OpenClaw / Hermes |
| **coding-cli** | `bindings/coding-cli/` | 一键执行的编程 CLI | Claude Code / QwenCode / OpenCode / Codex CLI |

> 形态是"架构形状"；同一形态下的**产品差异写进产品矩阵行**，不要为每个产品新开目录。

## 2. 写三个文件（每文件中英成对）

| 文件 | 内容 |
|---|---|
| `mapping-table.md` | 8 个 CAP 能力逐项映射（载体 + 满足情况 + 风险）；产品矩阵（每个产品一行）；不可满足项写清硬门与后果 |
| `skill-fragments.md` | spawn / 脚本 / 审核链在该运行时的落地方式；能引用 `core/scripts/` 的确定性脚本就直接引用 |
| `deployment-guide.md` | 部署形态、配置路径、失败序列与恢复（按实际可得信息写，信息不足写 `TBD`，**不要编造**） |

## 3. 合规声明（必须）

- 8 能力是否全部满足？**不满足的硬门必须显式声明**（例：coding-cli 的 CAP-SPAWN X1 不满足）。
- 声明口径：`compliant` = 8/8 且硬门全过；否则写 `reference`（可参考，非合规）。
- 在 `mapping-table.md` 头部写一句总判定（如 "7.5/8，reference，X4 尽力非强制"）。

## 4. 验收

```bash
make test                                   # golden 13 + 83 必须全绿
# 双语完整性：新增 md 必须有 .en 孪生
# 敏感信息：不得含凭据 / 私有地址 / 个人标记
```

## 5. 边界（铁律）

- 核心层（`core/` 与 `templates/`）**不得**出现该运行时的专名；专名只出现在 `bindings/` 下。
- 绑定文档**不改协议语义**：核心说"必须发生什么"，绑定说"这里怎么发生"；两者冲突时以核心为准并记录差异。
- 新产品的加入 = 在既有形态目录里加一行矩阵 + 补差异说明；**不新建形态目录**。
