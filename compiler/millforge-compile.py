#!/usr/bin/env python3
"""millforge compiler — 6 段流水线（确定性，同输入同输出）

用法:
  millforge compile <team.json> [--out <dir>] [--budget-override <role>=<lines>] [--lang zh|en]
  millforge validate <team.json>          # 只跑 Validate 段
  millforge list-fragments                # 列出 INDEX.yaml 注册的全部片段

双语: team.json `lang: "zh"|"en"`（默认 zh），CLI `--lang` 覆盖。
lang=en → 全部模板取 .en.md 孪生文件（缺失 = Assemble fail，双语完整性硬门）；
产出（.soul.md + fragments/ + spawn-specs/）整树为英文。

6 段（任一段 fail = 整体 fail，绝不截断产出）:
  ① Validate  — JSON Schema 校验（team.schema.json）+ 交叉一致性（roster/mode/budget）  exit 2
  ② Assemble  — skeleton 选择 + 触发指针表生成 + 片段部署清单（缺片段 = fail）
  ③ Budget    — 行硬门（coordinator≤500/leader≤250/worker≤150/critic≤150）；超 = fail + 超支清单
  ④ Render    — 占位符解析（未解析残留 = fail）
  ⑤ SelfCheck — 门: 零残留占位符 / 行数 / scrub 词表（生产专名）/ 触发指针完整性
  ⑥ Provenance— 头注释（模板版本 + 片段 sha256 + 实例参数指纹 + 编译时间）

三层装载架构（§12-REDLINES，U 形注意力 + 行天花板）:
  第 0 层 常驻（身份文件，受行硬门）: skeleton（身份+铁律+核心循环）+ 协议触发指针表（一行一个）+ 角色参数
  第 1 层 按需（运行时触发装载）: 协议片段全文 fragments/protocol-*.md + 行业片段 fragments/industry-*.md
  第 2 层 参考/注入: 域片段 spawn-specs/*.md（派发 spawn 时注入 task spec，不占身份文件）
  触发机制 = 绑定层实现（能力触发/read_file）；核心只要求触发描述常驻 + 片段文件部署。
  域片段 ≠ 身份文件内容（header 已声明"派发时注入 spawn 的 task spec"）——不编译进 .soul.md。

确定性: 无 LLM；片段装载顺序固定（INDEX 声明序）；时间戳只进 provenance 头（不进正文）。
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # millforge/
CORE = os.path.join(ROOT, "core")
TEMPLATES = os.path.join(ROOT, "templates")
SCHEMAS = os.path.join(CORE, "schemas")
INDEX = os.path.join(TEMPLATES, "INDEX.yaml")

EXIT_OK = 0
EXIT_VALIDATE = 2
EXIT_ASSEMBLE = 3
EXIT_BUDGET = 4
EXIT_RENDER = 5
EXIT_SELFCHECK = 6
EXIT_USAGE = 64

BUDGETS = {"coordinator": 500, "leader": 250, "worker": 150, "critic": 150}
# 生产专名 scrub 词表（核心层通用词纪律；出现 = SelfCheck fail）
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


def lang_of(doc, cli_lang=None):
    """语言选择：CLI --lang > team.json lang > 默认 zh。en = 全链路 .en.md 模板。"""
    lang = cli_lang or doc.get("lang", "zh")
    if lang not in LANGS:
        fail("validate", EXIT_VALIDATE, f"非法 lang: {lang}（支持 {', '.join(LANGS)}）")
    return lang


def tpath_lang(rel, lang):
    """模板路径语言选择：lang=en → X.md 的孪生 X.en.md 必须存在（双语完整性硬门）。"""
    if lang == "zh":
        return os.path.join(ROOT, rel)
    en_rel = rel[:-3] + ".en.md" if rel.endswith(".md") else rel + ".en.md"
    p = os.path.join(ROOT, en_rel)
    if not os.path.exists(p):
        fail("assemble", EXIT_ASSEMBLE,
             f"双语完整性：{en_rel} 缺失（lang=en 需要全部模板提供 .en.md 孪生文件）")
    return p


def fail(stage, code, msg, extra=None):
    out = {"ok": False, "stage": stage, "error": msg}
    if extra:
        out.update(extra)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(code)


def load_index():
    import yaml
    with open(INDEX, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256_8(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:8]


# ── ① Validate ─────────────────────────────────────────────────
def validate_team(doc):
    errors = []
    try:
        import jsonschema
        with open(os.path.join(SCHEMAS, "team.schema.json"), encoding="utf-8") as f:
            schema = json.load(f)
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
    idx = load_index()
    for r in roles:
        for d in r.get("domains", []):
            if d not in idx.get("domains", {}):
                errors.append({"rule": "xcheck", "path": f"roles.{r['id']}.domains", "message": f"域片段 {d} 未注册（INDEX.yaml）"})
    mc = doc.get("protocol", {}).get("multi_critic", {})
    if mc.get("enabled") and mc.get("model_families", 0) < 2:
        errors.append({"rule": "xcheck", "path": "protocol.multi_critic", "message": "MC-4: 多 critic 必须 ≥2 模型族"})
    if doc.get("template") == "custom" and not doc.get("industry_fragment"):
        errors.append({"rule": "xcheck", "path": "template", "message": "template=custom 需 industry_fragment（人确认冻结）"})
    return errors


# ── ② Assemble（三层装载）─────────────────────────────────────
def assemble_role(role, doc, lang="zh"):
    """身份文件 = skeleton + 触发指针表 + 角色参数。返回 (body, deploy_refs)
    deploy_refs: [(label, src_path, out_relpath, sha8)] 第 1/2 层片段部署清单"""
    idx = load_index()
    kind = role["kind"]
    ui = UI[lang]
    tdesc = TRIGGER_DESC[lang]

    def tpath(rel):
        return tpath_lang(rel, lang)

    skel = idx["skeletons"][kind]
    skel_path = tpath(skel["file"])
    if not os.path.exists(skel_path):
        fail("assemble", EXIT_ASSEMBLE, f"skeleton 缺失: {skel['file']}")
    with open(skel_path, encoding="utf-8") as f:
        body = f.read().rstrip()
    deploy = [("skeleton", skel_path, None, sha256_8(skel_path))]

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
        preg = idx["protocol"][name]
        f = tpath(preg["file"])
        if not os.path.exists(f):
            fail("assemble", EXIT_ASSEMBLE, f"协议片段缺失: {preg['file']}（{name}）")
        desc = tdesc.get(name, ui["desc_default"])
        rows.append(f"| {desc} | `fragments/protocol-{name}.md` |")
        deploy.append((f"protocol/{name}", f, f"fragments/protocol-{name}.md", sha256_8(f)))
    body = body.replace("{{protocol_triggers_block}}", ui["table_head"] + "\n" + "\n".join(rows) + "\n")

    # 行业（第 1 层部署；身份文件只留一行指针）
    industry = doc.get("template")
    ind_line = ui["no_industry"]
    if industry and industry != "custom":
        ind = idx.get("industry", {}).get(industry)
        if ind and kind in ind.get("applies_to", []):
            f = tpath(ind["file"])
            if not os.path.exists(f):
                fail("assemble", EXIT_ASSEMBLE, f"行业片段缺失: {ind['file']}")
            deploy.append((f"industry/{industry}", f, f"fragments/industry-{industry}.md", sha256_8(f)))
            ind_line = ui["industry_line"].format(ind=industry)
    elif industry == "custom":
        cf = os.path.join(os.path.dirname(os.path.abspath(doc_path_global)), "industry-custom.frag.md")
        with open(cf, "w", encoding="utf-8") as fh:
            fh.write(doc["industry_fragment"].rstrip() + "\n")
        deploy.append(("industry/custom", cf, "fragments/industry-custom.md", sha256_8(cf)))
        ind_line = ui["industry_custom"]
    body = body.replace("{{industry_block}}", ind_line)

    # 域（第 2 层：spawn-specs 部署；身份文件一行指针）
    dom_lines = []
    for d in role.get("domains", []):
        dreg = idx["domains"][d]
        f = tpath(dreg["file"])
        if not os.path.exists(f):
            fail("assemble", EXIT_ASSEMBLE, f"域片段缺失: {dreg['file']}（{d}）")
        if kind not in dreg.get("applies_to", ["worker"]):
            fail("assemble", EXIT_ASSEMBLE, f"域片段 {d} 不适用于 {kind}")
        deploy.append((f"domain/{d}", f, f"spawn-specs/{d}.md", sha256_8(f)))
        dom_lines.append(ui["domain_line"].format(d=d))
    body = body.replace("{{domain_block}}", "\n".join(dom_lines) if dom_lines else ui["no_domain"])

    return body, deploy


# ── 占位符渲染 ─────────────────────────────────────────────────
PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z0-9_.\[\]#-]+)\}\}")


def build_context(doc, lang="zh"):
    ui = UI[lang]
    ctx = {
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
    }
    return ctx


def render(body, ctx, role):
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


# ── 主流程 ─────────────────────────────────────────────────────
doc_path_global = None  # custom 行业片段落盘锚点（main 里设）


def compile_team(doc, outdir, overrides=None, lang=None):
    overrides = overrides or {}
    lang = lang_of(doc, lang)
    ui = UI[lang]
    outputs = []
    deployed = {}
    for role in doc["roles"]:
        body, deploy = assemble_role(role, doc, lang)
        ctx = build_context(doc, lang)
        rendered, unresolved = render(body, ctx, role)
        lines = len(rendered.splitlines())
        budget = overrides.get(role["kind"], role.get("budget", BUDGETS[role["kind"]]))
        fp = hashlib.sha256(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        frag_fp = ",".join(sorted(set(f"{lbl}@{sha}" for lbl, _, _, sha in deploy)))
        header = (
            f"<!-- {ui['hdr_do_not_edit']}\n"
            f"     team: {doc['name']} | role: {role['id']}({role['kind']}) | mode: {doc['mode']} | lang: {lang}\n"
            f"     template: {doc.get('template') or 'T0-generic'} | experimental: {doc.get('experimental', False)}\n"
            f"     instance_fp: {fp} | compiled: {now} | millforge: 1.0\n"
            f"     fragments: {len(deploy)} | {frag_fp}\n"
            f"     {ui['hdr_layers']}\n"
            f"     recompile: millforge compile <team.json> -->\n"
        )
        final = header + rendered
        out_path = os.path.join(outdir, f"{role['id']}.soul.md")
        # 片段部署（共享，去重）
        for lbl, src, rel, sha in deploy:
            if rel is None:
                continue
            target = os.path.join(outdir, rel)
            deployed.setdefault(rel, (src, sha, target))
        outputs.append({
            "role": role["id"], "kind": role["kind"], "path": out_path,
            "lines": len(final.splitlines()), "budget": budget,
            "budget_status": "ok" if lines <= budget else "EXCEEDED",
            "unresolved": unresolved, "fragments": [d[0] for d in deploy],
            "_final": final,
        })

    # 全量判定通过后才写盘（超预算 = fail 且零落盘，不截断）
    over = [o for o in outputs if o["budget_status"] == "EXCEEDED"]
    if over:
        fail("budget", EXIT_BUDGET, "行硬门超出——超支清单（绝不截断，回模板层减片段或提预算走人审）",
             {"over_budget": [{"role": o["role"], "lines": o["lines"], "budget": o["budget"]} for o in over]})
    unres = [(o["role"], k) for o in outputs for k in o["unresolved"]]
    if unres:
        fail("render", EXIT_RENDER, "未解析占位符（实例参数缺失）", {"unresolved": unres})
    # SelfCheck 门③ scrub（内存态判定，先于落盘）
    scrub_hits = []
    for o in outputs:
        for w in SCRUB_WORDS:
            if w in o["_final"]:
                scrub_hits.append({"file": f"{o['role']}.soul.md", "word": w})
    for rel, (src, sha, target) in deployed.items():
        with open(src, encoding="utf-8") as f:
            text = f.read()
        for w in SCRUB_WORDS:
            if w in text:
                scrub_hits.append({"file": rel, "word": w})
    if scrub_hits:
        fail("selfcheck", EXIT_SELFCHECK, "scrub 词表命中（生产专名/内部 ID 泄漏进编译物）", {"hits": scrub_hits})
    # SelfCheck 门④ 触发指针完整性
    pointer_gaps = []
    for o in outputs:
        for m in re.finditer(r"`((?:fragments|spawn-specs)/[\w.-]+\.md)`", o["_final"]):
            if m.group(1) not in deployed:
                pointer_gaps.append({"role": o["role"], "pointer": m.group(1)})
    if pointer_gaps:
        fail("selfcheck", EXIT_SELFCHECK, "触发指针指向未部署文件", {"gaps": pointer_gaps})
    # 全部判定通过 → 落盘
    if not doc.get("dry_run"):
        os.makedirs(outdir, exist_ok=True)
        for o in outputs:
            with open(o["path"], "w", encoding="utf-8") as f:
                f.write(o["_final"])
        for rel, (src, sha, target) in deployed.items():
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if not os.path.exists(target):
                with open(src, encoding="utf-8") as fsrc, open(target, "w", encoding="utf-8") as fdst:
                    fdst.write(fsrc.read())

    result = {
        "ok": True,
        "team": doc["name"], "mode": doc["mode"],
        "outputs": [{k: o[k] for k in ("role", "kind", "path", "lines", "budget", "budget_status")} for o in outputs],
        "deployed_fragments": sorted(deployed.keys()),
        "deterministic_note": "同 team.json 同模板库 → 同产出（provenance 头时间戳除外，golden diff 时忽略）",
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return EXIT_OK


def main():
    global doc_path_global
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(EXIT_USAGE if not args else EXIT_OK)
    cmd = args[0]
    if cmd == "list-fragments":
        idx = load_index()
        print(json.dumps({"skeletons": list(idx["skeletons"]), "industry": list(idx["industry"]),
                          "domains": list(idx["domains"]), "protocol": list(idx["protocol"]),
                          "teams": list(idx["teams"])}, ensure_ascii=False, indent=1))
        sys.exit(EXIT_OK)
    if cmd not in ("compile", "validate"):
        fail("usage", EXIT_USAGE, f"unknown command: {cmd}（compile|validate|list-fragments）")
    if len(args) < 2:
        fail("usage", EXIT_USAGE, "missing <team.json>")
    doc_path_global = args[1]
    with open(args[1], encoding="utf-8") as f:
        doc = json.load(f)
    errs = validate_team(doc)
    if errs:
        fail("validate", EXIT_VALIDATE, "实例校验失败", {"errors": errs})
    if cmd == "validate":
        print(json.dumps({"ok": True, "team": doc["name"], "validations": "schema+xcheck passed"}, ensure_ascii=False))
        sys.exit(EXIT_OK)
    outdir = None
    overrides = {}
    cli_lang = None
    i = 2
    while i < len(args):
        if args[i] == "--out":
            outdir = args[i + 1]; i += 2
        elif args[i] == "--budget-override":
            k, v = args[i + 1].split("=", 1); overrides[k] = int(v); i += 2
        elif args[i] == "--lang":
            cli_lang = args[i + 1]; i += 2
        else:
            i += 1
    doc["dry_run"] = outdir is None
    outdir = outdir or os.path.join(os.getcwd(), "out", doc["name"])
    sys.exit(compile_team(doc, outdir, overrides, cli_lang))


if __name__ == "__main__":
    main()
