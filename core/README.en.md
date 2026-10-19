# core/ — Protocol Layer v1.0 (Frozen Baseline)

```
protocol/           13 protocol documents (frozen baseline; all bilingual .md + .en.md)
invariants/         4 invariants (task/decision/loop/attention state machines; bilingual)
binding-contract.md 8 capabilities (CAP-*) interface contract — the sole dependency of the protocol layer
schemas/            JSON Schemas (10)
scripts/            8 deterministic scripts (shipped with core; the deterministic part of protocol semantics)
```

## Migration Path (Strangler Fig, B-7)

**Existing hand-edited SOUL teams are not rewritten from scratch** — strangulated in three phases:

1. **Shadow**: write a `team.json` for your team (adapt one of the 2 reference instances in `golden-tests/fixtures/`: `example-biz-team.json` = single_user / `bizmarket-team.json` = multi_user), compile once, diff against the existing SOUL (audit: which clauses of the current protocol does the new protocol not cover)
2. **Parallel**: enable the newly compiled SOUL on some roles (new tasks on the new protocol; in-flight tasks on the old)
3. **Cut**: full switch; archive the old SOUL

The migration toolchain (team.json skeleton generation + human-confirmation checklist) is planned (B-7; not shipped with v1.0). `golden-tests/fixtures/` provides 2 reference team.json files + 5 production-baseline SOULs (anonymized; see `golden-tests/PRODUCTION-BASELINE.md`).

## Change Discipline

- protocol-layer change = **full review flow** (enabled with the contribution process): rationale + adversarial review record + production-traceability re-verification
- invariants must keep sync with protocol (add a new transition → add a new invariant assertion)
- scripts are protocol semantics' deterministic implementation; script change = protocol-change flow (semantic change) or compatibility fix (behavior unchanged)
- this layer is **generic-term discipline scope**: no runtime-specific API names may appear
