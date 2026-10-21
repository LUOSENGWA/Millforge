# 不变式：决策节点状态（NMH 锁定 / R5 重开 / 契约锁）

> 决策节点 = NMH 决策树节点 + 契约 pin + 已锁定 spec 字段。锁定不是永久不可变——是**重开成本显著高于首次决策**（R5）。

## 1. 节点状态机

```
 🔓 open ──human 确认/修改/否决──▶ ✅ locked
    ▲  │                            
    │  └──搁置🏳️ / 无来源🏳️──▶ 🏳️ parked
    │
    └── R5 重开成功（加权多数 + 新证据 + 原锁定者 ×2 有效）
```

| 状态 | 语义 | 出边 |
|------|------|------|
| 🔓 open | 探索/未锁定 | human 反应表（04-NMH §7）→ locked/parked |
| ✅ locked | 已锁定，带原话+时间戳 | R5 重开 → locked(v2 覆盖记录)；演化追加 → locked+eN |
| 🏳️ parked | 显式搁置 | 执行中遇到必须处理 → 升级路径（04-NMH §7）；新证据 → open |

## 2. 锁定记录（append-only，不覆盖）

- 每次锁定/重开 = 新记录 `{node_id, version, decision, human_quote, locked_by, locked_at, supersedes?}`
- **R5 覆盖**：旧锁记录保留 + 标 `superseded_by: <new_version>`（审计链；"被 R5 覆盖"标记）
- **演化**：`[D{n}-e{N}]` 追加，不改原节点文本
- 契约 pin 覆盖 = semver 新版本 + 旧版本对象保留（CAP-STORE 不可变）

## 3. 不变式断言

1. **I-D1** 锁定记录 append-only：不存在"修改锁定记录"操作（只有新版本）
2. **I-D2** locked 记录的 `human_quote` 非空且 `locked_by` ∈ roster（不替 human 锁定 = 机器可检：locked_by 必须是人类成员 ID）
3. **I-D3** R5 重开成功记录必含：新证据 ref + 受影响 acceptance criteria 列表 + 投票记录 ref（aggregate-vote 输出）
4. **I-D4** B-4 迟到降权：locker 的 vote.received_at > due_at 时 weight 记为 1.0（脚本派生，非写入）；迟到恢复 = 重算后重出计票结果
5. **I-D5** 契约 pin 的 fingerprint 与 CAP-STORE 实际值一致（合并前/验收时双验证，S2）
6. **I-D6** locked spec 字段被 R6 回答/加权多数修改前必过 locked_spec_consistency_check（C-3）；contradict → 修改不生效 + spec_conflict
7. **I-D7** type 封闭：decision_log 条目 type 必须 ∈ 类型注册表当前版本（C-1）；dimension 冲突 = 拒收
8. **I-D8** 同一节点并发 R5 请求 → 幂等键去重（hash(task_id+node_id+requester+evidence_fp)），不产生双重重开

## 4. 升级边界

- parked 超过任务完成期限 → 视为"未决策"，验收时按 blocked 处理（不得默认通过）
- 🏳️ "未取得可验证来源"节点：执行体不得填充；只可由 human/外部信息（附来源）解除
- 事实断言必须带可解析来源；无来源节点不得置 locked（I-D9）
