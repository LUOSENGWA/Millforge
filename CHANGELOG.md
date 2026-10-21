# 变更日志

本文件记录 Millforge 协议编译器与参考绑定的对外可见变更。格式参照 [Keep a Changelog](https://keepachangelog.com/)，版本遵循语义化版本。

## [Unreleased]

### 新增

- **NMA 恢复结构化通信**：`05-NMA` 拆 Part A（8 型消息封闭清单 + 字段 + 7 条纪律）/ Part B（审查）；`06-LIFECYCLE` 派发三要素 = `DELEGATE` 必填字段。
- **NMH 来源判定 + 执行期随时问**：§7「未取得可验证来源」（fail-closed，弃权合法）；§8 结构化决策请求（CAP-ATTN 持久展示面 + CAP-NOTIFY 代码级事件）。
- **上下文窗口分档（S/M/L）**：`12-REDLINES §5.1–5.4`（分档预算 + 装载矩阵 + 越界行为）。
- **binding-contract 新增 21 条编号条目**（S5–S7 / T4–T6 / U5–U7 / V7–V8 / W8–W10 / X5–X7 / Y4–Y7；合计 55 条编号）。
- **绑定改名**：`bindings/single-agent` → `bindings/standalone-agent`（三形态：agentteams / standalone-agent / coding-cli）。

### 变更

- Loop 协议阶段 ↔ Loop CRD `status.state` 映射（`10-LOOP §2.1`）；task 运行时 9 态对齐上游任务契约。
- 能力声明改用「覆盖等级（完整/部分/声明降级）」；L1/L2/L3 仅用于可靠性分层。
- 仓内清理：移除内部轮次/日期/版本注记与 PR 进度表；README 结构树修正。

### 工程

- 编译器：`team.json` 新增可选 `context_tier`（S/M/L）；Budget 段新增常驻 token 门（`token_estimate` = CJK 字符数 + 非 CJK ÷ 4；声明 tier 时超限 fail，未声明只报告）；新增 `golden-tests/tests/test_tier_gate.py`。
- 绑定合规状态机：`bindings/*/compliance.json`（机器可读覆盖等级 + 缺口）+ `make compliance`；两级状态 `compliant` / `reference`（当前三绑定均为 reference）。
- 证据登记：`docs/EVIDENCE.md`（`[E#]` 外部引用 / 内部观察）+ `make evidence`。
- 附录上移：`bindings/reference-mappings.md`（跨绑定非规范附录）。

### 修复

- 不变式计数 46→55；死链；`spawn context_refs` 上限 4/6/8（含必填集）。

## [1.0.0] - 2026-10-20

### 新增

- **协议层 v1.0 冻结**：`core/protocol/` 13 篇双语条文（00-OVERVIEW ~ 12-REDLINES），CAP-* 8 能力 + 55 条不变式（34 条能力不变式 + 21 条实现子项/补充）。
- **核心文档**：`core/binding-contract.md`（绑定契约）、`security.md`（威胁模型 + 机制矩阵 + 5 场景）、`cost-model-tiering.md`（成本三档）、`production-harden.md`（生产化 4 补丁）、`calibration/token-shadow-calibration.md`。
- **JSON Schema ×11**：team / spec / task_meta / decision_log / contract / contract_snapshot / handoff / loop_spec / scorecard / signal_event / aggregation_result。
- **确定性脚本 ×9**（`core/scripts/`）：validate-decision-log / detect-conflict / contract-revalidate / attention-stall / verification-mismatch-window / saga-compensate / consistency-check / aggregate-vote / timer-derive。
- **不变式文档 ×4 双语**：attention-state / decision-state / loop-state / task-transitions。
- **编译器**：6 阶段零 LLM 管线（Validate → Assemble → Budget → Render → SelfCheck → Provenance），`validate` / `compile` 子命令。
- **模板 ×43 双语**：skeleton ×4 / fragments ×12 / domain ×21 / industry ×6，注册表 `templates/INDEX.yaml` 带三级出处纪律（production / reference / llm）。
- **参考绑定 ×3**：`bindings/agentteams`（含 mapping-table / skill-fragments / cron-spec / deployment-guide / s3-storage 五件正文）、`bindings/standalone-agent`（裸 QwenPaw 等独立 agent 运行时）、`bindings/coding-cli`（Claude Code / QwenCode / OpenCode 等编程 CLI 运行时）。
- **golden-tests**：生产基线 35 条（`PRODUCTION-BASELINE.md`）+ 编译门 13 + 脚本断言 83 + 断言覆盖记档（`ASSERTION-COVERAGE.md`）。
- **CI**：GitHub Actions 三门（golden / 双语完整性 / 敏扫）+ `requirements.txt` + `Makefile` + SECURITY / VERSION。

### 变更

- **绑定层按架构形态重组**：`bindings/agentteams`（AgentTeams 参考绑定，运行时不敏感）/ `bindings/standalone-agent`（独立 agent 运行时：QwenPaw / OpenClaw / Hermes…）/ `bindings/coding-cli`（编程 CLI：Claude Code / QwenCode / OpenCode…）；产品差异改为矩阵行。状态目录路径更正为 `.qwenpaw/workspaces/`（qwenpaw ≥2.1；`.copaw` 为旧 copaw 运行时）。

- 绑定层与协议层分离定案：运行时专名仅允许出现在 `bindings/`。
- 编译器不实现 `binding_profile` 参数（降级定案：绑定差异由 `bindings/` 文档 + 运行时片段注入承载）。

### 已知限制

- 事件面发射（SIG-*) 与 Loop reconciler 在下游运行时侧实现，本仓只定义 schema 与不变式。
- 部分 golden 断言依赖运行时事件面（见 `golden-tests/ASSERTION-COVERAGE.md` Blocked 清单）。
