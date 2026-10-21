# Token 影子计数校准规程 v1.0

> 版本: v1.0 | 许可: Apache-2.0
> 配合行硬门使用，不替代行硬门

1. 对每个目标模型族，取其官方 tokenizer（Qwen: qwen-tokenizer；
   Claude: anthropic tokenizer；GPT: tiktoken cl100k/o200k）。
2. 对现有每个 SOUL 编译产物，分别用行计数器和 tokenizer 计数，
   记录 (lines, tokens, rules_estimated)。
   rules_estimated = 显式祈使句/约束句数量（可由编译器在 Assemble
   段用正则统计 "必须/禁止/不得/always/never/must" 等标记，
   不调 LLM）。
3. 建立三列基线：
   - line_to_token_ratio = tokens / lines（中文混排通常 4–6；
     代码片段多则 6–8；纯中文说明则 3–4）；
   - rules_per_100_tokens = rules_estimated / (tokens/100)；
   - budget_headroom = 1 - tokens / 目标族软上限。
4. 若某 SOUL 的 rules_estimated > 80（Manager）/ > 60（Leader）
   / > 40（Worker），即使 token 未超软门，也在 provenance 中标记
   "instruction_density_warning"。
5. 若某 SOUL 在目标族 tokenizer 下 tokens 超过软上限的 1.2 倍，
   标记 "token_shadow_exceeded"，建议拆分片段，但不阻断编译。
6. 模型切换或 tokenizer 升级时，重跑步骤 2–5，比较基线漂移；
   漂移 >15% 的片段列入人工复审。
7. 所有标记写入 provenance，与模板版本、片段哈希一起可审计。
