# 部署指南（Claude Code / coding-CLI 绑定专属）

> 本文件是 `bindings/coding-cli/` 的部署/调用规格；映射见 `mapping-table.md`。
> 定位：本绑定无平台层、无身份文件概念——「部署」= 调用约定 + 证据链验收；缺失的 4 能力全部由父执行体承载。

## 1. 拓扑

| 原语 | 部署形态 |
|------|---------|
| 本运行时 | coding-CLI 进程（one-shot），由父执行体调用 |
| 父执行体 | AgentTeams worker / standalone-agent runtime（提供 CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER） |
| state | 父执行体 CAP-STATE（本运行时 stateless） |
| store | coding-runs API + 本地工作区文件 |
| timer / notify / roster | 不适用（父执行体提供） |
| 身份文件 | 无（协议约束通过 task spec + 调用参数 + 父执行体身份文件三处承载） |

## 2. 调用链（编译 → 调用 → 验收）

```
父执行体
  → 构造 task spec（core/schemas/spec.schema.json）
  → 调 coding-CLI（one-shot；flags 含 --max-wall-time + --approval-mode）
  → exit 0: 读 coding-runs 证据链 → 指纹验证（CAP-STORE T2）→ 验收
  → exit 55: bounded_failure（记 decision_log，≤3 次升级）
  → 其他: 失败（同上）
```

**硬约束**：
- `--max-wall-time` 必须设置（X4：有界性是本绑定的核心契约；无界调用 = 不合规调用）。
- critical_delivery（R1 类）：**禁止 yolo**（见 `skill-fragments.md` §4）。
- 无 SOUL.md 部署（CLI 无身份文件概念）。

## 3. 同步层

not applicable——无异步同步层；本地 read-after-write 强一致。

## 4. 失败序列与恢复

| 失败 | 检测 | 恢复 |
|------|------|------|
| 执行超时 | exit 55 | bounded_failure：记 decision_log；≤3 次升级（父执行体重派） |
| 执行失败（其他非零退出） | exit 码 | 同上（失败语义；decision_log） |
| 产物指纹不匹配 | coding-runs 校验和 vs 返回指纹 | 拒绝验收；三层审核链（见 `skill-fragments.md` §3） |
| 审批超时 / 无应答 | 审批提示无回应 | 父执行体 CAP-TIMER 判定 + 持久展示面兜底（本绑定审批面 = 同步提示；W5 持久面由父承担） |
| 状态丢失 | 不适用（本运行时 stateless） | 状态在父执行体 CAP-STATE；恢复按父执行体机制 |
| 运行时版本漂移（flag 行为变化） | TBD | TBD（运行时版本矩阵声明未提供） |
