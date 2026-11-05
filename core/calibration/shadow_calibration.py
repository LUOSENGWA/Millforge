#!/usr/bin/env python3
"""Token 影子校准样本库与偏差报告（MF-7）。

影子校准度量编译器初值 token 估算（编译报告里的 token_estimate /
token_shadow）与真实 tokenizer 实测值之间的偏差。本模块只记录、只报告，
绝不参与预算判定：compiler/pipeline 不 import 本模块，行硬门与常驻档位
token 门的逻辑不受任何影响（规程见同目录 token-shadow-calibration.md）。

样本记录（JSONL，一行一个 compact JSON 对象，append-only）:
  field          str   被校准的估计量（如 "biz-lead.soul.token_estimate"）
  initial        int   编译器初值估算（tokens，>= 0）
  measured       int   真实 tokenizer 实测值（tokens，>= 0）
  deviation_rate float (measured - initial) / initial；initial == 0 时为 None（比值无定义）
  另可携带自由溯源键（role / team / lines / tokenizer / observed_at / note 等），
  原样存储、不解释、不影响聚合。

缺样本 = 空报告（零样本），从不报错。
"""
from __future__ import annotations

import json
import os

SAMPLE_REQUIRED_FIELDS = ("field", "initial", "measured")


def compute_deviation_rate(initial, measured):
    """(measured - initial) / initial；initial == 0 时返回 None（比值无定义）。"""
    if initial == 0:
        return None
    return (measured - initial) / initial


def normalize_sample(sample):
    """校验样本并补全 deviation_rate。非法样本 raise ValueError（不落盘）。"""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a dict")
    for k in SAMPLE_REQUIRED_FIELDS:
        if k not in sample:
            raise ValueError(f"sample missing field: {k}")
    if not isinstance(sample["field"], str) or not sample["field"]:
        raise ValueError("sample field must be a non-empty string")
    for k in ("initial", "measured"):
        v = sample[k]
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise ValueError(f"sample {k} must be an int >= 0, got {v!r}")
    out = dict(sample)
    if "deviation_rate" not in out:
        out["deviation_rate"] = compute_deviation_rate(out["initial"], out["measured"])
    return out


def _sample_rate(sample):
    """取样本偏差率：显式键优先；缺失时按 initial/measured 重算；不可用返回 None。"""
    if "deviation_rate" in sample:
        return sample["deviation_rate"]
    if "initial" in sample and "measured" in sample:
        try:
            return compute_deviation_rate(sample["initial"], sample["measured"])
        except (TypeError, ZeroDivisionError):
            return None
    return None


class TokenShadowStore:
    """显式路径上的 append-only JSONL 样本库。"""

    def __init__(self, path):
        self.path = path

    def record(self, sample):
        """校验 + 追加一条样本；返回规范化后的样本。"""
        norm = normalize_sample(sample)
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(norm, ensure_ascii=False, separators=(",", ":")) + "\n")
        return norm

    def samples(self):
        """全部样本；样本文件不存在 = 空列表（缺样本不报错）。"""
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def report(self):
        """按 field 聚合偏差报告；空库 = 零报告（缺样本不报错）。

        返回:
          {
            "samples": 总样本数,
            "fields": {field: {"n", "rated", "mean_deviation_rate",
                                "max_abs_deviation_rate", "mean_initial", "mean_measured"}},
            "overall": {"n", "rated", "mean_deviation_rate", "max_abs_deviation_rate"}
          }
        rated = 该组内偏差率有定义（initial > 0）的样本数。
        """
        groups = {}
        for s in self.samples():
            field = s.get("field")
            if not isinstance(field, str) or not field:
                continue
            g = groups.setdefault(field, {"n": 0, "rates": [], "initials": [], "measureds": []})
            g["n"] += 1
            rate = _sample_rate(s)
            if rate is not None:
                g["rates"].append(rate)
            if isinstance(s.get("initial"), int):
                g["initials"].append(s["initial"])
            if isinstance(s.get("measured"), int):
                g["measureds"].append(s["measured"])

        def _agg(rates, initials, measureds, n):
            entry = {
                "n": n,
                "rated": len(rates),
                "mean_deviation_rate": (sum(rates) / len(rates)) if rates else None,
                "max_abs_deviation_rate": (max(abs(r) for r in rates)) if rates else None,
                "mean_initial": (sum(initials) / len(initials)) if initials else None,
                "mean_measured": (sum(measureds) / len(measureds)) if measureds else None,
            }
            return entry

        all_rates = [r for g in groups.values() for r in g["rates"]]
        fields = {
            f: _agg(g["rates"], g["initials"], g["measureds"], g["n"])
            for f, g in sorted(groups.items())
        }
        total = sum(g["n"] for g in groups.values())
        return {
            "samples": total,
            "fields": fields,
            "overall": _agg(all_rates, [], [], total),
        }


def render_report_text(report):
    """偏差报告的确定性文本渲染（供人工审阅；不写任何门判定）。"""
    lines = [
        "# Token shadow calibration report",
        f"samples: {report['samples']}",
    ]
    for field, g in report["fields"].items():
        mean = g["mean_deviation_rate"]
        mx = g["max_abs_deviation_rate"]
        lines.append(
            f"- {field}: n={g['n']} rated={g['rated']} "
            f"mean_deviation={mean if mean is None else round(mean, 4)} "
            f"max_abs_deviation={mx if mx is None else round(mx, 4)}"
        )
    o = report["overall"]
    mean = o["mean_deviation_rate"]
    mx = o["max_abs_deviation_rate"]
    lines.append(
        f"overall: n={o['n']} rated={o['rated']} "
        f"mean_deviation={mean if mean is None else round(mean, 4)} "
        f"max_abs_deviation={mx if mx is None else round(mx, 4)}"
    )
    lines.append("（影子校准只记录/报告，不改变预算判定）")
    return "\n".join(lines) + "\n"
