# Millforge Runtime Binding Contract v1.0

> 版本: v1.0（协议层冻结基线） | 许可: Apache-2.0
> 千锻核心与任何运行时之间的**最小能力接口**（唯一合法引用面）。
> 核心条文只能引用 CAP-* 编号和不变式，不得引用任何具体组件。
> 范式：contract 不包含任何 provider 类型，adapter 把具体运行时语义翻译成统一 contract。
> durable collaboration 与 native execution 分离：harness 拥有持久状态，provider 只负责执行。
> 运行时专名对照见 `bindings/agentteams/reference-mappings.md`（英文孪生 `.en.md`）——非规范附录；本契约本体不含任何运行时专名。

## 设计原则

1. 核心不引用具体组件——只引用 CAP-* 编号和不变式
2. 能力是**最小集**不是最大集——运行时可以提供更多，核心只依赖以下 8 项
3. 每项能力必须声明不变式——**不变式违反 = 绑定不合法**，不是"实现差异"

---

## CAP-STATE — 任务级持久状态存储

**语义**：为每个 task 提供可原子更新的键值状态；进程重启/崩溃后幸存。

**接口契约**（语言无关）：
```
read(task_id, key) -> value | ABSENT
compare_and_set(task_id, key, expected, next) -> OK | CONFLICT | ABSENT
append(task_id, key, entry) -> new_length      # 追加语义，事件流用
list_keys(task_id) -> key[]
```

**不变式**：
- **S1 写入持久化**：返回 OK 的写入必须在崩溃后可读回（durable custody）
- **S2 原子性**：compare_and_set 并发下线性；CAS 失败不得产生部分写入
- **S3 可重放**：append 顺序在重读时一致（append-only 语义）
- **S4 不可静默丢失**：状态不得因缓存淘汰、通知丢失、临时存储清理而丢失
- **S5 记录结构（实现子项）**：状态记录为带版本的 JSON（版本字段或 append 序号），支撑 S3 重放
- **S6 写入确认（实现子项）**：写入必须有可确认点；未确认的写入视为未执行，确认前不得触发任何 merge/consume/accept（对齐 CAP-STORE T2 执行细则）
- **S7 确定性实现（实现子项）**：超时判定/计票/冲突检测等协议层判定必须由确定性脚本（L2）读 CAP-STATE 派生，不得依赖 agent“记住计算”；绑定必须声明脚本的触发机制（如外部调度器）

**千锻依赖**：R1-R6 决策记录、NMH 锁定链、B-4/B-5/B-6 计数与窗口、B-10 分类状态、spec 与 decision_class、loop 权威状态（§10）。

> 注意：对象存储（S3 语义）的定位是 **CAP-STORE 不是 CAP-STATE**。若用 S3 JSON 文件实现 CAP-STATE，用 conditional PUT + 版本号做乐观并发（失败重试）；不要拿对象级 conditional write 模拟键值 CAS（热 key 串行化）。

## CAP-STORE — 可寻址、可指纹的 artifact 存储

**语义**：存储可路径寻址的不可变内容；内容可计算密码学指纹。

**接口契约**：
```
write(path, bytes) -> {ref, fingerprint}
append(path, entry) -> new_ref        # 见 T3
read(ref) -> bytes | ABSENT
fingerprint(ref) -> fingerprint | ABSENT
exists(ref) -> bool
```

**不变式**：
- **T1 内容寻址**：同一 ref 的 fingerprint 内容不变时恒定；内容变化必须产生新 ref 或新 fingerprint
- **T2 写入可确认**：write 返回的 {ref, fingerprint} 必须在持久化完成后才返回；返回即代表可被下游安全消费
  - **T2 执行细则**：若写入路径经过同步层（工作区 ↔ 对象存储的异步同步），write 返回前必须确认同步层已持久化该对象（uploaded/committed 回执）；未确认的写入不得返回 {ref, fingerprint}，调用方不得消费未确认的 ref。同步层实现（push_loop/mirror/rsync 等）是绑定参数，"确认后才返回"是 T2 强制语义
