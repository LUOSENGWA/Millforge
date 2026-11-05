"""Millforge compiler — 六段纯函数管线（MF-6）

Parse → Validate → Budget → Compile → Render → Verify

纯度约定（确定性 = 同输入同输出）:
  * 每段是纯函数：输入显式（doc / 模板库快照 / 显式时钟 compiled_at），
    无墙钟、无 LLM、无写盘、无全局状态变更；
  * 模板库经 TemplateLib 显式传入（磁盘状态是显式依赖，读取带缓存、顺序固定）；
  * 时间戳只进 provenance 头，且由调用方注入（compiled_at）——管线自身不取 now；
  * 任一段 raise PipelineError = 整体 fail，零产出（绝不截断）。

段与门（固定顺序，保持历史失败优先级）:
  ① Parse    JSON 解码 + 顶层结构预检            fail → exit 2
  ② Validate schema(draft-07) + 交叉一致性 + lang  fail → exit 2
  ③ Budget   行预算解析（override > role.budget > 种类默认）+ 上下文档位  fail → exit 4
  ④ Compile  skeleton + 触发指针表 + 片段部署清单（三层装载）              fail → exit 3
  ⑤ Render   占位符解析（残留只记录；零残留门在 ⑥ 按固定序执行）
  ⑥ Verify   行硬门 → 档位 token 门 → 零残留 → scrub 词表 → 指针完整性
             + provenance 头 + 指标                fail → exit 4/5/6

历史映射（2026-11-05 前的五段命名）: Validate→②, Assemble→④, Budget→③,
Render→⑤, SelfCheck/Provenance→⑥（provenance 头并入 ⑥ 产出）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re

STAGES = ["parse", "validate", "budget", "compile", "render", "verify"]

EXIT_OK = 0
EXIT_VALIDATE = 2
EXIT_COMPILE = 3   # 旧 EXIT_ASSEMBLE
EXIT_BUDGET = 4
EXIT_RENDER = 5
EXIT_VERIFY = 6    # 旧 EXIT_SELFCHECK
EXIT_USAGE = 64

BUDGETS = {"coordinator": 500, "leader": 250, "worker": 150, "critic": 150, "writer": 150}

# 上下文档位（12-REDLINES §5.2）：常驻身份文件 token 上限；声明 context_tier 时为硬门
TIER_CAPS = {"S": 8000, "M": 10000, "L": 12000}

# 生产专名 scrub 词表（核心层通用词纪律；出现 = Verify fail）
SCRUB_WORDS = [
    "spawn_subagent", "QwenPaw", "qwenpaw", "TeamHarness", "teamharness",
    "Matrix", "matrix-commander", "MinIO", "minio", "RustFS", "rustfs",
    "hiclaw", "HiClaw", "copaw", "Copaw", "SGLang",
    "QwenPaw 2", "qwenpaw_worker", "agentteams-", "hiclaw-worker",
]
# 部署环境敏感词（各部署方在本地副本追加自己的主机名/存储名/人类 MXID localpart；
# 开源基线不携带任何具体环境名）。格式示例（勿直接启用）：
# SCRUB_WORDS += ["<host-1>", "<host-2>", "<nas-name>", "<human-a>", "<human-b>"]

LANGS = ("zh", "en")

# 协议片段的常驻触发描述（第 0 层一行一个；全文在第 1 层按需装载）
TRIGGER_DESC = {
    "zh": {
        "nmh": "human 消息含方案/设计/评估/选型/对比/重构，或含隐含决策点（拿不准=触发）",
        "nma": "任务提交 / 验收请求到达 / 项目终审",
        "five-clauses": "（常驻铁律，无触发）",
        "task-lifecycle": "（常驻铁律：派发三要素/TASK_COMPLETED/故障 SOP）",
        "dual-channel": "（常驻铁律：项目 room 底线 + 原始通道送达）",
        "fuse": f"权限错误 ≥{{{{fuse_threshold}}}}（≤{{{{fuse_window_seconds}}}}s 内切 DM）",
        "loop": "收到 loop_spec / 任务进入迭代（iteration > 1）",
        "signal": "（常驻：7 封闭标记 + 三条引用资格）",
        "handoff": "跨团队任务派发 / 收到 handoff（仅 single_user 编译进协调角色）",
        "contract": "task spec 含 contract_refs / 契约变更 / R6 回答继承",
        "governance": "R5 重开 / 投票计票 / attention 升级 / 熔断判定",
        "attention-ux": "CAP-ATTN request 到达（持久展示面应答，非群聊）",
    },
    "en": {
        "nmh": "human message contains a plan/design/evaluation/selection/comparison/refactor, or a hidden decision point (when unsure = trigger)",
        "nma": "task submission / acceptance request arrives / project final review",
        "five-clauses": "(resident ironclad rules, no trigger)",
        "task-lifecycle": "(resident ironclad rules: dispatch triad / TASK_COMPLETED / failure SOP)",
        "dual-channel": "(resident ironclad rules: project-room floor + originating-channel delivery)",
        "fuse": f"permission errors ≥ {{{{fuse_threshold}}}} (switch to DM within {{{{fuse_window_seconds}}}}s)",
        "loop": "loop_spec received / task enters iteration (iteration > 1)",
        "signal": "(resident: 7 closed markers + 3 citation qualifications)",
        "handoff": "cross-team task dispatch / handoff received (compiled into coordinator only for single_user)",
        "contract": "task spec contains contract_refs / contract change / R6 answer inheritance",
        "governance": "R5 reopening / vote counting / attention escalation / fuse decision",
        "attention-ux": "CAP-ATTN request arrives (persistent display surface, not group chat)",
    },
}

# 编译器内置骨架字符串（第 0 层固定文案；模板文件之外的少量硬编码面）
UI = {
    "zh": {
        "no_industry": "（无行业差异——T0 通用）",
        "industry_line": "`fragments/industry-{ind}.md`（派发/验收时装载）",
        "industry_custom": "`fragments/industry-custom.md`（实例自带，人确认冻结）",
        "table_head": "| 触发条件 | 装载 |\n|------|------|",
        "desc_default": "（按需）",
        "domain_line": "- **{d}**: `spawn-specs/{d}.md`（派发该域 spawn 时注入 task spec）",
        "no_domain": "（无域片段——general 兜底）",
        "roster_line": "- {id} — {role}（weight {w}）",
        "member_fallback": "（按 task 动态 spawn）",
        "hdr_do_not_edit": "MILLFORGE-COMPILED — 勿手编",
        "hdr_layers": "layer1: fragments/（触发装载） layer2: spawn-specs/（spawn 注入）",
    },
    "en": {
        "no_industry": "(no industry variation — T0 generic)",
        "industry_line": "`fragments/industry-{ind}.md` (loaded at dispatch/acceptance)",
        "industry_custom": "`fragments/industry-custom.md` (instance-provided, human-frozen)",
        "table_head": "| Trigger | Load |\n|------|------|",
        "desc_default": "(on demand)",
        "domain_line": "- **{d}**: `spawn-specs/{d}.md` (injected into task spec when dispatching a spawn for this domain)",
        "no_domain": "(no domain fragments — general fallback)",
        "roster_line": "- {id} — {role} (weight {w})",
        "member_fallback": "(dynamically spawned per task)",
        "hdr_do_not_edit": "MILLFORGE-COMPILED — DO NOT HAND-EDIT",
        "hdr_layers": "layer1: fragments/ (trigger-loaded) layer2: spawn-specs/ (spawn-injected)",
    },
}

PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_.\[\]#-]+)\}\}")

DETERMINISTIC_NOTE = (
    "同 team.json 同模板库同 compiled_at → 逐字节同产出；"
    "CLI 用墙钟注入 compiled_at（golden diff 时忽略该时间戳行）"
)


class PipelineError(Exception):
    """任一段 fail = 整体 fail（携带段名、退出码、结构化错误）。"""

    def __init__(self, stage, code, error, extra=None):
        self.stage = stage
        self.code = code
        self.error = error
        self.extra = extra or {}
        super().__init__(error)

    def to_dict(self):
        out = {"ok": False, "stage": self.stage, "error": self.error}
        out.update(self.extra)
        return out


def default_root():
    """仓库根（compiler/pipeline/pipeline.py → 上三级）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def estimate_tokens(text: str) -> int:
    """Bilingual-aware token estimate: CJK chars ≈1 token, other chars ≈1/4 token."""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or ch in "，。；：！？（）【】、“”‘’")
    return cjk + (len(text) - cjk) // 4


