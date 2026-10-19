# Domain Fragment: ML / Data Science (ml-data)

> T2 domain fragment · source: reference | applies to: worker | spawn domain: ml-data

## Context Input (spawn reads from files)

- data description (source/metric definitions/field table, file references)
- model/experiment configuration (config = contract; random seed mandatory)
- evaluation baseline (existing metric snapshot)

## Execution Constraints

- **reproducibility triad**: seed + dependency versions (pip freeze ref) + data snapshot fingerprint; missing any = not acceptable
- experiment records: every experiment = an independent artifact (config + metrics + conclusion); append, never overwrite
- metric definitions: evaluation split/metric definitions go into the spec (a definition change = a new artifact)
- large files (models/data) = CAP-STORE refs; strictly forbidden in conversation
- GPU/long training tasks = R2 (resource consumption: declare duration + budget)

## Acceptance Points (critic perspective)

- rerun reproduction (seed + data fingerprint match → metrics match; tolerance declared)
- data-leakage check (train/evaluation set boundary)
- baseline comparison: new metrics vs snapshot (no improvement = the conclusion must be honest; no dressing up)
