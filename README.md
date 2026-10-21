# 千锻（Millforge）— 多 Agent 团队协议编译器

> 把「经过生产验证的 Agent 团队协作协议」编译成可直接部署的团队身份文件（SOUL + 协议片段 + 域规范）。
> 协议冻结、模板开源、编译器确定性——改需求 = 改参数，不是改文件。

**[English README](README.en.md)** ｜ 许可：Apache-2.0 ｜ 协议版本：v1.0（冻结基线）

---

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
│   └── schemas/         # team.schema.json（实例 Schema）
├── compiler/            # 编译器（Python，零 LLM，6 段流水线）
├── templates/           # 模板库（43 件，全部双语：X.md + X.en.md）
│   ├── skeleton/        #   角色骨架 ×4（coordinator/leader/worker/critic）
│   ├── fragments/       #   协议片段 ×12（NMH/NMA/双通道/熔断/契约/治理/loop/signal/handoff…）
│   ├── industry/        #   行业模板 ×6（software/embedded/data/content/business/custom）
│   ├── domain/          #   域片段 ×21（web/mcu/数据/市场/办公…）
│   └── INDEX.yaml       #   片段注册表
├── bindings/            # 运行时绑定层（agentteams（参考绑定）/ standalone-agent / coding-cli，产品做矩阵行）
├── golden-tests/        # 确定性回归（T1–T10 门 / 13 用例 / 83 脚本断言）
└── docs/                # provenance/（照搬源流原文归档）
```

## 快速开始

```bash
# 依赖：python3 + jsonschema + pyyaml（已声明）
pip install -r requirements.txt   # 或 make deps；随后 make test 跑全部门

# 1. 写团队实例（或从 golden-tests/fixtures/ 的参考实例改起：
#    example-biz-team.json = single_user，bizmarket-team.json = multi_user）
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

**CI（GitHub Actions）**：三门 = golden（13+83）/ 双语完整性 / 敏扫，push 与 PR 自动触发。

**scrub 纪律**：核心层只允许 CAP-* 能力编号 + 通用词；运行时专有 API 名（各运行时的子代理/存储/定时器机制）全部归 binding 层。开源基线不携带任何具体部署环境名、人类 MXID、内部事故编号。

## 协议层 v1.0（13 篇）

00 总则 / 01 原语 / 02 模式（single_user/multi_user）/ 03 决策类（R1-R6）/ 04 NMH（人↔Agent 审讯锁定）/ 05 NMA（同行审查）/ 06 生命周期（派发三要素/TASK_COMPLETED/故障 SOP）/ 07 跨团队 Handoff / 08 契约 Pinning / 09 治理（投票/裁决/熔断）/ 10 Loop 原语 / 11 Signal 原语 / 12 红线

核心设计立场：**验证者 ≠ 声明者**、**文件即契约**、**状态外置**（消息可丢，状态不可丢）、**注意力预算**（三层装载 + 行硬门，容量够 ≠ 注意力够）。

## 理念与二次生成

`PHILOSOPHY.md` 是千锻设计哲学全文——**复制全文 + 描述你的团队情况，喂任意 LLM，可生成你的 `team.json` 或自定义行业模板**（模板库覆盖不到时的第二兜底通道）。

## 贡献

**暂未开放**（仓库处于协议稳定期）。协议层稳定后开启贡献流程；届时：协议层变更走完整审查流程，模板层按 source 三级纪律（production/reference/llm）。

## 致谢

机制源流（含逐字继承的外部设计）见 [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)。

## 许可

Apache-2.0（见 [LICENSE](LICENSE)）。
