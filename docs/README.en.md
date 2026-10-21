# Documentation Index

> This directory holds **design and usage docs** (protocol clauses live in `core/protocol/`, binding docs in `bindings/`; this directory does not duplicate them).

| Document | Content |
|---|---|
| `README.md` (this file) | documentation index and reading order |
| `adding-a-binding.md` | how to add a runtime binding (three shapes, 8 capabilities, product matrix, compliance declaration) |
| `EVIDENCE.md` | evidence register: `[E#]` claims → external citations / internal observations (not externally verifiable) |
| `provenance/grill/` | verbatim session records from the design phase (provenance only; Chinese-only, exempt from the bilingual gate) |

## Suggested reading order

1. `README.md` (repo root) → repo positioning and quickstart
2. `PHILOSOPHY.md` → why it is designed this way (can be fed verbatim to any LLM)
3. `core/protocol/00-OVERVIEW.md` → navigation across the 13 protocol clauses
4. `core/binding-contract.md` → the minimal capability set a runtime declares (8 capabilities + 55 invariants: 34 capability invariants + 21 implementation sub-items)
5. `bindings/<shape>/` → which shape your runtime should follow
6. `migration/` → how an existing team migrates in

## Conventions

- Docs in this directory are bilingual pairs (`X.md` + `X.en.md`), consistent with the CI bilingual gate.
- Protocol concepts are referenced only by CAP-* ids (e.g. CAP-STATE); concrete runtime names appear only under `bindings/`.
