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
    05-NMA           同行审查（Checklist/同行审查/多 critic MC-1~10/B-6）
    06-LIFECYCLE     递归拆解/完成信号/双通道/声明-验证/故障 SOP
    07-HANDOFF       跨团队（仅 single_user 编译）
    08-CONTRACT      契约 pinning + spec 结构化
    09-GOVERNANCE    投票/裁决/状态映射（B-4/B-5/B-8/C-3）
    10-LOOP          第 14 原语：loop_spec/五阶段/driver/反绕过
    11-SIGNAL        第 15 原语：7 封闭标记/三条效应/分层 reset
    12-REDLINES      安全红线 S1-S5/信任边界/可靠性分层/注意力装载
  schemas/           JSON Schema（10 个，L5 编译器 Validate 段消费）
  invariants/        状态机不变式（task/decision/loop/attention，4 篇，双语）
  scripts/           8 确定性脚本 + timer-derive（协议语义的可执行部分）
  binding-contract.md 8 能力接口（CAP-STATE/STORE/TIMER/NOTIFY/ATTN/SPAWN/EXEC/ROSTER，双语）
compiler/            6 段编译器（Validate→Assemble→Budget→Render→SelfCheck→Provenance）
templates/           模板库（skeleton 4 + fragment 12 + domain 21 + industry 6；全双语 X.md + X.en.md）
golden-tests/        L5 回归（10 门全绿：脚本测试 + 编译回归 + 冻结基线 + 生产溯源）
bindings/            参考绑定（agentteams / bare-qwenpaw / claude-code）
docs/                通用文档 + provenance/（照搬源流原文归档）
```

## 迁移路径（Strangler Fig，B-7）

**存量手编 SOUL 的团队不是推倒重来**——按三阶段绞杀：

1. **Shadow**：为现团队写一份 `team.json`（可改自 `golden-tests/fixtures/` 的 2 个参考实例：`example-biz-team.json`=single_user / `bizmarket-team.json`=multi_user），编译一遍，与现有 SOUL diff（审计：现协议有哪些条款新协议没覆盖）
2. **Parallel**：新编译的 SOUL 在部分角色启用（新任务走新协议，存量任务走旧）
3. **Cut**：全量切换，旧 SOUL 归档

迁移工具链（team.json 骨架生成 + 人工确认清单）在规划中（B-7，未随 v1.0 发布）。`golden-tests/fixtures/` 提供 2 个参考 team.json + 5 份生产基线 SOUL（占位化，见 `golden-tests/PRODUCTION-BASELINE.md`）。

## 版本

- **协议 v1.0**（2026-10-19 冻结基线）：语义变更 = minor；原语增删/模式定义变更 = major
- 绑定版独立版本化，声明"兼容 Millforge v1.x"
- 旧版本归档不删除（审计链）

## 来源链（重铸追溯）

NMProtocol 方案 v3.0（721L，2026-09-03 定案基座）
+ DeepSeek 八轮审查（2026-10-17~19，media/ 原文，全采纳 + 我方 4+3 处修正）
+ 生产实证（L4 重测 10 节点 / Manager 五问题 / #123 群历史 / #150 决策链 / #176 pydantic）
→ 定案文档：`AgentCom/千锻-DS审查分析-20261018.md` §A-W（工作区，不随开源）
