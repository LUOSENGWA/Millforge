## 契约 Pinning（精简装载版 · 全文 = 协议 §08-CONTRACT）

**契约物**：spec 中对下游有约束力的可观察部分（接口/格式/acceptance/锁定决策）→ CAP-STORE `contracts/<id>/<semver>.contract.json`；指纹 `contract:<semver>:<sha256-8>` 由 CAP-STORE 写入时计算返回（**不得自声明**）。

**双确认（S3）**：acceptance 需 provider + consumer 各一名独立确认者显式记录。B-9：contract owner ≠ consumer 实现者（fallback = 父级编排者/临时 spawn 独立确认者；不可避免 → 标 `contract_owner_is_implementer` + critic 复核强制）。

**Pinning 规则（B-3）**：派发时记录 contract_ref + pinned_fingerprint（exact-semver）。执行期契约变更 → 确定性判定（contract-revalidate）：
- `none` → accept
- `minor` → **在途任务 = 重验非返工**（按新契约重跑验收，不重做）
- `major` → **必返工**
- C-2 同线：provider/consumer 指纹必须同一 semver 线（major 号一致），否则按 major

**contract_snapshot（C-2，R6 回答必带）**：{task_id, contract_ref, pinned_fingerprint, checked_at} → 后续 spawn 继承回答前验证：指纹匹配 + 有效期内（默认 72h）；**不匹配 = 跨版本重验**（不自动失效回答，但重走一致性检查 + 验收）。

**decision_log 关联**：`contract_touch=true` 条目 = 截断保护（截断含契约条目 = 违规）+ 契约变更触发对其重验。