- **T3 append-only（可链式模拟）**：`append(path, entry) -> new_ref`。实现可以是：① 同对象 JSONL 追加（运行时支持安全并发时）② 新对象链式追加（entry_ref = path+seq，append 返回链尾）③ 其他等价语义。核心只要求 read(ref) 能按 append 顺序返回所有条目，**不要求物理同对象**
- **T4 不可变性（建议级）**：已 accept 的 artifact 冻结；内容变化必须产生新版本（新 ref）
- **T5 路径契约**：artifact 路径形如 `<root>/<kind>/<id>…`（kind ∈ artifacts/decisions/nmh-docs/contracts/…），稳定可预测
- **T6 指纹算法声明**：指纹算法必须由绑定声明（如 sha256-8）；跨绑定实现可不同，同一绑定内必须一致

**千锻依赖**：decision_log 落盘、contract artifact、handoff、decision record、saga 补偿指令。
**decision_log 落盘规则**：写入 CAP-STORE 返回 {ref, fingerprint} 且满足 T2；spawn 返回只携带 ref + fingerprint；ref 必须写入 CAP-STATE。

## CAP-TIMER — 到期触发

**语义**：注册"持久化时间点到期后触发派生动作"的定时器；触发动作是确定性的（读状态、派生到期、执行预定义动作）。

**接口契约**：
```
schedule(task_id, timer_id, due_at, action_spec) -> OK | ALREADY_EXISTS
cancel(task_id, timer_id) -> OK | ABSENT
on_due(callback)   # due_at 之后调用；callback 幂等
```

**不变式**：
- **U1 单调性 + 时钟权威**：due_at 以持久化状态中的时间戳为准；触发不得早于 due_at。**timeout_at 必须由 CAP-STATE 写入，使用 CAP-STATE 所在时钟源的时间；定时器触发时比较的 now 必须来自同一时钟源**（或经校准声明的等价源）
- **U2 至多一次**：同一 timer_id 不得触发两次；迟到触发允许，callback 必须幂等
- **U3 状态权威**：定时器不得维护独立"已处理"标记作为判定依据；判定必须从 CAP-STATE 重新派生（幂等重派生）
- **U4 粒度声明**：运行时必须声明最小检查粒度（如 2 分钟）；调用方不得假设更细精度
- **U5 触发模式**：支持 one-shot 与周期（periodic）触发；周期触发用于兜底唤醒（watchdog/心跳）场景，周期为绑定声明参数
- **U6 payload 自包含**：触发 payload 必须自包含，不得假设接收会话仍记得上下文
- **U7 去重键公式**：去重键 = `hash(task_id + trigger_kind + due_at)`（U2 至多一次的具体化）

**千锻依赖**：R6 30min/2h 超时、R5 24h/4h 窗口、B-5 停摆、B-6 mismatch 窗口、loop 兜底唤醒、watchdog 三模式。

## CAP-NOTIFY — 尽力而为通知

**语义**：向人类或 Agent 投递通知；允许丢失（丢失时状态必须能从 CAP-STATE 重建）；**协议事件必须有代码级订阅面，IM 文本不是唯一观测点**。

**接口契约**：
```
send(recipients[], message, event_ref?)
  -> delivery_report {delivered[], failed[], gaps[]: {recipient, reason}}
subscribe(event_types[], callback) -> subscription_id   # 代码级事件面
unsubscribe(subscription_id) -> OK | ABSENT
```

**不变式**：
- **V1 通知不是状态**：任何决策/到期/计数不得只存在于通知中
- **V2 丢失可重建**：通知丢失后，CAP-STATE + CAP-TIMER 必须足以重建"谁需要知道什么"
- **V3 不静默丢弃**：运行时已知某 recipient 不可达（不在 allowlist/频道不存在/身份未验证）→ 必须在 delivery_report.gaps[] 返回原因；gaps 不阻塞 send，但调用方必须可观测
- **V4 通知可重复**：同一消息重复投递不产生状态副作用；接收方按 message_id 去重
- **V5 代码级订阅**：每个协议事件（attention 创建/解决/超时、决策锁定/重开、熔断状态变更、契约快照变更）必须可被程序订阅，事件携带 event_ref（指向 CAP-STATE 权威记录）；IM 文本通知是代码级事件的**派生视图**，不是唯一观测面
- **V6 回执可查**：delivery_report 必须区分 delivered（运行时确认送达通道）与 accepted（通道确认接收）；仅 accepted 不构成"人类已看到"——人类已看到的证据只能是 CAP-ATTN resolve 或通道侧显式 read receipt
- **V7 通道声明**：绑定必须声明存在哪些通道（project room / DM / originating channel）及其相对位置
- **V8 originating-channel 通知分层**：originating-channel 通知的投递是 L2 机制（delivery_report 可观测）；报告的内容生成是 L3 行为层；丢失部分可按 V2 从 CAP-STATE 重建；不得依赖“记住发送”

