# Evidence Register

> Rule: empirical claims in the docs must carry an `[E#]` marker. `external-citation` must provide a verifiable source; `internal-observation` must be labelled "internal observation, not externally verifiable", and the protocol design must not depend on its specific numbers (only on the conclusion carried by a hard gate/mechanism).

| ID | Claim | Type | Source | Reproducibility |
|----|-------|------|--------|-----------------|
| **E1** | Long-context attention is U-shaped: strong at the beginning and end, weaker in the middle | external-citation | Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, arXiv:2307.03172 | public paper |
| **E2** | Hallucinated answers keep high confidence after generation; models may recognise an out-of-scope query yet still answer (a compliance failure rather than an awareness failure) | external-citation | *Beyond Calibration: Temporal LLM Confidence Assessment Across Languages and Local Settings* (arXiv:2610.27702); *CHARM: Character Hallucination for Multicultural Role Play Benchmark* (arXiv:2609.01352) | public papers |
| **E3** | An isomorphic-critic panel yields far fewer effective independent votes than its nominal count (internal observation) | internal-observation | internal multi-model review records (unpublished) | **internal observation, not externally verifiable**; the protocol relies only on the mechanism conclusion "must be heterogeneous (MC-4)", not on the numbers |
| **E4** | A worker's native session doing implementation work leads to context overflow (internal L4 tests) | internal-observation | internal L4 test records (unpublished) | **internal observation, not externally verifiable**; the protocol carries it via the X1/X7 hard gates and the 06-LIFECYCLE isolation principle |

## Usage

1. Register a new empirical claim here first, then cite `[E#]` in the text; never write numbers without a registration.
2. External citations must be openable (paper ID / official doc URL); internal observations must be explicitly labelled as not externally verifiable.
3. `core/scripts/check-evidence-refs.py` runs in `make test`: every `[E#]` reference must exist, and internal observations must carry the label.
