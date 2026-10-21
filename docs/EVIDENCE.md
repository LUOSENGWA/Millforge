# 证据登记（Evidence Register）

> 规则：文档中的经验性断言必须挂 `[E#]`。`external-citation` 必须给出可核验出处；`internal-observation` 必须标注「内部观察，不可外部验证」，且协议设计不得依赖其具体数字（只依赖由硬门/机制承载的结论）。

| ID | 断言 | 类型 | 出处 | 可复现性 |
|----|------|------|------|----------|
| **E1** | 长上下文注意力呈 U 形：开头与结尾高、中段衰减 | external-citation | Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, arXiv:2307.03172 | 公开论文 |
| **E2** | 幻觉答案在生成后仍维持高置信；模型可能识别越界却仍作答（主要是合规失败而非意识失败） | external-citation | *Beyond Calibration: Temporal LLM Confidence Assessment Across Languages and Local Settings*（arXiv:2610.27702）；*CHARM: Character Hallucination for Multicultural Role Play Benchmark*（arXiv:2609.01352） | 公开论文 |
| **E3** | 同构 critic 面板的有效独立票远低于名义票数（内部观察） | internal-observation | 内部多模型评审记录（未公开） | **内部观察，不可外部验证**；协议只依赖「必须异构（MC-4）」这一机制结论，不依赖具体数字 |
| **E4** | worker native session 承担实现工作会导致上下文超限（内部 L4 实测） | internal-observation | 内部 L4 测试记录（未公开） | **内部观察，不可外部验证**；协议由 X1/X7 硬门与 06-LIFECYCLE 的隔离原则承载 |

## 使用约定

1. 新增经验性断言 → 先在此登记，再在正文引用 `[E#]`；没有登记就不写数字。
2. 外部引用必须可点开核验（论文 ID / 官方文档 URL）；内部观察必须显式标注不可外部验证。
3. `core/scripts/check-evidence-refs.py` 在 `make test` 中校验：正文引用的 `[E#]` 必须存在，内部观察必须带标注。
