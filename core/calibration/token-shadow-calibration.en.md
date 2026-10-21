# Token Shadow Counting Calibration Procedure v1.0

> Version: v1.0 | License: Apache-2.0
> Provenance: finalized in the second-round DeepSeek review (implementation round, 2026-10-18)
> Used together with the line hard gate; it does not replace the line hard gate

1. For each target model family, take its official tokenizer (Qwen: qwen-tokenizer; Claude: anthropic tokenizer; GPT: tiktoken cl100k/o200k).
2. For each existing SOUL compilation artifact, count separately with the line
   counter and the tokenizer, recording (lines, tokens, rules_estimated).
   rules_estimated = the number of explicit imperative/constraint sentences
   (the compiler may count markers such as "must / prohibited / shall not /
   always / never / must" with a regex in the Assemble stage, without
   calling an LLM).
3. Establish a three-column baseline:
   - line_to_token_ratio = tokens / lines (Chinese mixed text is usually 4–6;
     many code snippets 6–8; pure Chinese prose 3–4);
   - rules_per_100_tokens = rules_estimated / (tokens/100);
   - budget_headroom = 1 - tokens / the target family's soft limit.
4. If a SOUL's rules_estimated > 80 (Manager) / > 60 (Leader)
   / > 40 (Worker), even if the tokens have not exceeded the soft gate, mark
   "instruction_density_warning" in the provenance.
5. If a SOUL's tokens under the target family's tokenizer exceed 1.2× the soft
   limit, mark "token_shadow_exceeded" and recommend splitting the fragment,
   but do not block the compilation.
6. When switching models or upgrading the tokenizer, re-run steps 2–5 and
   compare the baseline drift; fragments with drift >15% are listed for
   manual review.
7. All markers are written into the provenance and are auditable together
   with the template version and the fragment hash.
