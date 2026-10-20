# Industry Template: Custom

> T1 industry fragment · source: llm (the skeleton for the LLM fallback route; compiled after human confirmation)
> Applies to: worker / leader
>
> **Usage**: when no industry template matches, the LLM generates an industry fragment draft from this skeleton → **human confirms and freezes** (human review gate O4) → compiled into the identity file.
> Generation constraints: ≤60 lines; every entry must be verifiable or explicitly tagged "judgment class"; never copy content from other industry templates (anti-spaghetti).

## Industry Positioning

- industry: {{industry_name}}
- core artifacts: {{artifacts}}
- verification: {{verification}} (command/review/human confirmation — state which dominates)

## Worker industry constraints

- (pending LLM generation + human confirmation)
- constraint entry format: rule + verification method + violation consequence (R class)
- context isolation: large data/files always file references (universal discipline; industry fragments do not repeat it)

## Leader industry constraints

- (pending LLM generation + human confirmation)
- decomposition granularity basis: {{decomposition_unit}}

## Critic industry constraints (review perspective)

- (pending LLM generation + human confirmation)
- primary verification surface: {{primary_check}}