**千锻依赖**：attention 旁路 CC、升级通知、冻结/解冻通知、dashboard/IM 卡片（派生视图）。

## CAP-ATTN — 人类注意力请求与应答

**语义**：向指定人类发起需应答的请求；应答必须持久化；同一请求幂等；**人类应答必须可从至少一个持久展示面发起，且发起者身份可验证**。

**接口契约**：
```
request(task_id, kind, prompt, options?, route_to, timeout_at, idempotency_key)
  -> {request_id, state, surfaces[]}
resolve(request_id, response, responder_id, surface_id, idempotency_key)
  -> OK | ALREADY_RESOLVED | NOT_FOUND | IDENTITY_UNVERIFIED
status(request_id) -> {state, response?, resolved_at?, resolved_via_surface?}
list_open(task_id) -> request_id[]
```

**不变式**：
- **W1 幂等**：同一 idempotency_key 的 request 不得产生多个独立请求，重复返回同一 request_id；resolve 同样幂等——同一 (request_id, responder_id, idempotency_key) 重复 resolve 返回首次结果，不产生第二个应答
- **W2 应答持久化**：resolve 成功后，应答（含 responder_id、surface_id、时间戳）必须写入 CAP-STATE；仅在通道上"已读/已点"不算应答
- **W3 超时由 CAP-TIMER 判定**：request 不维护墙钟超时；timeout_at 写入 CAP-STATE，到期动作由 CAP-TIMER 触发
- **W4 身份可信**：resolve 必须校验 responder 身份；不得信任 payload 自声明角色；身份校验强度由通道声明（W5），低于最低要求的通道不得作为应答面
- **W5 应答面质量**：每个 request 必须至少有一个**持久展示面**支持应答——请求超时前持续存在、可被人类主动回访、应答可在该面完成身份验证。IM 私聊、dashboard 待办列表、专用审批页 = 持久展示面；**群聊 @mention 不是**（消息被淹没、无法回访）
- **W6 多面关闭**：任一持久展示面 resolve 成功 → CAP-STATE 状态 resolved；其他展示面通过轮询/事件推送感知并关闭待办；关闭是视图行为，不改变权威状态
- **W7 选项结构**：kind=decision 且提供 options 时，options 必须是 `[{option_id, label, consequence_summary?}]` 结构化列表；应答必须回传 option_id，**不得回传自由文本作为选择**
- **W8 应答者限人类**：request 只能由人类 resolve（roster role = human）；Agent 不得自行 resolve
- **W9 幂等键公式**：request 幂等键 = `hash(task_id + decision_node_id + decision_hash)`；resolve 幂等键含 responder_id + action，即 `hash(task_id + request_id + responder_id + action)`
- **W10 应答写入确认**：人类应答在写入确认后才进入 CAP-STATE；后续动作（重分类/重新投票）不得先于确认启动

**千锻依赖**：R6 attention、NMH 锁定确认、B-6 升级、B-10 重分类裁决、C-3 undecidable 升级。

## CAP-SPAWN — fresh 上下文执行体

**语义**：创建全新上下文的执行体，接收结构化任务，返回结构化结果。

**接口契约**：
```
spawn(task_spec, context_refs[], return_schema, timeout?)
  -> {spawn_id, result, decision_log_ref}
```