def tier_exceeded(tier, text):
    """Return (exceeded, estimate, cap). No tier → never exceeded."""
    cap = TIER_CAPS.get(tier) if tier else None
    est = estimate_tokens(text)
    return (cap is not None and est > cap), est, cap


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_8(text: str) -> str:
    return sha256_text(text)[:8]


def load_index(root):
    import yaml
    with open(os.path.join(root, "templates", "INDEX.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_team_schema(root):
    with open(os.path.join(root, "core", "schemas", "team.schema.json"), encoding="utf-8") as f:
        return json.load(f)


class TemplateLib:
    """模板库快照（各段的显式依赖）。

    读盘带缓存、顺序固定；lang=en 时 .en.md 孪生缺失 = Compile 段 fail
    （双语完整性硬门）。同一 root+index 的磁盘状态不变 → 输出不变。
    """

    def __init__(self, root, index):
        self.root = root
        self.index = index
        self._cache = {}

    def path(self, rel, lang):
        """模板路径语言选择：lang=en → X.md 的孪生 X.en.md 必须存在。"""
        if lang == "zh":
            return os.path.join(self.root, rel)
        en_rel = rel[:-3] + ".en.md" if rel.endswith(".md") else rel + ".en.md"
        p = os.path.join(self.root, en_rel)
        if not os.path.exists(p):
            raise PipelineError(
                "compile", EXIT_COMPILE,
                f"双语完整性：{en_rel} 缺失（lang=en 需要全部模板提供 .en.md 孪生文件）",
            )
        return p

    def text(self, rel, lang):
        resolved = self.path(rel, lang)
        if resolved not in self._cache:
            with open(resolved, encoding="utf-8") as f:
                self._cache[resolved] = f.read()
        return self._cache[resolved]


# ── ① Parse ─────────────────────────────────────────────────────
def parse(text):
    """JSON 解码 + 顶层结构预检。str → doc dict。"""
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise PipelineError("parse", EXIT_VALIDATE, f"JSON 解析失败: {e}")
    if not isinstance(doc, dict):
        raise PipelineError("parse", EXIT_VALIDATE, "顶层必须是 JSON 对象（team 实例）")
    return doc


# ── ② Validate ──────────────────────────────────────────────────
def _validation_errors(doc, schema, index):
    """schema(draft-07) + 交叉一致性（roster/mode/budget/域注册）。返回错误列表（空 = 通过）。"""
    errors = []
    try:
        import jsonschema
        v = jsonschema.Draft7Validator(schema)
        for e in sorted(v.iter_errors(doc), key=lambda e: list(e.path)):
            errors.append({"rule": "schema", "path": ".".join(map(str, e.path)), "message": e.message})
        if errors:
            return errors
    except ImportError:
        errors.append({"rule": "schema", "path": "", "message": "jsonschema 未安装——pip install jsonschema（或 millforge[dev]）"})
        return errors
    roles = doc["roles"]
    ids = [r["id"] for r in roles]
    if len(ids) != len(set(ids)):
        errors.append({"rule": "xcheck", "path": "roles[].id", "message": "角色 ID 重复"})
    kinds = [r["kind"] for r in roles]
    if kinds.count("coordinator") > 1:
        errors.append({"rule": "xcheck", "path": "roles", "message": "coordinator 必须唯一"})
    if not any(r["kind"] == "leader" for r in roles):
        errors.append({"rule": "xcheck", "path": "roles", "message": "至少一个 leader"})
    if len([m for m in doc["roster"] if m["role"] == "accountable"]) > 1:
        errors.append({"rule": "xcheck", "path": "roster", "message": "accountable 必须单点（Z2）"})
    if doc["mode"] == "single_user" and not any(r["kind"] == "coordinator" for r in roles):
        errors.append({"rule": "xcheck", "path": "roles", "message": "single_user 需要 coordinator（跨团队扩展依赖）"})
    if doc["mode"] == "multi_user" and any(r["kind"] == "coordinator" for r in roles):
        errors.append({"rule": "xcheck", "path": "roles", "message": "multi_user 不得含 coordinator（相变：角色不存在）"})
    for r in roles:
        for d in r.get("domains", []):
            if d not in index.get("domains", {}):
                errors.append({"rule": "xcheck", "path": f"roles.{r['id']}.domains", "message": f"域片段 {d} 未注册（INDEX.yaml）"})
    mc = doc.get("protocol", {}).get("multi_critic", {})
    if mc.get("enabled") and mc.get("model_families", 0) < 2:
        errors.append({"rule": "xcheck", "path": "protocol.multi_critic", "message": "MC-4: 多 critic 必须 ≥2 模型族"})
    if doc.get("template") == "custom" and not doc.get("industry_fragment"):
        errors.append({"rule": "xcheck", "path": "template", "message": "template=custom 需 industry_fragment（人确认冻结）"})
    return errors


def validate(doc, *, schema, index, cli_lang=None):
    """JSON Schema + 交叉一致性 + 语言选择。返回 {"lang": ...}。

    失败优先级与历史一致：schema/xcheck 先于 lang（两者均 stage=validate, exit 2）。
    """
    errors = _validation_errors(doc, schema, index)
    if errors:
        raise PipelineError("validate", EXIT_VALIDATE, "实例校验失败", {"errors": errors})
    lang = cli_lang or doc.get("lang", "zh")
    if lang not in LANGS:
        raise PipelineError("validate", EXIT_VALIDATE, f"非法 lang: {lang}（支持 {', '.join(LANGS)}）")
    return {"lang": lang}


# ── ③ Budget ────────────────────────────────────────────────────
def budget(doc, *, overrides=None):
    """行预算解析（override > role.budget > 种类默认）+ 上下文档位。纯数据，无渲染依赖。

    超支判定（行硬门/档位 token 门）需要渲染后行数，在 ⑥ Verify 按固定序执行——
    本段只负责预算计划本身；计划不合法（档位未注册）= 本段 fail。
    """
    overrides = overrides or {}
    tier = doc.get("context_tier")
    if tier is not None and tier not in TIER_CAPS:
        raise PipelineError("budget", EXIT_BUDGET, f"非法 context_tier: {tier}（支持 {', '.join(TIER_CAPS)}）")
    entries = []
    for role in doc["roles"]:
        kind = role["kind"]
        entries.append({
            "role": role["id"], "kind": kind,
            "budget": overrides.get(kind, role.get("budget", BUDGETS[kind])),
        })
    return {"tier": tier, "tier_cap": TIER_CAPS.get(tier), "entries": entries}


# ── ④ Compile（旧 Assemble：三层装载）────────────────────────────
def _assemble_role(role, doc, lang, lib):
    """身份文件 = skeleton + 触发指针表 + 角色参数。返回 (body, deploy)。
    deploy: [{"label","src_rel"(可空),"out_rel"(可空),"sha8","content"(仅内联)}]
    第 1/2 层片段部署清单；content 仅 custom 行业内联片段非空。
    """
    index = lib.index
    kind = role["kind"]
    ui = UI[lang]
    tdesc = TRIGGER_DESC[lang]

    def tpath(rel):
        return lib.path(rel, lang)

    skel = index["skeletons"][kind]
    skel_path = tpath(skel["file"])
    if not os.path.exists(skel_path):
        raise PipelineError("compile", EXIT_COMPILE, f"skeleton 缺失: {skel['file']}")
    body = lib.text(skel["file"], lang).rstrip()
    deploy = [{"label": "skeleton", "src_rel": skel["file"], "out_rel": None,
               "sha8": sha256_8(lib.text(skel["file"], lang))}]

    # 协议触发指针表（第 0 层一行一个；第 1 层文件部署共享）
    proto = doc.get("protocol", {})
    pmap = {
        "nmh": proto.get("nmh", True),
        "nma": proto.get("nma", True),
        "five-clauses": proto.get("five_clauses", True),
        "task-lifecycle": True,
        "dual-channel": proto.get("dual_channel", True),
        "fuse": proto.get("attention", True),
        "loop": bool(proto.get("loop", {}).get("enabled")),
        "signal": True,
        "handoff": (doc["mode"] == "single_user" and kind == "coordinator"),
        "contract": True,
        "governance": kind in ("coordinator", "leader"),
        "attention-ux": kind in ("coordinator", "leader"),
    }
    rows = []
    for name, on in pmap.items():
        if not on:
            continue
        preg = index["protocol"][name]
        f = tpath(preg["file"])
        if not os.path.exists(f):
            raise PipelineError("compile", EXIT_COMPILE, f"协议片段缺失: {preg['file']}（{name}）")
        desc = tdesc.get(name, ui["desc_default"])
        rows.append(f"| {desc} | `fragments/protocol-{name}.md` |")
        deploy.append({"label": f"protocol/{name}", "src_rel": preg["file"],
                       "out_rel": f"fragments/protocol-{name}.md",
                       "sha8": sha256_8(lib.text(preg["file"], lang))})
    body = body.replace("{{protocol_triggers_block}}", ui["table_head"] + "\n" + "\n".join(rows) + "\n")

    # 行业（第 1 层部署；身份文件只留一行指针）
    industry = doc.get("template")
    ind_line = ui["no_industry"]
    if industry and industry != "custom":
        ind = index.get("industry", {}).get(industry)
        if ind and kind in ind.get("applies_to", []):
            f = tpath(ind["file"])
            if not os.path.exists(f):
                raise PipelineError("compile", EXIT_COMPILE, f"行业片段缺失: {ind['file']}")
            deploy.append({"label": f"industry/{industry}", "src_rel": ind["file"],
                           "out_rel": f"fragments/industry-{industry}.md",
                           "sha8": sha256_8(lib.text(ind["file"], lang))})
            ind_line = ui["industry_line"].format(ind=industry)
    elif industry == "custom":
        content = doc["industry_fragment"].rstrip() + "\n"
        deploy.append({"label": "industry/custom", "src_rel": None,
                       "out_rel": "fragments/industry-custom.md",
                       "sha8": sha256_8(content), "content": content})
        ind_line = ui["industry_custom"]
    body = body.replace("{{industry_block}}", ind_line)

    # 域（第 2 层：spawn-specs 部署；身份文件一行指针）
    dom_lines = []
    for d in role.get("domains", []):
        dreg = index["domains"][d]
        f = tpath(dreg["file"])
        if not os.path.exists(f):
            raise PipelineError("compile", EXIT_COMPILE, f"域片段缺失: {dreg['file']}（{d}）")
        if kind not in dreg.get("applies_to", ["worker"]):
            raise PipelineError("compile", EXIT_COMPILE, f"域片段 {d} 不适用于 {kind}")
        deploy.append({"label": f"domain/{d}", "src_rel": dreg["file"],
                       "out_rel": f"spawn-specs/{d}.md",
                       "sha8": sha256_8(lib.text(dreg["file"], lang))})
        dom_lines.append(ui["domain_line"].format(d=d))
    body = body.replace("{{domain_block}}", "\n".join(dom_lines) if dom_lines else ui["no_domain"])

    return body, deploy


def compile_stage(doc, *, lang, lib):
    """skeleton 选择 + 触发指针表生成 + 片段部署清单（缺片段 = fail）。"""
    roles = []
    for role in doc["roles"]:
        body, deploy = _assemble_role(role, doc, lang, lib)
        roles.append({"role": role, "body": body, "deploy": deploy, "ctx": build_context(doc, lang)})
    return {"roles": roles}


# ── 占位符渲染（⑤ Render 使用）───────────────────────────────────
def build_context(doc, lang="zh"):
    ui = UI[lang]
    return {
        "team": doc["name"],
        "mode": doc["mode"],
        "lang": lang,
        "protocol_version": "1.0",
        "charter.mission": doc["charter"]["mission"],
        "charter.scope": " / ".join(doc["charter"]["scope"]),
        "charter.non_goals": " / ".join(doc["charter"]["non_goals"]),
        "team_count": str(len([r for r in doc["roles"] if r["kind"] == "leader"])),
        "fuse_threshold": str(doc["protocol"].get("fuse_threshold", 2)),
        "fuse_window_seconds": str(doc["protocol"].get("fuse_window_seconds", 30)),
        "max_reflow": "2",
        "roster_block": "\n".join(
            ui["roster_line"].format(id=m['id'], role=m['role'], w=m.get('weight', 1.0))
            for m in doc["roster"]
        ),
        "coordinator_ref": next((r["id"] for r in doc["roles"] if r["kind"] == "coordinator"), "human"),
        "leader_ref": next((r["id"] for r in doc["roles"] if r["kind"] == "leader"), doc["name"] + "-lead"),
        "member_list": " / ".join(r["id"] for r in doc["roles"] if r["kind"] in ("worker", "critic")) or ui["member_fallback"],
        "human_touch_budget": (lambda h: f'{h.get("max_human_touches", "")}/{h.get("window", "")}' if h else "")(doc.get("human_touch_budget")),
    }


def _render(body, ctx, role):
    ctx2 = dict(ctx)
    ctx2["name"] = role["id"]
    ctx2["profile"] = role.get("profile", "")
    ctx2["domain"] = "/".join(role.get("domains", [])) or "general"
    ctx2["domain_name"] = ctx2["domain"]
    ctx2["skills_block"] = "\n".join(f"- {s}" for s in role.get("skills", [])) or "- （无）"
    out = []
    unresolved = []
    for line in body.splitlines():
        def sub(m):
            key = m.group(1)
            if key in ctx2 and ctx2[key] is not None:
                return str(ctx2[key])
            unresolved.append(key)
            return m.group(0)
        out.append(PLACEHOLDER_RE.sub(sub, line))
    return "\n".join(out), unresolved


def render_stage(compiled):
    """占位符解析。残留占位符只记录（unresolved），零残留门在 ⑥ Verify
    按历史固定序执行（行硬门/档位门先于零残留门）。"""
    roles = []
    for entry in compiled["roles"]:
        rendered, unresolved = _render(entry["body"], entry["ctx"], entry["role"])
        e = dict(entry)
        e.update({"rendered": rendered, "unresolved": unresolved, "lines": len(rendered.splitlines())})
        roles.append(e)
    return {"roles": roles}


# ── ⑥ Verify（门 + provenance + 指标）───────────────────────────
def _fragment_text(entry, lang, lib):
    if entry.get("content") is not None:
        return entry["content"]
    return lib.text(entry["src_rel"], lang)


def verify_stage(rendered, plan, *, doc, lang, lib, outdir, compiled_at):
    """provenance 头 + 指标 + 全部门（固定顺序，任一 fail = 整体 fail 不截断）:
    行硬门(budget,4) → 档位 token 门(budget,4) → 零残留(render,5)
    → scrub 词表(verify,6) → 触发指针完整性(verify,6)。
    """
    ui = UI[lang]
    budgets = {e["role"]: e["budget"] for e in plan["entries"]}
    fp = hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    outputs = []
    deployed = {}
    for entry in rendered["roles"]:
        role = entry["role"]
        budget_val = budgets[role["id"]]
        frag_fp = ",".join(sorted(set(f"{d['label']}@{d['sha8']}" for d in entry["deploy"])))
        header = (
            f"<!-- {ui['hdr_do_not_edit']}\n"
            f"     team: {doc['name']} | role: {role['id']}({role['kind']}) | mode: {doc['mode']} | lang: {lang}\n"
            f"     template: {doc.get('template') or 'T0-generic'} | experimental: {doc.get('experimental', False)}\n"
            f"     instance_fp: {fp} | compiled: {compiled_at} | millforge: 1.0\n"
            f"     fragments: {len(entry['deploy'])} | {frag_fp}\n"
            f"     {ui['hdr_layers']}\n"
            f"     recompile: millforge compile <team.json> -->\n"
        )
        final = header + entry["rendered"]
        # ③ Budget 指标：规则密度软门（>12/100 行 = warn，不拦）+ token 影子计数（只报不硬门）
        rule_hits = sum(final.count(t) for t in ("MUST", "SHALL", "必须", "不得"))
        rule_density = round(rule_hits * 100.0 / max(len(final.splitlines()), 1), 2)
        token_shadow = len(final) // 4
        tier_over_role, token_estimate, tier_cap = tier_exceeded(doc.get("context_tier"), final)
        tier_status = "EXCEEDED" if tier_over_role else "ok"
        out_path = os.path.join(outdir, f"{role['id']}.soul.md")
        # 片段部署（共享，去重）
        for d in entry["deploy"]:
            if d["out_rel"] is None:
                continue
            deployed.setdefault(d["out_rel"], d)
        outputs.append({
            "role": role["id"], "kind": role["kind"], "path": out_path,
            "lines": entry["lines"], "budget": budget_val,
            "budget_status": "ok" if entry["lines"] <= budget_val else "EXCEEDED",
            "rule_density": rule_density, "density_soft_warn": rule_density > 12.0,
            "token_shadow": token_shadow, "token_estimate": token_estimate,
            "context_tier": doc.get("context_tier"), "tier_status": tier_status,
            "unresolved": entry["unresolved"], "fragments": [d["label"] for d in entry["deploy"]],
            "_final": final,
        })

    # 全量判定通过才放行（超预算 = fail 且零落盘，不截断）
    over = [o for o in outputs if o["budget_status"] == "EXCEEDED"]
    if over:
        raise PipelineError("budget", EXIT_BUDGET, "行硬门超出——超支清单（绝不截断，回模板层减片段或提预算走人审）",
                            {"over_budget": [{"role": o["role"], "lines": o["lines"], "budget": o["budget"]} for o in over]})
    tier_over = [o for o in outputs if o["tier_status"] == "EXCEEDED"]
    if tier_over:
        raise PipelineError("budget", EXIT_BUDGET, "常驻 token 超出上下文档位上限（声明 context_tier 时强制；绝不截断）",
                            {"over_tier": [{"role": o["role"], "token_estimate": o["token_estimate"],
                                            "tier": o["context_tier"], "cap": TIER_CAPS[o["context_tier"]]} for o in tier_over]})
    unres = [(o["role"], k) for o in outputs for k in o["unresolved"]]
    if unres:
        raise PipelineError("render", EXIT_RENDER, "未解析占位符（实例参数缺失）", {"unresolved": unres})
    # scrub 词表（内存态判定，先于落盘）
    scrub_hits = []
    for o in outputs:
        for w in SCRUB_WORDS:
            if w in o["_final"]:
                scrub_hits.append({"file": f"{o['role']}.soul.md", "word": w})
    for rel, entry in deployed.items():
        text = _fragment_text(entry, lang, lib)
        for w in SCRUB_WORDS:
            if w in text:
                scrub_hits.append({"file": rel, "word": w})
    if scrub_hits:
        raise PipelineError("verify", EXIT_VERIFY, "scrub 词表命中（生产专名/内部 ID 泄漏进编译物）", {"hits": scrub_hits})
    # 触发指针完整性
    pointer_gaps = []
    for o in outputs:
        for m in re.finditer(r"`((?:fragments|spawn-specs)/[\w.-]+\.md)`", o["_final"]):
            if m.group(1) not in deployed:
                pointer_gaps.append({"role": o["role"], "pointer": m.group(1)})
    if pointer_gaps:
        raise PipelineError("verify", EXIT_VERIFY, "触发指针指向未部署文件", {"gaps": pointer_gaps})

    fragment_artifacts = {rel: _fragment_text(entry, lang, lib) for rel, entry in deployed.items()}
    return {
        "ok": True,
        "team": doc["name"], "mode": doc["mode"],
        "outputs": [{k: o[k] for k in ("role", "kind", "path", "lines", "budget", "budget_status",
                                        "rule_density", "density_soft_warn", "token_shadow",
                                        "token_estimate", "context_tier", "tier_status")} for o in outputs],
        "budget_gates": {"line_hard_gate": "fail", "rule_density_soft_gate": "warn(>12/100L)", "token_shadow": "report-only",
                          "token_estimate": "report", "resident_token_tier_gate": "fail(when context_tier declared)"},
        "stages_run": [],
        "deployed_fragments": sorted(deployed.keys()),
        "deterministic_note": DETERMINISTIC_NOTE,
        "artifacts": {f"{o['role']}.soul.md": o["_final"] for o in outputs},
        "fragment_artifacts": fragment_artifacts,
    }


# ── 编排 ────────────────────────────────────────────────────────
def run_pipeline(source, root, *, outdir, overrides=None, cli_lang=None, compiled_at):
    """六段编排（纯函数）。

    source: str（JSON 文本 → 走 ① Parse）或 dict（已解析 doc → ① 视为调用方完成）。
    compiled_at: 显式时钟（ISO8601 UTC），只进 provenance 头；不提供默认值——
    确定性必须由调用方保证（CLI 注入墙钟，测试注入固定值）。
    返回 verify 段结果（report + artifacts）；任一段 fail → raise PipelineError。
    """
    overrides = overrides or {}
    index = load_index(root)
    schema = load_team_schema(root)
    lib = TemplateLib(root, index)
    stages_run = []
    if isinstance(source, str):
        doc = parse(source)
        stages_run.append("parse")
    else:
        doc = source
    lang = validate(doc, schema=schema, index=index, cli_lang=cli_lang)["lang"]
    stages_run.append("validate")
    plan = budget(doc, overrides=overrides)
    stages_run.append("budget")
    compiled = compile_stage(doc, lang=lang, lib=lib)
    stages_run.append("compile")
    rendered = render_stage(compiled)
    stages_run.append("render")
    result = verify_stage(rendered, plan, doc=doc, lang=lang, lib=lib,
                          outdir=outdir, compiled_at=compiled_at)
    stages_run.append("verify")
    result["stages_run"] = stages_run
    return result
