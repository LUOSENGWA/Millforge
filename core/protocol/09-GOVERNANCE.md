# 治理：投票、裁决、状态映射

> v1.0
> **聚合执行边界**：计票、超时判定、升级触发全部是**纯函数逻辑**（core/scripts/，L2）——人类只提供投票/裁决输入，执行体只执行协议层算出的结果。

## 1. 投票执行（确定性）

- **R2/R5 加权计票** = `core/scripts/aggregate-vote.sh`（exit 0=pass/reject/wait，80=平局升级，81=不可逆超时阻塞，82=数据不可读）
- 权重 = **角色权重**（owner/approver/informed × 数值），不是模型置信度
- 计票输入 = CAP-STATE 中的 attention 条目 votes[]（状态权威），不是消息流
- **平局不重投**（直接升级）；**无票 ≠ 同意**（缺席不是票）

## 2. R5 locker 超时（B-4）

- 窗口：不可逆 **24h** / 可逆 **4h**
- 超时 = 原锁定者 ×2 权重**失效降 1.0**（**非默认同意**）
- 迟到应答 → 恢复权重重算
- 旧锁保留并标"被 R5 覆盖"（审计链，不删除）

## 3. R6 停摆熔断（B-5）

- attention 超时未应答计数 = **派生值**（`core/scripts/attention-stall.sh`，读 CAP-STATE 计算，非写入累加）
- **第 1 次**：watch（记录）
- **第 2 次**：升级 accountable stakeholder + task `blocked` + **禁弃权计票**（defer 计入分母，对通过不利）
- **第 3 次**：task `frozen`，**人显式解冻**（无自动恢复）
- **任何人应答 → 计数归零**（派生语义：只统计最近一次人应答之后开立的 open 超时项）

## 4. NMH × multi_user 约束（B-8）

- **accountable 持锁**：R6 规格回答的锁定权归 accountable stakeholder，不加权投票
- 加权多数**仅限 R2 资源类**（及 R5 重开）——永不用于触及已锁定 spec 的回答
- 仲裁方在任何 mode 下**不产实质决策**，只产出"聚合结果"或"升级信号"

## 5. locked_spec_consistency_check（C-3，最关键防线）

**漏洞**：加权多数可以"程序合法"地推翻人锁 spec——人锁被流程合法化绕过。

**处置**：任何 R6 回答 / 加权多数结果**写回前**强制 `core/scripts/consistency-check.py`：

```
R6 回答/多数结果
  → 规则层（结构化字段机械判定：forbidden/allowed_values）
      → contradict → 拒收 → spec_conflict 升级链（human 裁决）
      → consistent → 写回
      → undecidable
          → LLM 受限分类 spawn（固定 schema {input_hash, contradict, criterion_id, reason≤50}）
              → contradict → 拒收 → 升级
              → neutral / hash 不匹配 / 无 fallback → undecidable → 升级 human
              → 不自动放行（任何路径不得静默写入）
```

**纪律**：
- 规则层优先，LLM 只在规则判不了时介入，且输出 schema 固定（reason ≤50 字，无自由发挥）
- **non-structured 回答直接 undecidable**（不强行规则判定）
- 幂等键 = 输入哈希；hash 不匹配 = stale = 不可信 = undecidable

## 6. 状态映射（T3：不动上游状态机）

**原则**：协议子状态是**叠加层**，不改运行时既有任务状态机契约。

| 协议 decision_status | 运行时映射 | 说明 |
|---------------------|-----------|------|
| open | RUNNING/QUEUED（不变） | 正常推进 |
| blocked | **BLOCKED** | R6 熔断第 2 次 / R5 不可逆超时 |
| frozen | **BLOCKED** | 第 3 次熔断；人显式解冻 → open |
| paused | BLOCKED | B-10 误分类暂停重分 |
| spec_conflict | BLOCKED | C-3 拒收后升级 |

- **超时判定唯一权威 = task meta 的 timeout_at / due_at 字段**（CAP-STATE）——定时器/watchdog 缓存只做通知去重，不作为判定依据（F-2：幂等重派生）
- **写入确认铁律（F-1）**：task meta / decision_log 写入 CAP-STATE/CAP-STORE 后，**同步层确认（写入可确认，T2）之前不允许任何 merge/消费动作**
- decision_status 变更记录 append 到 task meta 历史（审计链）

## 7. 升级链总图

```
执行体遇到歧义 → R6 attention（accountable，30min/2h 超时）
  → 停摆计数 2 → blocked + 升级
  → 停摆计数 3 → frozen + 人显式解冻
验证打回 → mismatch 窗口 24h → 超时维持 spec（dissent 保留）
  → 同 criterion 3 轮 → 冻结 + 人终裁
平票 / 无多数 / 分类歧义 → 升级 accountable → owner → （single_user）human 终裁
契约 major / 不可逆超时 / 不可补偿副作用 → 直接 human
```

**终裁权永远 = human**（agent 仲裁只产升级信号）。
