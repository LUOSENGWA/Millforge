# 决策类 R1-R6 + decision_log

> v1.0
> 核心立场：**按可逆性分层，不按"重要程度"分层**——可逆性可机器判定（有无回滚路径/是否触碰外部副作用/是否消耗不可回收资源）。

## 1. 决策类型 × 聚合规则矩阵

| # | 决策类型 | 判定条件（可机器检查） | 聚合规则 | 锁语义 |
|---|---|---|---|---|
| **R1** | 不可逆 / 外部副作用 | 部署到生产、删除 artifact、发送外部通信、合并到主分支、消耗预算超阈值 | **Owner 单点裁决**；非 owner 反对记 dissent 不阻塞；owner 缺席 → 升级 human | owner 锁定后**不可被另一用户直接推翻**；推翻必须走 R5 显式重开 |
| **R2** | 资源消耗 / 预算 | 新增执行单元、长时运行任务、外部 API 花费 | **加权多数**（weight × 票，>50%）；平局 → 升级 | 锁定后**预算执行前**可被新加权多数推翻（资源未消耗，可逆） |
| **R3** | 风格 / 质量取舍 | 命名、格式、措辞、布局、文档结构等不影响可观察契约的选择 | **默认不聚合**：执行该 artifact 的单一执行者决定；异议走 NMA 返工；≥2 相关方显式要求投票时才加权多数 | 无锁；NMA 返工可覆盖 |
| **R4** | 可逆实现细节 | 内部实现选择、不影响外部契约的依赖/结构 | **自动通过**；自主决定，记入 decision_log | 无锁；随时可改 |
| **R5** | 推翻已锁定决策 | 任何相关方要求重开一个已锁定决策节点 | **显式重开协议**（§3） | 锁定不是永久不可变，而是**重开成本显著高于首次决策** |
| **R6** | 规格歧义 / attention 请求 | 执行中遇到需求歧义、权限边界、取舍，无法从 spec 判定 | **路由到 accountable stakeholder**（§4）；回答写入状态后锁定 | 后续子执行单元继承该回答，不得在子执行层私自推翻 |

**规则预算**：6 条聚合规则 + 1 条路由规则。
**兼容性**：single_user = multi_user 在 stakeholder set = {1 人} 时的退化。R1 退化为"人锁定"；R2 退化为"一票即多数"；accountable 即该人。

## 2. decision_log（B-1）

**定位**：执行期"非显然决策"的落盘契约。状态必须落盘（Matrix 静默丢消息教训：消息不是状态）。

**存储形态**（绑定层实现，核心只定语义）：
- 位置 = 对象存储（CAP-STORE），路径契约 `decisions/<task_id>/<spawn_id>.decision.json`
- 消息中只带 **ref + sha256-8 指纹**，不带内容（注意力保护 + 防篡改）
- append-only（CAP-STORE T3 可选语义；绑定层用 JSONL/不可变对象实现）

**三层 schema 校验**（确定性，脚本实现 = `core/scripts/validate-decision-log.sh`）：

| 层 | 时机 | 执行者 | 内容 |
|----|------|--------|------|
| 1 | spawn 返回后、**验收前**（父执行体跑） | 父执行体（LLM 不能自我校验） | schema 完整性：字段/枚举/条数 ≤10（contract_touch 条目不得被截断） |
| 2 | 多 spawn 合并前 | 父执行体（`detect-conflict.py` 纯函数） | 冲突检测：同 artifact 同 field 值不同 = hard；同 key 假设相反 = assumption；仅共享面 = 送 Step 4 |
| 3 | 验收时 | critic / 父执行体 | `decision_log_ref` 指纹 vs 消息携带指纹一致；不一致 = 拒收 |

**条目上限**：≤10 条；超限 = 截断，但 `contract_touch=true` 的条目**全部保留**（截断含 contract_touch = schema 违规 exit 11）。

## 3. R5 显式重开协议

重开请求必须包含：**新证据 + 受影响的 acceptance criteria**。

- **原锁定者权重 ×2** 参与加权多数
- 原锁定者反对 **且** 新证据不触及 acceptance criteria → 重开失败，锁定维持
- 原锁定者超时（B-4）：不可逆 24h / 可逆 4h 窗口；超时 = ×2 权重**失效降 1.0**（**非默认同意**）；迟到应答 → 恢复权重重算；旧锁保留并标"被 R5 覆盖"

## 4. attention 路由规则

1. 每个 task 创建时绑定一个 **accountable stakeholder**（默认 = project owner；可按 task 类型委派；委托链可查询 = CAP-ROSTER Z3）
2. attention 请求发给 accountable，抄送所有 approver（只读旁路，不阻塞）
3. 超时分两级：可逆（R2/R3/R4）30min → 弃权计，其余形成多数则生效，否则升级 owner；不可逆（R1/R5/R6 触外部副作用）2h → 任务阻塞（**不自动通过**）+ 通知 owner 与仲裁方
4. 两人答案冲突：都 approver 无 owner → R2 加权多数；其一为 accountable → 该人优先，另一人记 dissent；同权无 accountable → "无多数"升级；**任何情况不允许执行体用 LLM 总结两份人类回答后择一执行**——只能执行协议层算出的聚合结果

**加权多数适用范围（C-3 硬约束）**：仅限 **R2 / R4（及 R5 重开投票）**；**永不用于触及已锁定 spec 的 R6 回答**（见 §09-GOVERNANCE locked_spec_consistency_check）。

## 5. decision_class 误分类（B-10）

**场景**：编译期标 R4、执行期发现涉 R1 外部副作用——分类**错误**（非歧义）。

```
mismatch 事件 → 暂停 + 重分类
  R4→R1: 暂停 2h 重新分类
  R3→R2: 事后聚合
  R2→R1: 重做
decision_class_v2 = 新记录，不覆盖原值（审计链）
已执行副作用走 saga 补偿：
  未提交 → 生成补偿指令（逆依赖序，core/scripts/saga-compensate.py）
  已提交且不可补偿 → 升级 human
同一 task ≥2 次 mismatch → 审计该 task 的分类质量（Leader 分类错误率）
```

**分类裁决权**：编译期规则表 + task spec 的 `decision_class` 字段（实例参数由 Leader 填、人锁）。分类歧义 → 升级到 accountable 做**一次性分类裁决**（人只裁决"属于哪条规则"，不执行聚合）。

## 6. 类型封闭（C-1）

- decision_log 条目的 `type` 是**封闭枚举**，由类型注册表（CAP-STORE 中的 registry 文件）定义，每项带**语义维度标签**
- `type_dimension_mismatch`（同 artifact 被不同维度的 type 触碰）= **hard-conflict，卡在第 1 层校验**
- 新 type 必须经 critic 审核入注册表版本；**禁止运行时发明** type
- 注册表未覆盖的 type = schema 违规（绑定层在部署时全量预置）
