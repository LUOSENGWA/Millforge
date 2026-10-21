# 不变式：Task 状态机（T3 叠加层）

> 核心只约束**协议子状态**（decision_status）与运行时状态的映射；不重写运行时任务状态机。
> 9 态运行时状态（上游任务契约：planned / prepared / assigned / in_progress / submitted / completed / revision / blocked / cancelled）保持不动。

## 1. decision_status 子状态迁移

```
        blocked ──人解冻/条件消除──▶ open
         ▲                            │
         │（停摆 2 / R5 不可逆超时/     │（停摆 3）
         │  C-3 拒收/paused 重分失败）  ▼
        frozen ◀────────────────  open
```

| 迁移 | 触发 | 确定性判定（脚本） |
|------|------|-------------------|
| open → blocked | R6 停摆计数 = 2（attention-stall exit 40）；R5 不可逆窗口超时（aggregate-vote exit 81）；C-3 contradict 拒收；B-10 重分类暂停 | `attention-stall.sh` / `aggregate-vote.sh` / `consistency-check.py` |
| blocked → open | 条件消除（人应答/裁决/重分完成）；**frozen 除外** | 人动作记录（CAP-STATE append） |
| blocked → frozen | 停摆计数 = 3（attention-stall exit 41） | `attention-stall.sh` |
| frozen → open | **人显式解冻**（无自动恢复路径） | 人动作记录 |
| open → spec_conflict | C-3 拒收后进入 spec_conflict 升级链 | `consistency-check.py` exit 70 |
| spec_conflict → open/blocked | human 裁决：修订 spec（→open）/ 维持原 spec 升级（→blocked） | 人动作记录 |
| open → paused | B-10 mismatch 重分类窗口（R4→R1 2h） | `saga-compensate.py` 事件记录 |
| paused → open | 重分类完成 + saga 补偿成功 | `saga-compensate.py` |
| paused → blocked | 重分类发现不可补偿副作用（exit 60） | `saga-compensate.py` |

## 2. 运行时映射（单向，不反写）

| decision_status | 运行时状态 | 说明 |
|-----------------|-----------|------|
| open | 不变（planned/assigned/in_progress…） | 正常推进 |
| blocked | **BLOCKED** | 可恢复 |
| frozen | **BLOCKED** | 标记 frozen 子状态（元数据） |
| paused | BLOCKED | 重分类窗口 |
| spec_conflict | BLOCKED | 升级链中 |

**禁止**：协议层直接写运行时状态（只能写 BLOCKED 这一个收敛点）；运行时状态变化不自动改变 decision_status（由脚本派生后写回）。

> 注：上游任务契约把 `blocked` 列为**终态**（无出边）。协议 `decision_status` 的 blocked→open 是**协议子状态**恢复；若运行时按终态实现，恢复必须以**新任务/重新派发**落地，不修改运行时状态机（本协议不改写上游）。

## 3. 不变式断言（golden test 可检）

1. **I-T1** decision_status ∈ {open, blocked, frozen, paused, spec_conflict}，无其他值
2. **I-T2** frozen 只有"人显式解冻"一条出边（自动化脚本不得产生 frozen→open 迁移）
3. **I-T3** 每次迁移必 append decision_status_history（from/to/at/reason 四字段齐全）
4. **I-T4** timeout 判定只读 task_meta.timeout_at / attention.due_at（F-2：定时器/watchdog 缓存不参与判定）
5. **I-T5** 写 CAP-STATE 未获同步确认前，不得触发 merge/消费/验收（F-1）
6. **I-T6** loop 内 task 的 decision_status 不影响 loop 权威状态（loop_state 独立，§10-3）
7. **I-T7** 同一 task 的 decision_status_history 时间戳单调（同时钟源，CAP-TIMER U1）