**不变式**：
- **X1 上下文隔离（硬）**：spawn 不得继承父执行体的对话历史；只能通过 context_refs 获取显式输入。**不满足 X1 的运行时不得作为合法绑定**
- **X2 结构化返回**：result 必须符合 return_schema；decision_log_ref 必须指向 CAP-STORE 中可指纹 artifact
- **X3 独立性**：spawn 不得修改父执行体状态；所有状态变更通过返回值传递
- **X4 有界性（硬）**：spawn 必须有界——要么在声明时限内返回结构化结果 `{artifact_refs[], decision_log_ref, self_reported_status}`，要么时限内报告有界失败 `{bounded_failure: true, reason, partial_refs?}`；不得无限挂起；时限由调用方声明，运行时必须强制执行。**不满足 X4 的运行时不得作为合法绑定**（Loop 可执行前提：否则 iteration_budget 与 CAP-TIMER 失去意义）
- **X5 输入 = spec 引用**：spawn 输入是任务 spec 引用（task_spec / context_refs），不是消息内联长文
- **X6 context_refs 内容限制**：context_refs 只可包含标记信号 + CAP-STORE artifact refs（§11-SIGNAL）
- **X7 worker 上下文隔离（协议规则）**：worker 的 native session 只做调度 + 验收，所有实现工作必须经 CAP-SPAWN 子执行体（读文件取上下文、写文件出结果、用完销毁）；这是协议规则而非绑定特性，但绑定必须提供实现手段

**千锻依赖**：worker 上下文隔离、critic 独立执行、C-3 受限分类、merge 语义确认、loop 迭代/re-plan spawn。

## CAP-EXEC — 确定性程序执行

**语义**：运行确定性程序（脚本/二进制），传参，捕获结构化输出和退出码。程序可以是随核心分发的，也可以是运行时提供的等价物。

**接口契约**：
```
exec(program_ref, args[], stdin?, timeout?) -> {exit_code, stdout, stderr}
```

**不变式**：
- **Y1 确定性**：同一 program_ref + 同一输入 → 同一输出（不依赖 LLM 采样）
- **Y2 退出码语义**：退出码按调用方定义的语义解释；0 不自动等于"成功"
- **Y3 无隐式状态**：不得读写调用方隐式状态；所有输入显式传入，所有输出显式返回
- **Y4 执行环境声明**：绑定必须声明执行环境（哪台机器 / 容器 / 沙箱）
- **Y5 输出持久化**：执行输出必须持久化（写入 CAP-STORE 或内联返回），证据可审计
- **Y6 超时界**：命令执行必须有界，不得无限挂起
- **Y7 NMA 隔离边界**：执行者不得运行在被审方 workspace 内（跨容器/跨 workspace 不可达）；🔵 项限于外部可验证面（API / 对象存储 / 公开文档）

**8 脚本归属裁决**：`core/scripts/` 的 8+1 脚本**随核心协议分发**，不要求运行时重写——
1. CAP-EXEC 语义是"运行确定性程序"，不是"运行时提供这些特定程序"；运行时重写 = 语义漂移风险
2. 脚本是**协议语义的确定性实现**（B-1 schema 校验/B-2 冲突检测/B-3 semver 分类…），应与协议条文一起版本化
3. 无对象存储/群聊的运行时（claude-code 适配）脚本照常运行——输入输出路径由调用方按 CAP-STORE ref 解析（本地文件系统是合法 CAP-STORE 实现）
4. 例外：watchdog 的**调度部分**（调度器配置、状态文件路径）= 绑定实现；逻辑部分（到期判定/动作派生）= 核心 CAP-TIMER 参考实现

**千锻依赖**：B-1/B-2/B-3/B-5/B-6/B-10/C-3 全部确定性脚本 + timer-derive。

## CAP-ROSTER — 角色名册

**语义**：查询人类成员的身份、角色和权重。

**接口契约**：
```
members(team_id) -> [{member_id, role, weight, accountable_for[]}]
accountable(task_id) -> member_id | ABSENT
delegation_chain(task_id) -> [{delegator, delegatee, scope, granted_at}] | []
```

**不变式**：
- **Z1 权重来自角色**：权重是角色属性，不是模型置信度；核心不得用 LLM 推断权重
- **Z2 accountable 单点**：每个 task 最多一个 accountable stakeholder；ABSENT 必须显式返回，不得用"默认 owner"静默填充
- **Z3 委托链可查询**：accountable 委托应答时委托链必须可查询；核心判定"谁有权锁定"时使用委托链

**千锻依赖**：R1 owner 裁决、R2 加权多数、NMH 锁定、attention 路由（§03-4）、loop driver 身份确定（§10-3）。

---

## 安全红线（跨能力，S1-S5）

