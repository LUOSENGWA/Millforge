# 不变式：Attention 请求生命周期（CAP-ATTN）

> R6 决策/升级/澄清的载体。状态权威 = CAP-STATE（CAP-ATTN 接口是访问面，不是存储）。

## 1. 请求状态机

```
 (request)
    │  idempotency_key = hash(task_id + request_id + responder_expected + action)
    ▼
 pending ──resolve(W4 身份验证通过)──▶ resolved
    │  ▲                                 
    │  └──重复 resolve(同幂等键)──▶ resolved（返回首次结果，ALREADY_RESOLVED）
    │
    ├──timeout_at 到期（CAP-TIMER 判定）──▶ expired（分两级后果，见 §2）
    │
    └──身份验证失败──▶ rejected（IDENTITY_UNVERIFIED，不产生应答）
```

## 2. 超时后果（§03-4 超时分级）

| 类别 | 窗口 | 到期动作 |
|------|------|---------|
| 可逆（R2/R3/R4） | 30min | 弃权计（defer 计入分母）；其余形成多数 → 生效；否则升级 owner |
| 不可逆（R1/R5/R6 触外部副作用） | 2h | **任务阻塞（BLOCKED）+ 通知 owner 与仲裁方——不自动通过** |
| R5 重开窗口（B-4） | 不可逆 24h / 可逆 4h | locker ×2 权重失效降 1.0（非默认同意）；迟到恢复重算 |
| B-6 mismatch 窗口 | 24h | 维持原 spec + critic 记 dissent 且仍出评分卡 |

**停摆计数**（B-5）：派生值（attention-stall.sh 读 CAP-STATE 计算）：1=watch / 2=blocked+禁弃权计票 / 3=frozen+人显式解冻；任何人应答 → 归零（只统计最近应答后开立的 open 超时项）。

## 3. 不变式断言

1. **I-A1**（W1）同一幂等键 → 同一 request_id；同一 (request_id, responder_id, idempotency_key) → 同一应答（resolve 幂等）
2. **I-A2**（W2）resolved 记录必含 responder_id + surface_id + 时间戳，且已写入 CAP-STATE（不是只在通道上"已读"）
3. **I-A3**（W3）timeout_at 存于 CAP-STATE；判定只由 CAP-TIMER 触发 + 脚本派生；request 自身无墙钟计时
4. **I-A4**（W4）resolve 的 responder 身份经运行时 member_id 映射验证；payload 自声明角色无效；群聊 surface 不得 resolve（S4）
5. **I-A5**（W5）每个 pending request 至少一个持久展示面 surfaces[]（超时前持续存在+可回访+可身份验证）
6. **I-A6**（W6）多面关闭：首个 resolved 后其余面状态同步；关闭不改权威状态（视图行为）
7. **I-A7**（W7）kind=decision + options 存在时，resolve 的 response 必须是 option_id（自由文本选择 = 拒收）
8. **I-A8**（S5 重放）resolve 幂等键含 task_id；跨 task 的 request_id 重放 = NOT_FOUND
9. **I-A9** 两个 approver 冲突时：其一为 accountable → 该人优先（另一人记 dissent）；同权无 accountable → "无多数"升级；**禁止执行体 LLM 总结两份人类回答择一执行**（只能执行协议聚合结果）
10. **I-A10** 升级链终裁 = human；agent 仲裁只产聚合结果/升级信号
