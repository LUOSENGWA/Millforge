# Task 3: Protocol Cost Model + Tiering Final Decision

> Version: v1.0 | License: Apache-2.0

## 3.1 Per-mechanism Trigger Audit

| Mechanism | Trigger scoping | Always mandatory? |
|---|---|---|
| **decision_log** | any spawned execution unit (because the D1/D2/D3 criteria may hit); but when none of D1–D3 is met, the log may be empty and must be marked `no_significant_decisions` | **conditionally mandatory**: the spawn must produce it, but the content may be zero entries (an explicit "no significant decisions" declaration is required, not an omission) |
| **contract** | cross-boundary parallel implementation (≥2 execution units writing the same contract surface, or provider/consumer separation) | **conditionally mandatory**: no contract required without cross-boundary |
| **critic isolation** | any artifact needing acceptance (when a deliverable must be accepted) | **always mandatory** (if the deliverable has an acceptance stage); pure read-only / research tasks without artifact acceptance may have no critic |
| **Conflict detection Step 1–3** | ≥2 decision_logs on the same artifact | **conditionally mandatory**: single spawn, no parallel write → skip |
| **Three-part handoff** | cross-team / cross-Leader boundary | **conditionally mandatory**: the three-part format is not required inside a team |
| **NMH** | a new spec or a major spec change | **conditionally mandatory**: routine tasks with an already-locked spec do not require re-interrogation |
| **R1–R6 aggregation** | when a decision touches human input | **conditionally mandatory**: an R4 within the Agent's autonomous scope auto-passes |
| **Fingerprint / submission fence** | any artifact persistence | **always mandatory** |
| **Declaration–verification binding** | any "pushed / dispatched" claim | **always mandatory** |

## 3.2 Per-task Cost Budget

**Human touch = the scarcest resource.** The following is estimated per three tiers of tasks:

| Tier | Task profile | Additional spawns | Human touches | New artifacts |
|---|---|---|---|---|
| **Simple**: a single-worker simple task (e.g., a single-file documentation edit, a single query) | no parallel write, no cross-boundary, decision_class dominated by R4 | 0–1 (critic optional; 0 if the deliverable needs no acceptance) | 0–1 (only when R6 is triggered) | 1–2 (artifact + optional decision_log) |
| **Standard**: single-team multi-worker parallel (e.g., provider/consumer parallel as in SW-01, analysis-read parallel as in BIZ-01) | parallel writes, contracts, may need a merge | 1–3 (merge spawn + optional bounded classification spawn + critic) | 1–3 (NMH spec lock + possible R6 attention + mismatch clarification) | 4–8 (contract + 2×decision_log + merged artifact + critic report + handoff) |
| **Full**: cross-team chain (team A → team B, coordinated by the Manager) | every mechanism may trigger | 3–6 (per-team merge/critic + Manager coordination) | 2–5 (per-team NMH + cross-team handoff attention + possible R5) | 8–15 (per-team artifacts + cross-team handoff + decision record) |

**Human touch budget** (alert on budget excess):

| Tier | Budget | Meaning of excess |
|---|---|---|
| Simple | ≤1 | excess means the spec quality is poor (many ambiguities) or the task was misclassified as simple |
| Standard | ≤3 | excess means frequent parallel-write conflicts or recurring critic/spec inconsistencies |
| Full | ≤5 | excess means poor cross-team handoff quality, unstable contracts, or too many R5 reopens |

**Alert rule**: each tier's task maintains `human_touch_count` in the task meta; when the budget is exceeded, mark `human_touch_budget_exceeded` in the provenance and trigger a self-check (not an automatic escalation — it is a signal to the Leader/Manager: "this task's protocol overhead is too high, check the spec and the contracts").

## 3.3 Tiering Final Decision: Do We Need Task-Complexity Tiers?

**Recommendation: introduce the three tiers simple / standard / full, but the role of the tiers is to "declare which mechanisms may be conditionally skipped", not to "skip the protocol core".** Tiering is an **input parameter** (declared in the spec at task creation by the accountable stakeholder or the Leader), not an escape hatch the executor may freely choose at runtime.

