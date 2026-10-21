# 致谢与机制源流（ACKNOWLEDGMENTS）

> 本文件是千锻的出处账本。**照搬（机制逐字继承）必注出处**是千锻开源的红线纪律：
> 漏注 = 开源事故。本文件按三级纪律组织（照搬 / 适配 / 参考），并列出本仓库不包含的内部设计源流。

## 1. 照搬（逐字继承，原文可核）

**NMH（协作探索/审讯锁定协议）← QwenPaw 社区 skill `grill-me` / `grill-with-docs`**

继承点逐条对照（原文归档于 [`docs/provenance/grill/`](docs/provenance/grill/)，按原样保留）：

| 千锻 NMH 机制 | 源流（原稿表述） |
|------|------|
| 决策树逐分支审讯（沿树走分支，逐层解决依赖） | grill-me: "Walk down each branch of the design tree, resolving dependencies between decisions one-by-one" |
| 逐题追问（一次一问，不批量轰炸） | grill-me: "Ask the questions one at a time" |
| 每问附推荐项（选项 + 推荐 + 理由） | grill-me: "For each question, provide your recommended answer" |
| 可由上下文查证的问题先去查证再问 | grill-me: "If a question can be answered by exploring the codebase, explore the codebase instead" |
| 术语对齐：冲突术语即时指出（"你说的是 X 还是 Y？"） | grill-with-docs: "Challenge against the glossary … call it out immediately" |
| 模糊语言锐化（过载词 → 精确规范术语） | grill-with-docs: "Sharpen fuzzy language … propose a precise canonical term" |
| 具体场景压力测试 | grill-with-docs: "Discuss concrete scenarios … stress-test them with specific scenarios" |
| 落盘纪律：术语/决策即时写入文档，不攒到最后（"文件即契约"的即时性） | grill-with-docs: "Update CONTEXT.md inline … capture them as they happen" |
| 高权重决策的克制提出（不可逆 + 意外 + 真实权衡三条件齐备才升级） | grill-with-docs: "Offer ADRs sparingly — Only offer … when all three are true"（千锻对应 R1/R6 的 attention 提出门槛） |

**千锻扩展（非继承，自研）**：探索/锁定双模式、锁定前七问自检、NMH 文档结构（节点/选项/人类原话/时间戳）、R5 版本演进（append 不覆盖）、锁定输出为结构化 spec（goal/acceptance/out_of_scope/decision_class/contract_refs）、与 7 封闭信号体系集成。这些在源稿中不存在。

## 2. 适配（机制借鉴，千锻化改造）

| 千锻机制 | 借鉴对象 | 千锻化改造 |
|------|------|------|
| NMA 同行审查（审查票/复审循环/升级链） | 通用软件工程的 ticket-based peer review 实践（无特定上游，属公开工程惯例） | 票面三要素（检查什么/命令/预期）+ 🟢🔵❌ 证据分级 + 隔离边界（审查者不进被审者 workspace）+ 多 critic 投票（≥2 模型家族）+ B-6 僵局防御 |
| 契约 Pinning（semver 固定 + 指纹） | 通用软件依赖管理/语义化版本实践 | 契约对象 = spec 的对外绑定面（非代码包）；双确认（提供方+消费方）；in-flight 变更的 minor=重验/major=返工判定 |
| 行硬门预算（身份文件行数上限，超限=fail） | 通用 LLM 上下文工程实践（注意力预算意识） | 编译期强制（Budget 段），不截断；U 形注意力分布 → 三层装载 |
| 故障 SOP（restart→重派→3 次升级） | 通用服务运维的"指数退避/升级"思想 | 固化为角色义务（编排者绝不做工），次数与升级路径实例参数化 |

## 3. 参考（设计审查中引用，非继承文本）

- **分布式系统 12 原则**：千锻每个架构决策后的方法论压力测试框架（引用其原则维度，未复制其文本）。
- **外部强模型多轮对抗审查流程**：协议层 v1.0 的审查方法——每一轮由外部强模型对抗审查，缺口全部采纳或记录理由。这是千锻的**审查流程**（过程学分），非机制源流。
- **内部设计源流（不随本仓库发布）**：NMProtocol 方案 v3.0（千锻的语义基座，内部文档）、SATCOM（协议前身，内部）、多轮生产事故复盘（千锻各机制的生产事故驱动出处，见各协议篇「定案」节的内部引用编号）。这些内容已在协议层**脱敏通用化**（通用词纪律），原文不随开源包发布。

## 4. 第三方软件依赖

| 依赖 | 用途 | 许可 |
|------|------|------|
| Python 3 标准库 | 编译器主体 | PSF |
| `jsonschema` | team.json Schema 校验 | MIT/Apache-2.0 双许可 |
| `pyyaml` | INDEX.yaml 解析 | MIT |

## 5. 纪律声明

1. 本仓库正文（协议/模板/文档）**零句子级复制**外部文本——上表第 1 节的逐字对应仅存在于**机制模式**层面（决策树逐分支审讯等行为模式），千锻正文的表述全部为千锻术语体系下的重写。
2. 唯一例外：`docs/provenance/grill/` 中的两份 skill 原文按原样保留（照搬必注出处，原文可核）。
3. 新增照搬点必须：① 本文件加行 ② 原文归档 `docs/provenance/` ③ 协议篇「设计源流」节同步。三者缺一 = PR 不得合入。
