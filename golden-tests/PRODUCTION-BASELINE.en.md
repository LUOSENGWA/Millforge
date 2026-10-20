# Production Baseline Mapping (Golden-Gate Audit Anchor)

> v1.0 | 2026-10-19 | Closes open question #1

## 1. Baseline Definition & Gate Semantics

**Production baseline** = the 5 SOULs in `fixtures/production-baseline/` (the bizmarket team, multi_user first-compile baseline; hand-edited v2.0 + subsequent production hot-patches; anonymized copies — placeholder mapping in §5).

**Gate semantics (important)**: the diff target of the golden gate is the **frozen compiled baseline** (the `baseline/` directory — deterministic compiler output for `fixtures/bizmarket-team.json` + `fixtures/example-biz-team.json`), **not** the production baseline source. Why:

- the production SOULs are from the **previous protocol generation** (hand-edited in the SATCOM v1.0 / NMProtocol v3.0 era + production-incident hot-patches), while the compiler implements **protocol layer v1.0** (frozen after eight review rounds).
- the two generations share the same DNA (triad / dual-channel / declaration-verification binding / permission-wall fuse / context isolation), but terminology and structure have been upgraded (R1-R6 decision classes, X4 bounded deadlines, context_refs, decision_log, scorecard).
- forcing byte-level reproduction would = regressing the compiler to the old protocol, contradicting the frozen v1.0 rulings.

**Therefore the gate = a double gate**:
1. **compile determinism gate** (CI automatic): template/fragment/compiler change → compiled output vs `baseline/` diff; non-empty = must re-freeze explicitly with review (zero silent protocol regression).
2. **production traceability gate** (human audit, this file): every production protocol clause must map to a v1.0 landing point (§2-§4); a missing mapping = protocol content lost in upgrade = gate red. Every protocol-layer change must re-run this mapping.

## 2. Worker Common Clauses Mapping (shared by all 5 roles)

| # | Production clause (old) | v1.0 landing point | Status |
|:--:|------|------|:--:|
| W1 | Rule 1: duty boundary + refusal must escalate | `skeleton/worker.md` iron rules + `fragments/protocol-contract.md` (scope/out_of_scope contract) | ✅ absorbed (upgraded to structured contract) |
| W2 | Group-chat @mention rules (no @ = talking to yourself) | `fragments/protocol-attention-ux.md` + binding layer (Matrix mention formats in bindings/agentteams/README) | ✅ absorbed (binding specialization kept in the binding layer) |
| W3 | v2.40 context isolation (native = scheduling+review; implementation = spawn) | `skeleton/worker.md` iron rule #1 (compiled output keeps the "v2.40 ruling" citation) | ✅ absorbed |
| W4 | Spawn availability probe (no spawn-class tool in tool list → native execution) | `fragments/protocol-task-lifecycle.md` spawn discipline ("never call a tool that doesn't exist, never claim spawned" semantics) | ✅ absorbed |
| W5 | Core loop (triad → decompose → spawn → review → integrate) | `skeleton/worker.md` six-step workflow (triad + structured acceptance + decision_class) | ✅ absorbed (upgraded: structured acceptance + decision class) |
| W6 | Spawn context injection 5 elements (data path / goal / prohibition / delivery contract / data contract) | `spawn-specs/*.md` + `fragments/protocol-task-lifecycle.md` (context_refs file references + X4 deadline + return_schema) | ✅ absorbed (upgraded: long context goes to files, not messages) |
| W7 | Review spawn outputs (self-check items; ≤3 re-spawns → escalate) | `skeleton/worker.md` acceptance (structured checks → evidence into scorecard; verifier ≠ declarer; ≤3 escalates to leader) | ✅ absorbed (upgraded: scorecard evidence chain) |
| W8 | Deliverable delivery rules (dual-channel delivery + object-storage push + TASK_COMPLETED) | `fragments/protocol-task-lifecycle.md` (TASK_COMPLETED triad + mandatory 3-5 key conclusions) + `protocol-dual-channel.md` | ✅ absorbed (upgraded: mandatory conclusions = handoff raw material) |
| W9 | Spawn discipline (versioned 3600s hard deadline + timeout-kill signature + continuation re-dispatch) | X4 bounded deadline (generalized, not tied to a runtime version) + `protocol-task-lifecycle.md` failure SOP | ⚠️ upgraded (version pin → generic contract; runtime specialization moves to binding) |
| W10 | Team handoff section (writer↔analyst, writer↔designer dataflow) | instance params (team.json roles.profile/charter declare the pipeline) + `fragments/industry-business.md` | 📋 instance-specific (not protocol; templates never hardcode member pairs) |
| W11 | Role card (duties / content types / asset types / review dimensions) | instance params (team.json profile + domains) + `skeleton` domain section | 📋 instance-specific |

## 3. Leader-Specific Clauses Mapping