见 `protocol/12-REDLINES.md` §1（artifact 数据红线 / decision_log 防伪 / contract 双确认 / 群聊非应答面 / 重放防护）——五条均为 CAP 接口的执行细则，违反 = 绑定不合法。

## 绑定合法性判定

一个运行时构成**合法绑定**当且仅当：
1. 8 能力全部实现且不变式全部满足（X1/X4 为硬门）
2. 提供 CAP-EXEC 可运行 `core/scripts/`（或声明等价实现并过 golden test）
3. 声明：运行时版本矩阵 / 原语映射表（§01 每个原语 → 具体机制）/ 模式矩阵 / 定时器粒度 / 持久展示面清单
4. 通过 `golden-tests/` 回归（L5）

## 能力清单（速览）

| 能力 | 一句话语义 |
|---|---|
| CAP-STATE | 任务级持久状态读写（可重放、可原子更新） |
| CAP-STORE | 可寻址、可指纹的 artifact 存储（append 可选） |
| CAP-TIMER | 到期触发（粒度声明、幂等回调） |
| CAP-NOTIFY | 尽力而为通知通道（可丢失，状态可重建） |
| CAP-ATTN | 人类注意力请求与应答（持久展示面、幂等） |
| CAP-SPAWN | fresh 上下文执行体（结构化返回） |
| CAP-EXEC | 确定性程序执行（退出码语义） |
| CAP-ROSTER | 角色名册（人类成员 + 角色 + 权重） |

## 绑定声明格式

绑定 README **必须**包含：

```
## 能力声明（CAP-*）
| CAP | 已实现 | 覆盖等级（完整/部分/声明降级） | 具体机制（运行时 API） | 限制 |
|-----|--------|------------------|------------------------|------|
| CAP-STATE | ✅ | 完整 | … | … |
| CAP-STORE | ✅ | 完整 | … | … |
| CAP-TIMER | ✅ | 完整 | … | … |
| CAP-NOTIFY | ✅ | 完整 | … | … |
| CAP-ATTN | ⚠️ | 部分 | … | 持久展示面仅 DM |
| CAP-SPAWN | ✅ | 完整 | … | X4 时限 = 3600s（版本 vX） |
| CAP-EXEC | ✅ | 完整 | … | 隔离边界 = … |
| CAP-ROSTER | ✅ | 完整 | … | … |

## 非法能力降级
（逐能力声明本绑定"不支持 / 必须降级"的协议条文）

## 已知问题
（运行时已知缺陷及其对协议执行的影响）
```

> 覆盖等级描述**能力实现程度**（完整 / 部分 / 声明降级），与 §12-REDLINES §4 的**可靠性分层 L1/L2/L3**（平台内置 / 确定性脚本 / 行为层）是两套不同语义——不得用 L1/L2/L3 表示能力等级。

**未声明 = 非法绑定**（不能承载任何千锻协议流程）。

## 协议 ↔ 绑定依赖总表

| 协议件 | 依赖能力 | 缺失后果 |
|---|---|---|
| §03 决策聚合 | CAP-STATE + CAP-TIMER（脚本） | 聚合机制不可用（降级为"仅人类单点"） |
| §04 NMH | CAP-STORE（NMH 文档） | 决策树不落盘（文件即契约不可用 → 非法） |
| §05 NMA | CAP-EXEC + CAP-STORE | checklist 不可执行（降级为"仅同行审查"） |
| §06 生命周期 | CAP-NOTIFY + CAP-STATE | 双通道汇报 / 完成信号不可用 |
| §07 handoff | CAP-STORE（跨团队空间） | 跨团队不可用（仅 single_user；multi_user 绑定可省略） |
| §08 契约 | CAP-STORE（指纹）+ CAP-STATE（快照） | 契约 pinning 不可用（降级为"不 pin、每次重验"） |
| §09 治理 | CAP-STATE + CAP-TIMER + CAP-ATTN | 停摆熔断 / 超时不可用 |
| §10 loop | CAP-SPAWN(X4) + CAP-STATE + CAP-TIMER | loop 不可用（降级为"不迭代"） |
| §11 signal | CAP-STATE（event_type）+ CAP-STORE（指纹） | 信号不可用（降级为"验收引用全历史"——弱化模式，必须声明） |
