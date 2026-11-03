# 机器契约（JSON Schema）— 与协议正文的映射

> 本目录是 `core/protocol/` 协议条款的**机器可校验形态**。协议定"语义"，schema 定"字段"；
> 两者必须一起改。`make test` 的 `schemas` 门做两件事：校验 schema 自身合法、校验随仓实例符合 schema，
> 并**要求每份 schema 在本文登记**（未登记 = 孤儿 schema，门直接红）。

**English**: [README.en.md](README.en.md)

## 映射表

| Schema | 协议出处 | 谁写 · 谁读 | 随仓实例 |
|:--|:--|:--|:--|
| `team.schema.json` | `01-PRIMITIVES.md`（CAP-ROSTER：角色与 accountable）+ `02-MODES.md`（single_user / multi_user 形态） | 人写 `team.json` → 编译器读 | `golden-tests/fixtures/*.json`（2 份） |
| `spec.schema.json` | `04-NMH.md`（spec 人锁：goal / acceptance / out_of_scope / decision_class） | Leader 写 → NMH 锁定 → 执行体读 | — |
| `task_meta.schema.json` | `09-GOVERNANCE.md`（`decision_status` 协议子状态叠加层；`timeout_at` 是超时唯一权威）+ `06-LIFECYCLE.md`（状态机副作用归 L1/L2）。**运行时 9 态不在本 schema**，归 TeamHarness | TeamHarness 写 → 视图与验收读 | — |
| `signal_event.schema.json` | `11-SIGNAL.md`（7 个 SIG-* 封闭清单 + `is_signal` / `ref` / `fingerprint`） | 执行体 emit → 审查/验收/闭环读 | — |
| `decision_log.schema.json` | `12-REDLINES.md` **S2**（防伪 decision_log：ref + 指纹 + append-only） | 派发时写 → 验收双源比对 | — |
| `scorecard.schema.json` | `05-NMA.md`（同行审查评分卡） | critic 写 → 聚合读 | — |
| `aggregation_result.schema.json` | `03-DECISIONS.md`（R1–R6 决策聚合结果） | 聚合器写 → 闭环读 | — |
| `contract.schema.json` | `08-CONTRACT.md`（接口契约本体） | 契约方写 → 双方 pin | — |
| `contract_snapshot.schema.json` | `08-CONTRACT.md`（pinning 快照：`pinned_fingerprint` + `checked_at`） | 执行体写 → 漂移检测读 | — |
| `handoff.schema.json` | `07-HANDOFF.md`（跨团队交接：context / key_decisions / tasks_for_receiver） | 上游团队写 → 下游团队读 | — |
| `loop_spec.schema.json` | `10-LOOP.md` §1（`iteration_budget` / `convergence_rule` / `re_plan_rule` / `termination_action` / `cross_team_reflow`＝§5 跨团队回流） | 人锁预算 → Runner 读 | — |
| `looprunner-manifest.schema.json` | 设计文档 `12-Loop Runner 接口预留`（2026-11-03）§2.1（manifest：`version` / `protocol_version` / `kind` / `entrypoint` / `capabilities` / `requires`） | 上游 release 产出 → 安装器/客户端读 | — |
| `occurrence.schema.json` | 设计文档 `12-Loop Runner 接口预留` §2.2（发生：一次到期的唯一记录，去重键 = `(loop_id, window_start)`）；`10-LOOP.md` | 调度器（Runner 或内置 ticker）写 → controller/前端读 | — |
| `iteration.schema.json` | 设计文档 `12-Loop Runner 接口预留` §2.3（迭代：租约 + 预算 + 终止依据；`10-LOOP.md` 五要件） | Runner 写 → controller 读 | — |
| `kick.schema.json` | 设计文档 `12-Loop Runner 接口预留` §2.4（kick：唯一投递目标 = controller，幂等键 = `iteration_id`，`unknown` 不重放） | Runner 写 → controller 投递并读三态 | — |

## 使用方式

**校验器入口**：`python3 core/scripts/validate-schemas.py`（`make schemas` / `make test` 已包含）。

**新实例如何被自动覆盖**：JSON 文件顶层写 `"schema": "millforge/schemas/<name>.json"`（或 `$schema`），
门会自动按该 schema 校验；团队定义（含 `name`/`roles`/`roster`）无需标注，默认按 `team.schema.json`。

**改协议的纪律**：改 `core/protocol/` 的字段语义 → 同一次提交改对应 schema → 跑 `make test`
（schema 门 + T9 冻结基线门会同时红，逼你显式重冻）。

## 已知边界

- schema 只覆盖**结构**，不覆盖跨字段业务规则（如"终态不可逆""双源指纹一致"）——那些由协议条款 + 实现侧测试保证。
- 目前随仓实例只有 team 两类；其余 schema 尚无实例文件，等对应机制落地时补（届时门会自动校验）。
