# 断言覆盖记档（ASSERTION-COVERAGE）

> 本文件随断言增补更新；`PRODUCTION-BASELINE.md` 冻结不动。
> 断言入口：`golden-tests/scripts/run-scripts-tests.sh`（本批新增 section 10「PR-3 断言补全」，PASS 54 → 83）。
> 原则：断言值一律取自 `core/scripts/` 与 `core/schemas/` 的现有输出（退出码 / stdout JSON 字段）；runner 零 LLM、零外部依赖（python3 标准库 only）。
> 目的：把「可确定性断言」与「载体缺失、不可断言」的协议行为显式分开，防止「以为覆盖了」。

## A. 设计评审风险点（10）

| # | 风险点 | 现状 | 处置 |
|---|---|---|---|
| 1 | decision_log 物理位置 + schema 校验层 | ✅ 已覆盖（validate-decision-log 5 用例：valid / schema violation / 超限无 truncated / truncated+contract_touch / parse failure） | — |
| 2 | 合并冲突检测执行位置 | ✅ 已覆盖（detect-conflict 5 用例：shared surface 22 / hard conflict 20 / assumption conflict 21 / dimension mismatch 20 / no overlap 0） | — |
| 3 | 契约版本 pinning（minor/major） | ✅ 已覆盖（contract-revalidate 5 用例：none 0 / minor 30 / major 31 / report missing 32 / semver 跨线 31） | — |
| 4 | R5 锁定者超时（权重降级、非默认同意） | ✅ 已覆盖：原 1 不可逆 81/block 用例；本批补 3 用例（B-4 迟到降权 2.0→1.0、可逆超时=wait、defer 记 dissent 不计分母） | 新增 10.1–10.3 |
| 5 | R6 停摆累积（2 升级 / 3 冻结） | ✅ 已覆盖（attention-stall 5 用例：3 stale 41 / 2 stale 40 / 1 fresh 0 / 人工应答 0 / meta missing 42） | — |
| 6 | critic vs 人锁 spec 死循环（24h 终裁） | ⚠️ 部分：verification-mismatch-window 覆盖 24h 窗口侧（B-6）；终裁权属协议级行为，非脚本行为 | Blocked（缺载体：24h 终裁记录格式或裁决脚本；需新增 core 脚本或协议规则） |
| 7 | 生产团队迁移路径 | ❌ 不可断言（流程/运维域，非协议编译器行为） | out-of-scope |
| 8 | multi_user × NMH 路由 | ❌ 不可断言（路由语义归 binding 层映射表规划，协议编译器不产路由） | out-of-scope（binding 映射表落地后可断言） |
| 9 | contract owner 独立性（2W 规则） | ❌ 无载体：无任何规则脚本/编译器规则检查 contract owner 与 consumer 的独立性 | Blocked（缺载体：contract owner 独立性编译器规则） |
| 10 | decision_class 误分类（saga 补偿） | ✅ 已覆盖（saga-compensate 5 用例 + consistency-check 6 用例） | — |

## B. 协议断言：signal + multi-critic（6）

| 断言 | 现状 | 处置 |
|---|---|---|
| signal ① 未标记「已完成」不通过验收 | ❌ 无验收脚本载体 | Blocked（缺载体：验收门禁脚本，校验完成标记 signal；需新增 core 脚本） |
| signal ② hard reset 后 signal 集合一致 | ❌ 无状态机场景测试骨架 | Blocked（缺载体：状态转移场景 fixture + 重跑比对脚本，或状态机测试 harness） |
| signal ③ 审查 refs 零 is_signal=false | ✅ 已覆盖：本批补 `signal_event.schema.json` schema 级校验 3 用例（required + event_type 封闭清单，取值读自 schema 文件，不硬编码第二份清单） | 新增 10.4 |
| multi-critic ① 单模型族投票不得当多 critic 通过 | ⚠️ 载体存在（`scorecard.schema.json` 的 `critic_model_family`），规则未脚本化 | 本批补 schema 级 3 用例（含值合法 0 / 缺省合法 0 / 缺必填 1）；≥2 模型族规则 Blocked（缺载体：multi-critic 聚合规则脚本） |
| multi-critic ② 平票必须升级人 | ✅ 已覆盖：原 tie=80 用例 + 本批补 `next=escalate` 断言 | 原 section 8 用例 + 新增断言 |
| multi-critic ③ 少数 dissent 必记录 | ✅ 已覆盖：本批补 3 用例（defer=abstain 记 dissent、reject 时少数 approve 记 minority、blocked 态 defer 计入分母） | 新增 10.3 / 10.7 / 10.8 |

## C. Blocked 项清单（缺什么载体、要什么才能断言）

| 项 | 缺失载体 | 断言所需 |
|---|---|---|
| signal ① | 验收门禁脚本 | 新增 core 脚本（验收时校验完成标记 signal 存在）+ golden 场景 |
| signal ② | 状态机场景骨架 | hard reset 场景 fixture + signal 集合重跑比对脚本（或状态机测试 harness） |
| multi-critic ①（规则级） | multi-critic 聚合规则脚本 | 新增 core 脚本：`critic_model_family` ≥2 族检查（schema 级载体本批已钉住） |
| 风险点 6 | 24h 终裁记录/脚本 | 裁决记录格式（或裁决脚本）+ golden 场景 |
| 风险点 9 | contract owner 独立性编译器规则 | 编译器规则：owner ≠ consumer（2W）检查 |

## D. 断言值口径注记（与初稿措辞的偏差）

所有退出码/字段值以 `core/scripts/` 与 `core/schemas/` 当前实测输出为准；初稿措辞与实测不符处按实测修正如下：

1. **10.3（R2 defer 平票）**：平票路径确定性退出 80（`s_a==s_r → tie/escalate/80`）。初稿写 0，修正为 80（与既有 tie=80 用例及 multi-critic ② 的 tie→escalate 语义一致）。
2. **10.5（scorecard）**：`critic_model_family` 不在 schema 的 `required` 内（单 critic 场景合法缺省），故断言 缺省 → 0（钉住载体可选性）；另补真正必填缺失负例（缺 `verdict` → 1）钉住 required 集合。初稿写「缺 critic_model_family → 1」，按 schema 事实修正。
3. **10.8（blocked 态 defer 计入分母）**：初稿未指定退出码；实测 80——defer 计入分母把 would-be pass 翻成 tie，正是 B-5 的可观测证据，故按 80 断言。
