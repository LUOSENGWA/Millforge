# core/ — 千锻核心层（Apache-2.0）

> 运行时无关的协议语义 + 确定性实现 + 编译器 + 模板库 + 回归测试。
> **通用词纪律**：本目录只许 CAP-* 能力编号 + 通用词（子代理/父执行体/主会话/持久展示面/运行时调度器/对象存储/通知通道/决策记录/状态存储/定时器）。
> 运行时专名（spawn_subagent、cron、mc、dashboard、Matrix、MinIO/RustFS…）**只允许出现在 `bindings/` 层**。

## 目录

```
core/
  protocol/          协议条文（13 件，v1.0 冻结基线）
    00-OVERVIEW      总则：定位/原则 P1-P8/文档地图/版本策略/不做的
    01-PRIMITIVES    15 原语 + 角色不变量
    02-MODES         single_user / multi_user 相变
    03-DECISIONS     R1-R6 + decision_log + 类型封闭
    04-NMH           人↔Agent 协作探索（探索/锁定/七问/演化）
    05-NMA           Agent 间结构化通信（Part A）+ 同行审查（Part B：Checklist/多 critic MC-1~10/B-6）
    06-LIFECYCLE     递归拆解/完成信号/双通道/声明-验证/故障 SOP
    07-HANDOFF       跨团队（仅 single_user 编译）
    08-CONTRACT      契约 pinning + spec 结构化
    09-GOVERNANCE    投票/裁决/状态映射（B-4/B-5/B-8/C-3）
    10-LOOP          第 14 原语：loop_spec/五阶段/driver/反绕过
    11-SIGNAL        第 15 原语：7 封闭标记/三条效应/分层 reset
    12-REDLINES      安全红线 S1-S5/信任边界/可靠性分层/注意力装载/上下文分档
  security.md        威胁模型 + 安全章节 v1.0（信任边界/完整性机制矩阵/5 对抗场景/通道身份最低要求/升级规则，双语）
  cost-model-tiering.md  协议成本模型 + 三档分层 v1.0（simple/standard/full，档位=spec 创建期锁定，双语）
  production-harden.md   生产化 4 补丁 v1.0（协议版本化/native 上下文预算/批量委托/时钟权威，双语）
  calibration/       校准规程（token-shadow-calibration v1.0，token 影子计数，双语）
  schemas/           JSON Schema（11 个：team.schema 供编译期 Validate；其余供运行时产物校验）
  invariants/        状态机不变式（task/decision/loop/attention，4 篇，双语）
  scripts/           9 确定性脚本（8 + timer-derive；协议语义的可执行部分）
  binding-contract.md 8 能力接口（CAP-STATE/STORE/TIMER/NOTIFY/ATTN/SPAWN/EXEC/ROSTER，双语）
compiler/            6 段编译器（Validate→Assemble→Budget→Render→SelfCheck→Provenance；Budget = 行硬门 + 声明 context_tier 时的常驻 token 门）
templates/           模板库（skeleton 4 + fragment 12 + domain 21 + industry 6；全双语 X.md + X.en.md）
golden-tests/        L5 回归（T1–T10 / 13 用例 / 83 脚本断言 + 冻结基线 + 生产溯源 + 证据/合规/tier 单元门）
bindings/            运行时绑定（agentteams 参考绑定 / standalone-agent / coding-cli；产品做矩阵行）
migration/           B-7 迁移工具（scaffold-team.py 骨架生成 + MIGRATION-CHECKLIST.md 人工确认清单）
docs/                通用文档 + provenance/（照搬源流原文归档）
```

## 迁移路径（Strangler Fig，B-7）

**存量手编 SOUL 的团队不是推倒重来**——按三阶段绞杀：

1. **Shadow**：为现团队写一份 `team.json`（可改自 `golden-tests/fixtures/` 的 2 个参考实例：`example-biz-team.json`=single_user / `bizmarket-team.json`=multi_user），编译一遍，与现有 SOUL diff（审计：现协议有哪些条款新协议没覆盖）
2. **Parallel**：新编译的 SOUL 在部分角色启用（新任务走新协议，存量任务走旧）
3. **Cut**：全量切换，旧 SOUL 归档

迁移工具链**已随版**：`migration/`（scaffold-team.py 骨架生成 + MIGRATION-CHECKLIST.md 人工确认清单）。`golden-tests/fixtures/` 提供 2 个参考 team.json + 5 份生产基线 SOUL（占位化，见 `golden-tests/PRODUCTION-BASELINE.md`）。

## 版本

- **协议 v1.0**（冻结基线）：语义变更 = minor；原语增删/模式定义变更 = major
- 绑定版独立版本化，声明"兼容 Millforge v1.x"
- 旧版本归档不删除（审计链）

