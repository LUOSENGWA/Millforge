# 迁移规程（B-7，Strangler Fig 三阶段）

> 本目录是**存量团队迁移到千锻协议**的随版工具与规程。原则：不推倒重来，用绞杀榕三阶段渐进替换。

## 三阶段

| 阶段 | 做什么 | 产出 | 退出条件 |
|---|---|---|---|
| **1. 影子（Shadow）** | 存量团队照常运行；用 `scaffold-team.py` 从现有角色**反向生成** `team.json` 骨架；编译产物只做对比，不部署 | `team.json`（含 TODO 标记）+ 差异报告 | 骨架覆盖全部现有角色与职责，差异报告无未知角色 |
| **2. 并行（Parallel）** | 新协议片段（decision_log / contract / critic 隔离）以**增量方式**加进影子团队跑；关键决策双写（旧流程 + 新协议产物） | decision_log / contract_snapshot 产物样例 + 人工确认清单逐项打勾 | 双写一致率达到预设阈值；清单全绿 |
| **3. 切换（Cutover）** | 旧流程下线，新协议成为唯一执行路径；保留回滚窗口 | 切换记录 + 回滚预案 | 回滚窗口结束无异常 |

## 骨架生成器用法

```bash
python3 migration/scaffold-team.py \
  --from <存量角色目录（含 *.soul.md）> \
  --name my-team --mode multi_user --lang zh \
  --out team.json
```

- 只读取角色文件名与首段身份行，推断 `id` / `kind`（coordinator / leader / worker / critic）；
- 生成 **schema 合法**的 `team.json`，未知字段一律填 `TODO:` 占位（charter 目标、scope、权重、预算）；
- 不做任何网络/LLM 调用（确定性，可重复执行）；同输入 → 同输出。
- 生成后必须过 **人工确认清单**（`MIGRATION-CHECKLIST.md`）才允许进阶段 2。

## 边界

- 本工具**不**修改存量团队的任何运行文件；只产出新文件。
- 不可自动推断的内容（人类成员、权重、决策类别）**必须人工填**，禁止默认猜测。
- 与冻结基线的关系：迁移团队的 `team.json` 不进 `golden-tests/`；冻结基线只属于协议回归。
