"""Millforge token 影子校准（MF-7）——只记录/报告，绝不触碰预算判定。

样本库与偏差报告见 shadow_calibration.py；规程见 token-shadow-calibration.md
（/.en.md 孪生）。编译器管线（compiler/pipeline）不 import 本包，校准数据
永不进入行硬门 / 常驻档位 token 门。
"""
from .shadow_calibration import (  # noqa: F401
    SAMPLE_REQUIRED_FIELDS,
    TokenShadowStore,
    compute_deviation_rate,
    normalize_sample,
    render_report_text,
)