| # | Production clause (old) | v1.0 landing point | Status |
|:--:|------|------|:--:|
| L1 | Entry dual-channel (IM direct + channel bot equivalent) | instance params (roster + binding channel config) | 📋 instance-specific |
| L2 | Iron rule: never implement yourself | `skeleton/leader.md` iron rules | ✅ absorbed |
| L3 | Iron rule: report missing capacity (never absorb it yourself, never report under another's name) | `skeleton/leader.md` iron rules + `protocol-governance.md` | ✅ absorbed |
| L4 | Iron rule: verify the executor before reporting | `protocol-governance.md` (verifier ≠ declarer; report verification) | ✅ absorbed |
| L5 | Iron rule: declaration-verification binding (said ≠ done) | `skeleton/leader.md` iron rule #3 (kept in compiled output) | ✅ absorbed |
| L6 | Iron rule: permission-wall fuse (≥2 → switch to DM ≤30s) | `protocol-fuse.md` (fuse_threshold/fuse_window instance params) | ✅ absorbed |
| L7 | Iron rule: report before confirming (the session may end after the confirmation) | `protocol-dual-channel.md` + `protocol-task-lifecycle.md` (closure order) | ✅ absorbed |
| L8 | NMH interrogation locking (explore/lock dual mode + 7-question self-check + nmh-docs inline writing) | `fragments/protocol-nmh.md` (old = skill-loaded, new = fragment-pointer-loaded — mechanism upgrade, same content origin) | ✅ absorbed (loading mechanism skill→fragment) |
| L9 | Project room creation (project registration + two-part invite + joined_members verification) | binding layer (TeamHarness projectflow/roomflow) + `protocol-governance.md` (project lifecycle) | 📋 binding-specific (forward-chain detail belongs to the binding README) |
| L10 | Dispatch tri-check (triad @mention + never leave the room) | `protocol-task-lifecycle.md` (dispatch triad) | ✅ absorbed |
| L11 | Re-dispatch three-step re-check (event-ID idempotency signature) | `protocol-task-lifecycle.md` dispatch discipline + binding known issues (platform txn dedup signature) | ⚠️ partial (generic discipline absorbed; platform bug signature belongs to the binding layer) |
| L12 | Spec must be full text (no referential summaries into the spec param) | `protocol-task-lifecycle.md` (spec = full-text contract; context_refs upgrade: references are files, not referential sentences) | ✅ absorbed (upgraded) |
| L13 | One action per message | `protocol-task-lifecycle.md` dispatch discipline | ✅ absorbed |
| L14 | T+X hard deadline = one-shot cron (no heartbeat self-wake; cron text self-contained) | `protocol-task-lifecycle.md` timer discipline + binding (cron CLI shape) + `scripts/timer-derive.sh` (derives T+X) | ✅ absorbed (upgraded: derivation scripted) |
| L15 | Delivery discipline (chunked writes >2KB + delivery must @ the requester + verification evidence) | `protocol-task-lifecycle.md` delivery contract | ✅ absorbed |
| L16 | DAG registration (plan_dag task visualization) | binding layer (workbench plugin as source of truth) | 📋 binding-specific |
| L17 | Acceptance & aggregation (report before confirming) | same as L7 | ✅ absorbed |
| L18 | NMA handling (structured review) | `fragments/protocol-nma.md` | ✅ absorbed |
| L19 | Spawn rules (v2.40 isolation) | same as W3 | ✅ absorbed |
| L20 | @-format iron rule (full MXID, four mention formats) | binding layer (Matrix mention format spec, bindings/agentteams/README) | 📋 binding-specific |

## 4. Critic-Specific Clauses Mapping

| # | Production clause (old) | v1.0 landing point | Status |
|:--:|------|------|:--:|
| C1 | Independence (unaffected by lead; reviewer ≠ task assigner) | `protocol-governance.md` (separation of interests) + `skeleton/critic.md` | ✅ absorbed |
| C2 | Five-dimension review (goal / audience / quality / data / compliance) | role card (instance profile) + `protocol-nma.md` (Checklist mode) | 📋 instance-specific (dimension list) + ✅ mechanism absorbed |
| C3 | Bounce ≤3 → human intervention; deadlock ≥2 rounds → arbitration | `protocol-nma.md` (bounce budget + escalation chain) + `protocol-governance.md` | ✅ absorbed |
| C4 | Never fix for them (opinions only) | `skeleton/critic.md` iron rules | ✅ absorbed |

## 5. Placeholder Mapping (fixture ↔ production)

| fixture placeholder | production original category | note |
|------|------|------|
| `bizmarket-*` / `bizmarket` | team name + role ID prefix | instance param |
| `@human-owner` | human accountable MXID localpart | roster entry |
| `matrix.example.org` | private Matrix server endpoint | topology |
| `<gpu-node>` / `<port>` | GPU node name + text-to-image service port | topology |
| `shared/users/human-owner/` | object-storage human-user path segment | instance param |
| `owner` | human accountable's form of address | instance param |
| `platform-incident C1..C7/P3..P15` | internal incident docket numbers | incident signatures (content kept, numbering de-internalized) |
| `historical incident` | internal incident date | time desensitization |

Retained (public product names, not instance secrets): QwenPaw / spawn_subagent / Matrix / MinIO / mc / TeamHarness / agentteams-controller:6167 (public product standard service name+port) / SATCOM (protocol predecessor name, provenance citation) / SDXL-turbo (public model) / QwenPaw 2.2 3600s (public product version behavior).

## 6. Re-verification Procedure

Any protocol-layer change (core/protocol 13 / invariants / fragments) → re-run this mapping: verify each ✅ absorbed clause's landing point still exists, and each ⚠️/📋 clause's boundary has not drifted. A newly added clause must update this file in the same change. This file missing, or a clause with no landing point = production traceability gate red.
