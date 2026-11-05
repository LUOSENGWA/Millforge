"""MF-6: 六段纯函数管线测试（每段 + 端到端）+ CLI 冒烟 + golden 基线。

覆盖 make test 的 run-compile-tests.sh T1–T9 门（容器内 bash/python3 被
worker-proxy 拦截，本文件以 pytest 承载等价断言；宿主侧 make test 仍是终门）:
  T1 确定性（同输入两次编译逐字节一致，除 provenance 时间戳行）
  T2 行硬门 / T3 零残留占位符 / T4 provenance 头 / T5 触发指针完整性
  T6 Validate fail 路径（exit 2）/ T7 Budget fail 路径（exit 4，零产出）
  T8 scrub 词表（zh+en）/ T9 冻结基线 diff
另有: 每段单元（parse/validate/budget/compile/render/verify）、失败退出码映射、
全注册域片段可用性（子域模板矩阵）、en 孪生装载。
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = ROOT / "golden-tests" / "fixtures"
BASE = ROOT / "golden-tests" / "baseline"
CLI = ROOT / "compiler" / "millforge-compile.py"
COMPILED_AT = "2026-11-05T00:00:00Z"

sys.path.insert(0, str(ROOT / "compiler"))
import pipeline.pipeline as pl  # noqa: E402


def _load_cli():
    spec = importlib.util.spec_from_file_location("millforge_compile_mf6", CLI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mf = _load_cli()


def _doc(name):
    return json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))


def _run(doc, outdir, **kw):
    text = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    return pl.run_pipeline(text, pl.default_root(), outdir=outdir, compiled_at=COMPILED_AT, **kw)


def _strip_timestamp(text):
    return [ln for ln in text.splitlines(True) if "compiled:" not in ln]


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── ① Parse ─────────────────────────────────────────────────────
def test_parse_valid():
    doc = pl.parse('{"name": "x-y", "roles": []}')
    assert doc == {"name": "x-y", "roles": []}


def test_parse_invalid_json():
    with pytest.raises(pl.PipelineError) as ei:
        pl.parse("{not json")
    assert ei.value.stage == "parse" and ei.value.code == pl.EXIT_VALIDATE


def test_parse_top_level_not_object():
    with pytest.raises(pl.PipelineError) as ei:
        pl.parse("[1, 2, 3]")
    assert ei.value.stage == "parse" and ei.value.code == pl.EXIT_VALIDATE


# ── ② Validate ──────────────────────────────────────────────────
def _lib(root=None):
    root = root or pl.default_root()
    return pl.TemplateLib(root, pl.load_index(root))


def test_validate_ok():
    out = pl.validate(_doc("example-biz-team"), schema=pl.load_team_schema(pl.default_root()),
                      index=pl.load_index(pl.default_root()))
    assert out == {"lang": "zh"}


def test_validate_rejects_duplicate_role_id():
    doc = _doc("example-biz-team")
    doc["roles"][1]["id"] = doc["roles"][0]["id"]
    with pytest.raises(pl.PipelineError) as ei:
        pl.validate(doc, schema=pl.load_team_schema(pl.default_root()), index=pl.load_index(pl.default_root()))
    assert ei.value.stage == "validate" and ei.value.code == pl.EXIT_VALIDATE
    assert any(e["rule"] == "xcheck" for e in ei.value.extra["errors"])


def test_validate_rejects_bad_lang():
    doc = _doc("example-biz-team")
    doc["lang"] = "fr"
    with pytest.raises(pl.PipelineError) as ei:
        pl.validate(doc, schema=pl.load_team_schema(pl.default_root()), index=pl.load_index(pl.default_root()))
    assert ei.value.stage == "validate" and ei.value.code == pl.EXIT_VALIDATE


# ── ③ Budget ────────────────────────────────────────────────────
def test_budget_plan_resolution():
    doc = _doc("example-biz-team")
    plan = pl.budget(doc)
    by_role = {e["role"]: e["budget"] for e in plan["entries"]}
    assert by_role["biz-coordinator"] == 500  # role.budget
    assert by_role["biz-lead"] == 250
    assert plan["tier"] is None and plan["tier_cap"] is None
    plan2 = pl.budget(doc, overrides={"worker": 120})
    by_role2 = {e["role"]: e["budget"] for e in plan2["entries"]}
    assert by_role2["biz-analyst"] == 120  # override 生效


def test_budget_rejects_unknown_tier():
    doc = _doc("example-biz-team")
    doc["context_tier"] = "XL"
    with pytest.raises(pl.PipelineError) as ei:
        pl.budget(doc)
    assert ei.value.stage == "budget" and ei.value.code == pl.EXIT_BUDGET


# ── ④ Compile（旧 Assemble）─────────────────────────────────────
def test_compile_stage_builds_identity():
    doc = _doc("example-biz-team")
    lib = _lib()
    out = pl.compile_stage(doc, lang="zh", lib=lib)
    assert len(out["roles"]) == 5
    lead = next(r for r in out["roles"] if r["role"]["id"] == "biz-lead")
    assert "{{protocol_triggers_block}}" not in lead["body"]
    assert "{{industry_block}}" not in lead["body"]
    labels = {d["label"] for d in lead["deploy"]}
    assert "skeleton" in labels and "industry/business" in labels
    assert "protocol/nmh" in labels and "protocol/governance" in labels
    analyst = next(r for r in out["roles"] if r["role"]["id"] == "biz-analyst")
    assert {"domain/data-analysis", "domain/data-visualization"} <= {d["label"] for d in analyst["deploy"]}


def test_compile_stage_fails_on_missing_fragment():
    doc = _doc("example-biz-team")
    index = pl.load_index(pl.default_root())
    index["domains"]["data-analysis"]["file"] = "templates/domain/does-not-exist.md"
    lib = pl.TemplateLib(pl.default_root(), index)
    with pytest.raises(pl.PipelineError) as ei:
        pl.compile_stage(doc, lang="zh", lib=lib)
    assert ei.value.stage == "compile" and ei.value.code == pl.EXIT_COMPILE


# ── ⑤ Render ────────────────────────────────────────────────────
def test_render_stage_resolves_and_records_unresolved():
    doc = _doc("example-biz-team")
    compiled = pl.compile_stage(doc, lang="zh", lib=_lib())
    entry = compiled["roles"][0]
    out = pl.render_stage({"roles": [{"role": entry["role"], "ctx": entry["ctx"],
                                      "body": "{{team}} says hi\n{{no_such_key}}"}]})
    r = out["roles"][0]
    assert r["rendered"] == "example-biz-team says hi\n{{no_such_key}}"
    assert r["unresolved"] == ["no_such_key"]


# ── ⑥ Verify（门 + provenance + 指标）───────────────────────────
def _rendered_fixture(tmp_path):
    doc = _doc("example-biz-team")
    lib = _lib()
    rendered = pl.render_stage(pl.compile_stage(doc, lang="zh", lib=lib))
    plan = pl.budget(doc)
    return doc, lib, rendered, plan, str(tmp_path)


def test_verify_line_gate(tmp_path):
    doc = _doc("example-biz-team")
    with pytest.raises(pl.PipelineError) as ei:
        _run(doc, str(tmp_path), overrides={"worker": 1})
    assert ei.value.stage == "budget" and ei.value.code == pl.EXIT_BUDGET
    over = {o["role"] for o in ei.value.extra["over_budget"]}
    assert over == {"biz-analyst", "biz-writer"}


def test_verify_tier_gate(tmp_path, monkeypatch):
    doc = _doc("example-biz-team")
    doc["context_tier"] = "S"
    monkeypatch.setitem(pl.TIER_CAPS, "S", 100)
    with pytest.raises(pl.PipelineError) as ei:
        _run(doc, str(tmp_path))
    assert ei.value.stage == "budget" and ei.value.code == pl.EXIT_BUDGET
    assert "over_tier" in ei.value.extra


def test_verify_unresolved_gate(tmp_path):
    doc, lib, rendered, plan, outdir = _rendered_fixture(tmp_path)
    rendered["roles"][0]["unresolved"] = ["zz_missing_key"]
    with pytest.raises(pl.PipelineError) as ei:
        pl.verify_stage(rendered, plan, doc=doc, lang="zh", lib=lib, outdir=outdir, compiled_at=COMPILED_AT)
    assert ei.value.stage == "render" and ei.value.code == pl.EXIT_RENDER


def test_verify_scrub_gate(tmp_path):
    doc, lib, rendered, plan, outdir = _rendered_fixture(tmp_path)
    rendered["roles"][0]["rendered"] += "\n部署在 MinIO 上。\n"
    with pytest.raises(pl.PipelineError) as ei:
        pl.verify_stage(rendered, plan, doc=doc, lang="zh", lib=lib, outdir=outdir, compiled_at=COMPILED_AT)
    assert ei.value.stage == "verify" and ei.value.code == pl.EXIT_VERIFY
    assert any(h["word"] == "MinIO" for h in ei.value.extra["hits"])


def test_verify_pointer_gate(tmp_path):
    doc, lib, rendered, plan, outdir = _rendered_fixture(tmp_path)
    rendered["roles"][0]["rendered"] += "\n参见 `fragments/protocol-nope.md`。\n"
    with pytest.raises(pl.PipelineError) as ei:
        pl.verify_stage(rendered, plan, doc=doc, lang="zh", lib=lib, outdir=outdir, compiled_at=COMPILED_AT)
    assert ei.value.stage == "verify" and ei.value.code == pl.EXIT_VERIFY
    assert ei.value.extra["gaps"][0]["pointer"] == "fragments/protocol-nope.md"


def test_exit_code_mapping():
    # 对外退出码兼容: Validate=2 / Compile(=旧 Assemble)=3 / Budget=4 / Render=5 / Verify(=旧 SelfCheck)=6 / usage=64
    assert pl.EXIT_VALIDATE == 2
    assert pl.EXIT_COMPILE == 3 and mf.EXIT_ASSEMBLE == 3
    assert pl.EXIT_BUDGET == 4
    assert pl.EXIT_RENDER == 5
    assert pl.EXIT_VERIFY == 6 and mf.EXIT_SELFCHECK == 6
    assert pl.EXIT_USAGE == 64
    assert pl.STAGES == ["parse", "validate", "budget", "compile", "render", "verify"]


# ── 端到端 ──────────────────────────────────────────────────────
def test_e2e_fixture_success(tmp_path):
    doc = _doc("example-biz-team")
    r = _run(doc, str(tmp_path))
    assert r["ok"] is True
    assert len(r["outputs"]) == 5
    assert r["stages_run"] == pl.STAGES
    budgets = {o["role"]: (o["lines"], o["budget"]) for o in r["outputs"]}
    for lines, b in budgets.values():
        assert lines <= b
    assert all(o["budget_status"] == "ok" for o in r["outputs"])
    assert "spawn-specs/data-analysis.md" in r["fragment_artifacts"]
    assert "fragments/protocol-nmh.md" in r["fragment_artifacts"]
    art = r["artifacts"]["biz-lead.soul.md"]
    assert art.startswith("<!-- MILLFORGE-COMPILED")
    assert "instance_fp:" in art and "recompile:" in art


def test_e2e_deterministic_same_input(tmp_path):
    doc = _doc("example-biz-team")
    text = json.dumps(doc, ensure_ascii=False, sort_keys=True)
    r1 = pl.run_pipeline(text, pl.default_root(), outdir=str(tmp_path), compiled_at=COMPILED_AT)
    r2 = pl.run_pipeline(text, pl.default_root(), outdir=str(tmp_path), compiled_at=COMPILED_AT)
    h1 = {k: _sha(v) for k, v in r1["artifacts"].items()}
    h2 = {k: _sha(v) for k, v in r2["artifacts"].items()}
    f1 = {k: _sha(v) for k, v in r1["fragment_artifacts"].items()}
    f2 = {k: _sha(v) for k, v in r2["fragment_artifacts"].items()}
    assert h1 == h2 and f1 == f2  # 同输入两次输出 sha256 一致
    r3 = pl.run_pipeline(text, pl.default_root(), outdir=str(tmp_path), compiled_at="2026-11-06T00:00:00Z")
    for name in r1["artifacts"]:
        assert _strip_timestamp(r1["artifacts"][name]) == _strip_timestamp(r3["artifacts"][name])


def _domain_doc(domain):
    return {
        "name": f"t-{domain}",
        "mode": "multi_user",
        "template": None,
        "subdomain": domain,
        "experimental": True,
        "charter": {"mission": "domain coverage check", "scope": ["s"], "non_goals": ["g"]},
        "roles": [
            {"id": "lead", "kind": "leader", "profile": "coverage leader", "domains": [],
             "skills": [], "budget": 250, "spawn": False, "model": None},
            {"id": f"w-{domain}", "kind": "worker", "profile": "coverage worker", "domains": [domain],
             "skills": [], "budget": 150, "spawn": True, "model": None},
        ],
        "protocol": {"nmh": True, "nma": True, "five_clauses": True, "attention": True},
        "roster": [{"id": "h1", "role": "accountable", "weight": 1.0}],
    }


def test_all_registered_worker_domains_usable(tmp_path):
    """子域模板矩阵可用: INDEX 注册的每个 worker 适用域片段都能编译部署。"""
    index = pl.load_index(pl.default_root())
    domains = [d for d, reg in index["domains"].items() if "worker" in reg.get("applies_to", [])]
    assert len(domains) >= 15
    for d in domains:
        r = _run(_domain_doc(d), str(tmp_path))
        assert r["ok"] is True, f"domain {d} failed"
        assert f"spawn-specs/{d}.md" in r["fragment_artifacts"], f"domain fragment not deployed: {d}"


def test_en_lang_uses_twin_templates(tmp_path):
    doc = _doc("bizmarket-team")
    r = _run(doc, str(tmp_path), cli_lang="en")
    assert r["ok"] is True
    twin = (ROOT / "templates" / "fragments" / "nmh.en.md").read_text(encoding="utf-8")
    assert r["fragment_artifacts"]["fragments/protocol-nmh.md"].rstrip() == twin.rstrip()
    zh = (ROOT / "templates" / "fragments" / "nmh.md").read_text(encoding="utf-8")
    assert r["fragment_artifacts"]["fragments/protocol-nmh.md"] != zh.rstrip()
    assert "DO NOT HAND-EDIT" in r["artifacts"]["bizmarket-lead.soul.md"]


# ── CLI 冒烟（subprocess 承载；等价 run-compile-tests.sh T1–T9）──
def _cli(*args, cwd=None):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True,
                          cwd=str(cwd or ROOT))


def test_cli_validate_ok():
    r = _cli("validate", str(FIX / "example-biz-team.json"))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["ok"] is True


def test_cli_validate_fail_exit2():
    bad = _doc("example-biz-team")
    bad["roster"].append({"id": "x", "role": "accountable", "weight": 1.0})
    p = pathlib.Path(__file__).with_name("zz-bad-instance.json")
    p.write_text(json.dumps(bad), encoding="utf-8")
    try:
        r = _cli("validate", str(p))
        assert r.returncode == 2
        assert json.loads(r.stdout)["stage"] == "validate"
    finally:
        if p.exists():
            p.unlink()


def _compile_fixture(name, outdir):
    r = _cli("compile", str(FIX / f"{name}.json"), "--out", str(outdir))
    return r


def test_cli_deterministic_line_budget_provenance_pointers_baseline(tmp_path):
    """T1 确定性 + T2 行硬门 + T3 零残留 + T4 provenance + T5 指针 + T9 基线。"""
    a, b, c = tmp_path / "a", tmp_path / "b", tmp_path / "c"
    for name, out in (("example-biz-team", a), ("example-biz-team", b), ("bizmarket-team", c)):
        r = _compile_fixture(name, out)
        assert r.returncode == 0, f"{name}: rc={r.returncode} err={r.stderr} out={r.stdout}"

    # T1 同输入两次 → 除 provenance 时间戳行外逐字节一致
    fa = sorted(a.glob("*.soul.md"))
    for x, y in zip(fa, sorted(b.glob("*.soul.md"))):
        assert _strip_timestamp(x.read_text(encoding="utf-8")) == _strip_timestamp(y.read_text(encoding="utf-8"))

    # T2 行硬门（文件行数 ≤ 角色预算）
    for name, out in (("example-biz-team", a), ("bizmarket-team", c)):
        doc = _doc(name)
        budget_of = {role["id"]: role["budget"] for role in doc["roles"]}
        for f in out.glob("*.soul.md"):
            role_id = f.name[: -len(".soul.md")]
            n = len(f.read_text(encoding="utf-8").splitlines())
            assert n <= budget_of[role_id], f"{name}/{role_id}: {n} > {budget_of[role_id]}"

    # T3 零残留占位符
    for out in (a, c):
        for f in out.glob("*.soul.md"):
            assert "{{" not in f.read_text(encoding="utf-8"), f"placeholder left in {f.name}"

    # T4 provenance 头
    for f in (a / "biz-analyst.soul.md",):
        t = f.read_text(encoding="utf-8")
        for token in ("MILLFORGE-COMPILED", "instance_fp:", "fragments:", "recompile:"):
            assert token in t

    # T5 触发指针完整性
    for out in (a, c):
        for f in out.glob("*.soul.md"):
            for m in re.finditer(r"`((?:fragments|spawn-specs)/[A-Za-z0-9._-]+\.md)`", f.read_text(encoding="utf-8")):
                assert (out / m.group(1)).is_file(), f"pointer gap {m.group(1)} in {f.name}"

    # T9 冻结基线 diff（忽略 compiled: 时间戳行）
    for name, out in (("example-biz-team", a), ("bizmarket-team", c)):
        base_dir = BASE / name
        for f in sorted(base_dir.glob("*.soul.md")):
            src = out / f.name
            assert src.is_file(), f"missing compiled: {name}/{f.name}"
            assert _strip_timestamp(f.read_text(encoding="utf-8")) == _strip_timestamp(src.read_text(encoding="utf-8")), \
                f"baseline drift: {name}/{f.name}"


def test_cli_over_budget_exit4_zero_output(tmp_path):
    """T7: 超预算 = exit 4 且零落盘（不截断）。"""
    out = tmp_path / "over"
    r = _cli("compile", str(FIX / "example-biz-team.json"), "--out", str(out), "--budget-override", "worker=1")
    assert r.returncode == 4, f"rc={r.returncode} err={r.stderr} out={r.stdout}"
    if out.is_dir():
        assert not list(out.glob("*.soul.md"))


def test_cli_lang_en_scrub(tmp_path):
    """T8: zh + en 编译产物无生产专名（完整 SCRUB_WORDS 词表）。"""
    a, aen = tmp_path / "a-zh", tmp_path / "a-en"
    assert _cli("compile", str(FIX / "bizmarket-team.json"), "--out", str(a)).returncode == 0
    r = _cli("compile", str(FIX / "bizmarket-team.json"), "--out", str(aen), "--lang", "en")
    assert r.returncode == 0, r.stderr
    for out in (a, aen):
        for f in out.glob("*.soul.md"):
            t = f.read_text(encoding="utf-8")
            hits = [w for w in mf.SCRUB_WORDS if w in t]
            assert not hits, f"scrub hits in {f.name}: {hits}"


def test_cli_usage_errors(tmp_path):
    r = _cli("frobnicate", str(FIX / "example-biz-team.json"))
    assert r.returncode == 64
    r = _cli("compile")
    assert r.returncode == 64
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    r = _cli("validate", str(bad))
    assert r.returncode == 2
    assert json.loads(r.stdout)["stage"] == "parse"


def test_cli_list_fragments():
    r = _cli("list-fragments")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    index = pl.load_index(pl.default_root())
    assert data["domains"] == list(index["domains"])
    assert data["skeletons"] == list(index["skeletons"])


def test_cli_compile_module_api(tmp_path):
    """compile_team 模块 API（test_tier_gate 同接口）: 成功返回 0 并落盘。"""
    doc = _doc("example-biz-team")
    rc = mf.compile_team(dict(doc), str(tmp_path))
    assert rc == 0
    assert (tmp_path / "biz-lead.soul.md").is_file()
    assert (tmp_path / "spawn-specs" / "data-analysis.md").is_file()
