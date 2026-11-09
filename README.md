<p align="center">
  <img src="docs/assets/brand/millforge-logo.svg" alt="千锻 Millforge" width="320">
</p>

# 千锻（Millforge）— 多 Agent 团队协议编译器

> 把「经过生产验证的 Agent 团队协作协议」编译成可直接部署的团队身份文件（SOUL + 协议片段 + 域规范）。
> 协议冻结、模板开源、编译器确定性——改需求 = 改参数，不是改文件。

**[English README](README.en.md)** ｜ 许可：Apache-2.0 ｜ 协议版本：v1.0（冻结基线）

---

> **已集成到 AgentTeams**：[AgentTeams](https://github.com/agentscope-ai/AgentTeams) 的团队协议层就是千锻——
> AgentTeams 负责团队 / 任务 / Matrix 运行时的执行面，千锻负责把协作协议编译成可部署的身份与约束文件。
> 编译产物以 `teamharness` 模块经千锻发布仓（Millforge channels）分发，AgentTeams 控制器内置 Millforge 索引与模块安装端点；
> 协议条款、9 态、signal 契约、loop 预算一次冻结，团队差异只留在 `team.json`。

## 为什么需要千锻

多 Agent 团队（一个协调角色 + 若干 leader/worker/critic）的行为质量，不取决于模型多强，而取决于**协作协议**是否被严格执行。实践中反复出现的失效模式：

- Agent「说已完成」但没调用工具——**说了 ≠ 做了**
- 验收者就是产出者——**自己审自己**
- 长会话里上下文超限、群历史污染决策、跨团队信息在群聊里失传——**注意力稀缺是系统核心**
- 协议写在 SOUL.md 里，手改了又漂移——**文档不可复现**

千锻的答案：**协议层冻结 + 实例参数化 + 编译产出**。协议条款一次冻结（八轮审查定案），团队差异全部表达为 `team.json` 实例参数（使命/角色/域/预算/开关），编译器确定性地产出整棵部署树。同输入同输出，改需求改参数，漂移归零。

## 仓库结构

```
millforge/
├── core/
│   ├── protocol/        # 协议层 v1.0（13 篇，冻结基线）
│   ├── invariants/      # 状态机不变量（4 篇：task/decision/loop/attention）
│   ├── schemas/         # JSON Schema ×11（team/spec/task_meta/decision_log/…）
│   ├── scripts/         # 确定性脚本 ×9（计票/超时/冲突/一致性…）
│   ├── binding-contract.md    # 8 能力契约 + 绑定合法性判定
│   ├── security.md      # 威胁模型 + 机制矩阵
│   ├── cost-model-tiering.md  # 人类触达三档
│   ├── production-harden.md   # 生产化补丁
│   └── calibration/     # token 影子计数校准
├── compiler/            # 编译器（Python，零 LLM，6 段流水线）+ profiles/
├── templates/           # 模板库（43 件，全部双语：X.md + X.en.md）
│   ├── skeleton/        #   角色骨架 ×4（coordinator/leader/worker/critic）
│   ├── fragments/       #   协议片段 ×12（NMH/NMA/双通道/熔断/契约/治理/loop/signal/handoff…）
│   ├── industry/        #   行业模板 ×6（software/embedded/data/content/business/custom）
│   ├── domain/          #   域片段 ×21（web/mcu/数据/市场/办公…）
│   └── INDEX.yaml       #   片段注册表
├── bindings/            # 运行时绑定（agentteams 参考 / standalone-agent / coding-cli）
├── migration/           # 存量团队迁移（scaffold-team.py + MIGRATION-CHECKLIST）
├── golden-tests/        # 确定性回归（T1–T10 门 / 13 用例 / 83 脚本断言 + 证据/合规/tier 单元门）
├── releases/            # beta 分发镜像（模块产物 + channels.json 契约；见 releases/README.md）
├── tools/               # 本地工具（sync-beta 同步 / pack manifest 生成）
└── docs/                # 绑定指南（adding-a-binding）+ provenance/（源流原文归档）
```

**三种绑定形态**：

| 形态 | 目录 | 适用 | 能力覆盖 | 状态 |
|------|------|------|----------|------|
| 团队平台 | `bindings/agentteams/` | 多团队 / 跨团队 handoff / 多 human 隔离 | 8/8（CAP-NOTIFY 部分） | reference（非 compliant） |
| 独立 agent 运行时 | `bindings/standalone-agent/` | 单宿主、多 agent 实例、无编排层 | 8/8（CAP-NOTIFY 部分） | reference（非 compliant） |
| 编程 CLI 执行后端 | `bindings/coding-cli/` | 作为执行后端，由父执行体补全状态类能力 | 4/8（声明降级） | reference（非 compliant） |

## 快速开始

```bash
# 依赖：python3 + jsonschema + pyyaml（已声明）
pip install -r requirements.txt   # 或 make deps；随后 make test 跑全部门

# 1. 写团队实例（或从 golden-tests/fixtures/ 的参考实例改起：
#    example-biz-team.json = single_user，example-team.json = multi_user）
cat > my-team.json <<'EOF'
{ "name": "my-team", "mode": "multi_user", "lang": "zh",
  "template": "software",
  "charter": { "mission": "一句话使命", "scope": ["…"], "non_goals": ["…"] },
  "roles": [
    { "id": "my-lead", "kind": "leader", "profile": "…", "domains": [], "skills": [], "budget": 250, "spawn": false },
    { "id": "my-dev",  "kind": "worker", "profile": "…", "domains": ["web-frontend"], "skills": ["web-frontend"], "budget": 150, "spawn": true },
    { "id": "my-critic", "kind": "critic", "profile": "…", "domains": ["test-qa"], "skills": ["test-qa"], "budget": 150, "spawn": false }
  ],
  "protocol": { "nmh": true, "nma": true, "five_clauses": true, "attention": true },
  "roster": [ { "id": "human-owner", "role": "accountable", "weight": 2.0 } ]
}
EOF

# 2. 校验 + 编译
python3 compiler/millforge-compile.py validate my-team.json
python3 compiler/millforge-compile.py compile my-team.json --out out/my-team
```

产出 `out/my-team/`：每个角色一份 `.soul.md`（身份文件，受行硬门）+ `fragments/`（触发时装载的协议全文）+ `spawn-specs/`（spawn 注入的域规范）。部署方式见对应 binding 的 README。

## Deployment ledger

`deployments.jsonl`（仓库根目录）是部署台账：一行一条 JSON，记录某时刻某模块某版本部署/打包了哪个产物（含 sha256）到哪个目标、操作人是谁——让「当时部署/打包的是哪一版」随时可回答。

**为什么 append-only**：台账是溯源记录，改写历史会破坏可审计性；工具只以追加模式写入，回滚也是新增一条（`--action rollback`）而非抹除。`sha256_source` 区分两种来源：`computed`（由 `--artifact` 现场计算）/ `provided`（调用方提供 `--sha256`，`artifact` 字段取 `--label` 值）。

```bash
tools/deploy.sh record --module teamharness --version 0.3.0 --target build-host:/opt/agentteams \
    --operator alice --artifact releases/teamharness/0.3.0/teamharness.tar.gz
tools/deploy.sh record --module taskforge --version 0.1.0 --action pack --target deploy-host:/opt \
    --operator alice --sha256 <64hex> --label "pack of commit 0f11cde"
tools/deploy.sh verify --module teamharness --artifact releases/teamharness/0.3.0/teamharness.tar.gz
tools/deploy.sh list --module teamharness --limit 5
```

`verify` 取该模块**最后一条**匹配记录与当前值（artifact 现场重算哈希，或直接给 `--sha256`）比较：一致 exit 0；不一致 exit 1 并打印 `mismatch: recorded=… current=…`；无记录 exit 2。`list` 按时间顺序打印原始行（`--limit` 取最后 N 条）。零依赖（标准库）、不联网；文件入库（`.gitignore` 不忽略它）。

## 双语安装（中文 / English）

**每个模板都有全量中英文双文件**（`X.md` 中文 + `X.en.md` 英文，43/43 覆盖；协议层 13 篇 + 不变量 4 篇同样双语）。安装语言是**实例参数**，不是重新翻译：

- **中文安装**：`team.json` 写 `"lang": "zh"`（默认）
- **English install**: set `"lang": "en"` in team.json
- CLI 覆盖：`--lang en`（优先级高于 team.json）

`lang=en` 时编译器取全部模板的 `.en.md` 孪生文件，产出（SOUL + fragments + spawn-specs）整树为英文。**双语完整性是硬门**：任何模板缺 `.en.md` 孪生 → 编译失败（防止双语漂移）。

两条安装入口链接（部署后）：中文 `…/team.json 模板 + lang=zh` ｜ English `… + lang=en`。

## 质量门

| 门 | 内容 |
|------|------|
| 编译器 6 段 | Validate → Assemble → Budget（行硬门，超=fail 不截断）→ Render → SelfCheck（零残留/scrub 词表/指针完整性）→ Provenance（模板版本+片段 sha256+实例指纹） |
| golden 回归 | 同输入编译两次逐字节一致；生产专名零泄漏；触发指针全部可达 |
| **冻结基线（T9）** | 模板/片段/编译器变更 → 输出 vs 冻结基线 diff，非空 = 必须显式重冻并人审（协议回归零静默） |
| **生产溯源（T10）** | 生产基线 5 份 SOUL（占位化）+ 条款映射表：每条生产协议条款必须能映射到 v1.0 落点，缺失 = 协议内容在升级中丢失 |
| **机器契约（schemas）** | `core/schemas/*.json` 逐份校验（draft-07 合法 / `$id` 唯一 / required 已声明 / 内部 `$ref` 可解析）+ 随仓实例按 schema 校验 + **每份 schema 必须在 `core/schemas/README.md` 登记**（未登记=孤儿，门红） |
| **双语完整性** | 每个 `X.md` 必须有 `X.en.md`，反之亦然（`docs/provenance/`、`golden-tests/` 为文档化例外）——原 CI 门，现由 `make bilingual` 在本地执行 |

**门（本地，无外部 CI）**：`make test`（golden 13+83）/ 双语完整性 / 敏扫；外部 CI 已移除（11/02），提交前在本地跑同一套。

**scrub 纪律**：核心层只允许 CAP-* 能力编号 + 通用词；运行时专有 API 名（各运行时的子代理/存储/定时器机制）全部归 binding 层。开源基线不携带任何具体部署环境名、人类 MXID、内部事故编号。

## 协议层 v1.0（13 篇）

00 总则 / 01 原语 / 02 模式（single_user/multi_user）/ 03 决策类（R1-R6）/ 04 NMH（人↔Agent 审讯锁定）/ 05 NMA（同行审查）/ 06 生命周期（派发三要素/TASK_COMPLETED/故障 SOP）/ 07 跨团队 Handoff / 08 契约 Pinning / 09 治理（投票/裁决/熔断）/ 10 Loop 原语 / 11 Signal 原语 / 12 红线

核心设计立场：**验证者 ≠ 声明者**、**文件即契约**、**状态外置**（消息可丢，状态不可丢）、**注意力预算**（三层装载 + 行硬门，容量够 ≠ 注意力够）。

## 理念与二次生成

`PHILOSOPHY.md` 是千锻设计哲学全文——**复制全文 + 描述你的团队情况，喂任意 LLM，可生成你的 `team.json` 或自定义行业模板**（模板库覆盖不到时的第二兜底通道）。


## 致谢

机制源流（含逐字继承的外部设计）见 [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)。

## 许可

Apache-2.0（见 [LICENSE](LICENSE)）。
