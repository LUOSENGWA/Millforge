## 治理：投票/裁决/熔断（精简装载版 · 全文 = 协议 §09-GOVERNANCE）

**执行边界**：计票/超时/升级触发全是确定性脚本（L2）——人只提供投票/裁决输入，执行体只执行协议算出的结果。LLM 不得自行"算多数"。

**R2/R5 加权计票**（aggregate-vote）：权重 = 角色权重（owner/approver/informed），不是模型置信度；输入 = CAP-STATE attention.votes[]（状态权威，不是消息流）；**平局不重投**（直接升级）；**无票 ≠ 同意**；blocked 态禁弃权计票（defer 计入分母对通过不利）。

**R5 重开协议**：必须含 新证据 + 受影响 acceptance criteria；原锁定者 ×2 参与；反对且新证据不触 criteria → 重开失败。locker 超时（B-4）：不可逆 24h / 可逆 4h；超时 = ×2 权重失效降 1.0（**非默认同意**）；迟到 → 恢复权重重算；旧锁保留标"被 R5 覆盖"。

**R6 attention 路由**：发给 accountable（默认 project owner，可委派，委托链可查），抄送 approver（只读不阻塞）。超时分级：可逆 30min（弃权计，多数生效否则升级）；不可逆 2h（**阻塞不自动通过** + 通知 owner）。**两答冲突**：其一 accountable → 该人优先（另一人记 dissent）；同权无 accountable → 升级；**禁止执行体 LLM 总结两份人类回答择一执行**。

**停摆熔断（B-5）**：open attention 超时计数（派生值）：1=watch → 2=**blocked** + 升级 owner + 禁弃权计票 → 3=**frozen** + 人显式解冻（无自动恢复）。任何人应答 → 计数归零。

**locked_spec_consistency_check（C-3，最关键防线）**：加权多数可"程序合法"推翻人锁 spec = 漏洞。处置：R6 回答/多数结果**写回前**强制一致性检查：规则层（结构化字段机械判定）→ contradict = 拒收 + spec_conflict 升级链 ｜ undecidable → LLM 受限分类（固定 schema，hash 绑定输入）→ neutral/不可信 = 升级 human。**任何路径不得静默写入，不自动放行。**加权多数仅限 R2/R4/R5，**永不用于已锁 spec 的 R6**。

**状态映射（T3）**：协议子状态 open/blocked/frozen/paused/spec_conflict 叠加于运行时状态机（不改上游 9 态契约）；blocked/frozen/paused/spec_conflict → 运行时 BLOCKED；open → 不变。超时判定唯一权威 = task_meta 的 timeout_at/due_at（F-2）；写入确认（F-1）：CAP-STATE 同步确认前不得 merge/消费/验收。

**升级链**：歧义→R6 attention（30min/2h）→ 停摆 2 → blocked → 停摆 3 → frozen 人解冻；平票/无多数/分类歧义 → accountable → owner → human 终裁；契约 major/不可逆超时/不可补偿副作用 → 直接 human。**终裁权永远 = human。**
