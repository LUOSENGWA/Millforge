# Machine contracts (JSON Schema) — mapping to the protocol text

> This directory is the **machine-checkable form** of the clauses in `core/protocol/`. The protocol
> defines semantics; the schema defines fields. They change together. The `schemas` gate in
> `make test` validates the schemas themselves, validates the in-repo instances against them, and
> **requires every schema to be listed here** (an unlisted schema is an orphan and fails the gate).

**中文**: [README.md](README.md)

## Mapping

| Schema | Protocol source | Writer · Reader | In-repo instance |
|:--|:--|:--|:--|
| `team.schema.json` | `01-PRIMITIVES.md` (CAP-ROSTER: roles and accountability) + `02-MODES.md` (single_user / multi_user shapes) | a human writes `team.json` → the compiler reads it | `golden-tests/fixtures/*.json` (2) |
| `spec.schema.json` | `04-NMH.md` (human-locked spec: goal / acceptance / out_of_scope / decision_class) | Leader writes → NMH locks → the executor reads | — |
| `task_meta.schema.json` | `09-GOVERNANCE.md` (`decision_status` protocol substates; `timeout_at` is the sole timeout authority) + `06-LIFECYCLE.md` (state-machine side effects belong to L1/L2). **The nine runtime states are not in this schema** — they live in TeamHarness | TeamHarness writes → views and acceptance read | — |
| `signal_event.schema.json` | `11-SIGNAL.md` (seven SIG-* families + `is_signal` / `ref` / `fingerprint`) | emitters write → review / acceptance / closure read | — |
| `decision_log.schema.json` | `12-REDLINES.md` **S2** (tamper-evident decision log: ref + fingerprint + append-only) | written at dispatch → dual-source check at acceptance | — |
| `scorecard.schema.json` | `05-NMA.md` (peer-review scorecard) | a critic writes → aggregation reads | — |
| `aggregation_result.schema.json` | `03-DECISIONS.md` (R1–R6 aggregation result) | the aggregator writes → closure reads | — |
| `contract.schema.json` | `08-CONTRACT.md` (the interface contract itself) | the contract owner writes → both sides pin it | — |
| `contract_snapshot.schema.json` | `08-CONTRACT.md` (pinning snapshot: `pinned_fingerprint` + `checked_at`) | the executor writes → drift detection reads | — |
| `handoff.schema.json` | `07-HANDOFF.md` (cross-team handoff: context / key_decisions / tasks_for_receiver) | the upstream team writes → the downstream team reads | — |
| `loop_spec.schema.json` | `10-LOOP.md` §1 (`iteration_budget` / `convergence_rule` / `re_plan_rule` / `termination_action` / `cross_team_reflow` = §5 cross-team reflow) | a human locks the budget → the Runner reads | — |

## How it is enforced

**Gate entry**: `python3 core/scripts/validate-schemas.py` (included in `make schemas` and `make test`).

**New instances are covered automatically**: give a JSON file a top-level `"schema": "millforge/schemas/<name>.json"`
(or `$schema`) and the gate validates it against that schema. Team definitions (with `name` / `roles` / `roster`)
need no marker — they default to `team.schema.json`.

**Discipline when the protocol changes**: change a field's semantics in `core/protocol/` → change the schema in the
same commit → run `make test`. The schema gate and the T9 frozen-baseline gate both go red, forcing an explicit re-freeze.

## Known limits

- The schemas cover **structure**, not cross-field business rules (terminal-state immutability, dual-source fingerprint
  equality, and so on) — those stay with the protocol clauses and implementation tests.
- Only the team instances exist in-repo today; the other schemas gain instances as their mechanisms land, and the gate
  picks them up at that point.
