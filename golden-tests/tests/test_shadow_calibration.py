"""MF-7: token 影子校准（core/calibration）测试。

验收: 样本写入/读取；偏差报告可生成（字段/样本/偏差率）；缺样本不报错；
只记录/报告——与预算判定零耦合（编译器管线不 import 本模块）。
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "shadow_calibration_mf7", ROOT / "core" / "calibration" / "shadow_calibration.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sc = _load_module()


def test_compute_deviation_rate():
    assert sc.compute_deviation_rate(100, 120) == pytest.approx(0.2)
    assert sc.compute_deviation_rate(100, 90) == pytest.approx(-0.1)
    assert sc.compute_deviation_rate(0, 5) is None  # 比值无定义


def test_record_write_read_roundtrip(tmp_path):
    store = sc.TokenShadowStore(str(tmp_path / "samples" / "token-shadow.jsonl"))
    s1 = store.record({"field": "biz-lead.soul.token_estimate", "initial": 4000, "measured": 4300,
                       "role": "biz-lead", "tokenizer": "qwen-tokenizer"})
    assert s1["deviation_rate"] == pytest.approx(0.075)
    s2 = store.record({"field": "biz-lead.soul.token_estimate", "initial": 4000, "measured": 3800})
    assert s2["deviation_rate"] == pytest.approx(-0.05)
    assert len(store.samples()) == 2
    # append-only: 两行 JSONL，字段序 field/initial/measured 在前
    lines = (tmp_path / "samples" / "token-shadow.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert list(rec)[:3] == ["field", "initial", "measured"]
    assert rec == s1


def test_record_appends_without_clobbering(tmp_path):
    store = sc.TokenShadowStore(str(tmp_path / "s.jsonl"))
    store.record({"field": "a", "initial": 100, "measured": 110})
    first_line = (tmp_path / "s.jsonl").read_text(encoding="utf-8")
    store.record({"field": "a", "initial": 100, "measured": 90})
    lines = (tmp_path / "s.jsonl").read_text(encoding="utf-8").splitlines(keepends=True)
    assert len(lines) == 2 and lines[0] == first_line  # 首行字节不变（append-only）


def test_missing_samples_never_error(tmp_path):
    store = sc.TokenShadowStore(str(tmp_path / "nope" / "s.jsonl"))
    assert store.samples() == []
    rep = store.report()
    assert rep["samples"] == 0 and rep["fields"] == {}
    assert rep["overall"]["mean_deviation_rate"] is None
    text = sc.render_report_text(rep)
    assert "samples: 0" in text


def test_report_aggregation(tmp_path):
    store = sc.TokenShadowStore(str(tmp_path / "s.jsonl"))
    store.record({"field": "a", "initial": 100, "measured": 120})   # +0.2
    store.record({"field": "a", "initial": 100, "measured": 80})    # -0.2
    store.record({"field": "b", "initial": 0, "measured": 10})      # 无定义（initial=0）
    store.record({"field": "b", "initial": 200, "measured": 220})   # +0.1
    rep = store.report()
    assert rep["samples"] == 4
    a = rep["fields"]["a"]
    assert a["n"] == 2 and a["rated"] == 2
    assert a["mean_deviation_rate"] == pytest.approx(0.0)
    assert a["max_abs_deviation_rate"] == pytest.approx(0.2)
    assert a["mean_initial"] == 100 and a["mean_measured"] == 100
    b = rep["fields"]["b"]
    assert b["n"] == 2 and b["rated"] == 1
    assert b["mean_deviation_rate"] == pytest.approx(0.1)
    assert rep["overall"]["rated"] == 3
    assert rep["overall"]["max_abs_deviation_rate"] == pytest.approx(0.2)
    text = sc.render_report_text(rep)
    assert "- a: n=2 rated=2" in text and "- b: n=2 rated=1" in text


def test_report_text_deterministic(tmp_path):
    store = sc.TokenShadowStore(str(tmp_path / "s.jsonl"))
    store.record({"field": "a", "initial": 100, "measured": 120})
    assert sc.render_report_text(store.report()) == sc.render_report_text(store.report())


def test_invalid_samples_rejected_without_write(tmp_path):
    store = sc.TokenShadowStore(str(tmp_path / "s.jsonl"))
    bad = [
        {"initial": 1, "measured": 2},                       # 缺 field
        {"field": "", "initial": 1, "measured": 2},          # 空 field
        {"field": "a", "initial": -1, "measured": 2},        # 负值
        {"field": "a", "initial": 1.5, "measured": 2},       # 非 int
        {"field": "a", "initial": True, "measured": 2},      # bool 不是合法计数
        "not-a-dict",
    ]
    for s in bad:
        with pytest.raises(ValueError):
            store.record(s)
    assert not (tmp_path / "s.jsonl").exists()  # 非法样本不落盘


def test_calibration_decoupled_from_budget_gating():
    """MF-7 边界: 校准模块零 import 编译器管线（永不触碰预算判定）。"""
    import ast

    src = (ROOT / "core" / "calibration" / "shadow_calibration.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("pipeline" in m or "compiler" in m for m in imported), imported
