# 契约 Pinning + Spec 结构化

> v1.0
> 契约 = spec 中**对下游有约束力的可观察部分**（接口/格式/acceptance/锁定决策），以内容寻址 artifact 形式 pin 在共享存储。

## 1. 契约物（contract artifact）

- 位置：CAP-STORE 路径契约 `contracts/<contract-id>/<semver>.contract.json`
- 指纹格式：`contract:<semver>:<sha256-8>`（由 CAP-STORE 写入时计算并返回，**不得自声明**）
- **双确认（S3）**：acceptance 需 **provider + consumer 各一名独立确认者**显式记录（CAP-ROSTER Z1 权重=角色）
- **B-9 contract owner 独立性**：contract owner 不得是 consumer 实现者本人；fallback = 父级编排者或临时 spawn 的独立确认者；不可避免时显式标 `contract_owner_is_implementer: true` + critic 复核强制

## 2. Spec 结构化（NMH 锁定时的强制字段）

task spec / loop spec 必须含：

| 字段 | 说明 |
|------|------|
| `goal` | 一句话目标（非过程描述） |
| `acceptance` | **结构化 acceptance_criteria**（每条 {id, 检查方式, 通过标准}）——自然语言 acceptance 是 C-3 一致性检查判不了的地带 |
| `out_of_scope` | 显式排除项（防 scope 漂移） |
| `decision_class` | R1-R6（Leader 填、人锁；§03-5 误分类处置） |
| `contract_ref` | 涉及的契约 pin（`ref + fingerprint`，可多个） |
| `critical_delivery` | bool（多 critic 投票启用条件之一，§05-7） |

## 3. 契约 pinning 规则（B-3）

- **pin = exact-semver + 指纹**：派发时记录 `contract_ref` 与 `pinned_fingerprint`
- 执行期契约变化 → **contract-revalidate 判定**（`core/scripts/contract-revalidate.sh`）：
  - `none` → accept
  - `minor` → **在途任务 = 重验非返工**（产出按新契约重跑验收，不重做）
  - `major` → **必返工**
- **C-2 同线约束**：provider / consumer 的契约指纹必须同一 semver 线（major 号一致），否则至少 major 处理

## 4. 契约快照（contract_snapshot，C-2）

- **R6 attention 回答必须带 contract_snapshot**：`{task_id, contract_ref, pinned_fingerprint, checked_at}`
- 后续 spawn 继承回答前验证快照：指纹匹配 + 在有效期内（绑定层声明窗口，默认 72h）
- **指纹不匹配 → 跨版本重验**（不自动失效回答，但必须按新契约重走一致性检查 + 验收）
- 快照写入 CAP-STATE（task meta），不依赖消息留存

## 5. 与 decision_log 的关系

- `decision_log` 条目 `contract_touch=true` = 该条目触碰契约面 → 截断保护（§03-2）+ 任何 contract 变更触发对其重验
- 契约面决策（R1/R5 锁定的接口/格式）= handoff 中"约束 & 依赖"的权威来源

## 6. 确定性实现（P4/P5）

| 检查 | 脚本 | 落层 |
|------|------|------|
| semver 分类 + 重验触发 | `core/scripts/contract-revalidate.sh` | L2 |
| 指纹验证（合并前重读比对） | CAP-STORE `fingerprint(ref)` 调用 | L1/L2 |
| contract_snapshot 匹配 | `core/scripts/consistency-check.py` 前置检查 | L2 |