**Arguments against "trigger-based scoping alone is enough"**: the problem with trigger-based scoping is that the "trigger determination" itself costs — the Leader has to judge "does this task cross a boundary" and "are there parallel writes", and those judgments may err (misjudged as simple, skipping the decision_log). Tiering moves the determination forward to spec creation, locked in by a human; the executor cannot downgrade mid-flight.

**Arguments in favor of tiering**: if the protocol cost does not match the task risk, the executor will vote with its feet and bypass the protocol (e.g., splitting a cross-boundary task into two "single-team" tasks to avoid the contract). Tiering provides a legal downgrade path, but the downgrade must be explicitly declared and recorded, not silently bypassed.

### Concrete Tiering Rules

| Mechanism | May simple downgrade? | standard | full | Rationale |
|---|---|---|---|---|
| **Fingerprint / submission fence** | ❌ **not downgradable** | mandatory | mandatory | the foundation of integrity; downgrading = silently losing data |
| **provenance** | ❌ **not downgradable** | mandatory | mandatory | the foundation of audit; downgrading = untraceable |
| **Acceptance binding (critic or equivalent verification)** | ⚠️ may be simplified to "single-pass verification", but may not be omitted | mandatory | mandatory | no acceptance = claims become facts |
| **Human-locked spec (NMH or explicit spec lock)** | ❌ **not downgradable** (interrogation rounds may be simplified, but the spec must be human-confirmed) | mandatory | mandatory | requirement authority cannot be delegated to an Agent |
| **decision_log** | ✅ may be reduced to "empty log + `no_significant_decisions` declaration" | mandatory (D1–D3) | mandatory | without parallel writes, D3 is not met; the log may be empty but must be explicit |
| **contract** | ✅ may be skipped (not required without cross-boundary anyway) | mandatory when cross-boundary | mandatory | conditionally triggered |
| **Conflict detection Step 1–3** | ✅ may be skipped (single spawn, no conflict) | mandatory when parallel write | mandatory | conditionally triggered |
| **Three-part handoff** | ✅ may be skipped (inside a team) | mandatory when cross-team | mandatory | conditionally triggered |
| **R1–R6 aggregation** | ✅ R4 auto-passes; R1/R2/R5/R6 still per the rules | mandatory | mandatory | irreversible decisions like R1 cannot be downgraded |

**Verification of your prediction**: you said "the non-downgradable list = fingerprint / provenance / acceptance binding / human-locked spec" — **essentially correct, with one correction**: in the simple tier, the acceptance binding may be **simplified** to "single-pass verification" (e.g., the parent Worker performs one declaration–verification check), rather than requiring an independent critic. Omitting the acceptance binding entirely is unacceptable (that would degenerate into "claims become facts"). The other three are entirely non-downgradable.

**The enforcement mechanism that tiering is not an escape hatch**:

1. The tier declaration is **locked in by a human at spec creation** (NMH or explicit confirmation); the Leader cannot downgrade it on its own.
2. If during execution the actual complexity is found to be higher than declared (e.g., a simple task develops parallel writes) → a `complexity_mismatch` event must be emitted and handled per B-10's saga compensation logic, rather than continuing to run as simple.
3. The provenance records the tier and any downgrade decision; the golden tests include a check for "whether a simple-tier task is correctly confined within the simple mechanisms".

## 3.4 Self-check: Does the Cost Model Assume Metrics Only a Specific Runtime Has?

| Metric | Data source | CAP-* only? |
|---|---|---|
| human_touch_count | CAP-STATE attention resolve event count + NMH lock events | ✅ derived from the CAP-STATE event stream |
| spawn_count | CAP-SPAWN creation events | ✅ |
| artifact_count | CAP-STORE write events | ✅ |
| Budget-exceeded alert | provenance marker, derived by the compiler / protocol layer from CAP-STATE events | ✅ does not depend on dashboard statistics |

**Conclusion**: the cost model is derived entirely from the CAP-STATE event stream and does not depend on any specific runtime's dashboard statistics. A dashboard is only a visualization view of these events, not a data source.


## Multi-critic Budget Note

The N critics of multi-critic voting = N fresh spawns, **all counted in the spawn budget** (no discount).
On budget excess, **do not downgrade to a pure single critic** — the downgrade path = "single critic + mandatory dissent + human-locked acceptance"
(a human must explicitly confirm the single critic's conclusion). See `core/protocol/05-NMA.md` §12 Cost integration.
