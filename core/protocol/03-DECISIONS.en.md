# Decision Classes R1-R6 + decision_log

> v1.0
> Core stance: **grade by reversibility, not by "importance"** — reversibility is machine-decidable (rollback path exists? external side effect touched? non-reclaimable resources consumed?).

## 1. Decision Type × Aggregation Rule Matrix

| # | Decision type | Determination (machine-checkable) | Aggregation rule | Lock semantics |
|---|---|---|---|---|
| **R1** | irreversible / external side effect | deploy to production, delete an artifact, send external communication, merge to main branch, spend beyond budget threshold | **Owner single-point ruling**; a non-owner objection is recorded as dissent, does not block; owner absent → escalate to human | once locked by the owner, **not directly overridable by another user**; overturning must go through R5 explicit reopening |
| **R2** | resource consumption / budget | new execution units, long-running tasks, external API spend | **weighted majority** (weight × votes, >50%); tie → escalate | after locking, may be overturned by a new weighted majority **before budget execution** (resources not yet consumed, reversible) |
| **R3** | style / quality trade-off | naming, format, wording, layout, doc structure — choices that don't affect the observable contract | **no aggregation by default**: the single executor of that artifact decides; objections go through NMA rework; weighted majority only when ≥2 stakeholders explicitly request a vote | no lock; NMA rework may override |
| **R4** | reversible implementation detail | internal implementation choices, dependencies/structure not affecting the external contract | **auto-pass**; decided autonomously, recorded in decision_log | no lock; changeable at any time |
| **R5** | overturning a locked decision | any stakeholder requests reopening a locked decision node | **explicit reopening protocol** (§3) | a lock is not permanently immutable; reopening simply costs significantly more than the first decision |
| **R6** | spec ambiguity / attention request | requirement ambiguity, permission boundary, or trade-off encountered during execution, undecidable from the spec | **route to the accountable stakeholder** (§4); the answer, once written to state, is locked | subsequent sub-execution units inherit the answer; they may not silently overturn it at the sub-execution level |

**Rule budget**: 6 aggregation rules + 1 routing rule.
**Compatibility**: single_user = multi_user degenerated to a stakeholder set of {1 person}. R1 degenerates to "human-locked"; R2 degenerates to "one vote is a majority"; that person is the accountable.

## 2. decision_log (B-1)

**Positioning**: the write-to-disk contract for "non-obvious decisions" during execution. State must be written to disk (lesson of Matrix silently dropping messages: a message is not state).

**Storage form** (implemented by the binding layer; core defines semantics only):
- location = object storage (CAP-STORE), path contract `decisions/<task_id>/<spawn_id>.decision.json`
- messages carry only **ref + sha256-8 fingerprint**, never the content (attention protection + tamper evidence)
- append-only (CAP-STORE T3 optional semantics; the binding layer implements it as JSONL / immutable objects)

**Three-layer schema validation** (deterministic; script-implemented = `core/scripts/validate-decision-log.sh`):

| Layer | Timing | Executor | Content |
|----|------|--------|------|
| 1 | after spawn returns, **before acceptance** (run by the parent execution unit) | parent execution unit (an LLM cannot self-validate) | schema integrity: fields / enums / entries ≤10 (contract_touch entries must not be truncated) |
| 2 | before merging multiple spawns | parent execution unit (`detect-conflict.py`, pure function) | conflict detection: same artifact, same field, different value = hard; same key with opposite assumption = assumption; shared-surface only → send to Step 4 |
| 3 | at acceptance | critic / parent execution unit | `decision_log_ref` fingerprint vs fingerprint carried in the message must match; mismatch = reject |

**Entry cap**: ≤10; over the cap = truncate, but entries with `contract_touch=true` are **all retained** (truncation containing a contract_touch entry = schema violation, exit 11).

## 3. R5 Explicit Reopening Protocol

A reopening request must include: **new evidence + the affected acceptance criteria**.

- the **original locker's weight ×2** in the weighted majority
- the original locker objects **and** the new evidence does not touch the acceptance criteria → reopening fails, the lock stands
- original locker timeout (B-4): 24h for irreversible / 4h for reversible; timeout = the ×2 weight **fails down to 1.0** (**not default consent**); a late reply → weight restored and recomputed; the old lock is kept and tagged "overridden by R5"

## 4. attention Routing Rules

1. each task, at creation, binds one **accountable stakeholder** (default = project owner; delegable per task type; the delegation chain is queryable = CAP-ROSTER Z3)
2. the attention request goes to the accountable, CC all approvers (read-only side channel, non-blocking)
3. timeout is two-tiered: reversible (R2/R3/R4) 30min → counted as abstention; if the rest form a majority it takes effect, otherwise escalate to the owner; irreversible (R1/R5/R6 touching external side effects) 2h → task blocked (**never auto-passes**) + notify the owner and the arbitration side
4. two conflicting answers: both approvers with no owner → R2 weighted majority; one is the accountable → that person wins, the other records dissent; equal weight with no accountable → escalate as "no majority"; **in no case may an execution unit use an LLM to summarize two human answers and pick one to execute** — only the aggregated result computed by the protocol layer may be executed

**Scope of weighted majority (C-3 hard constraint)**: limited to **R2 / R4 (and R5 reopening votes)**; **never used for an R6 answer that touches a locked spec** (see §09-GOVERNANCE locked_spec_consistency_check).

## 5. decision_class Misclassification (B-10)

**Scenario**: classified R4 at compile time, but during execution an R1 external side effect is discovered — a classification **error** (not an ambiguity).

```
mismatch event → pause + reclassify
  R4→R1: pause 2h, reclassify
  R3→R2: post-hoc aggregation
  R2→R1: redo
decision_class_v2 = a new record, never overwriting the original (audit chain)
executed side effects go through saga compensation:
  uncommitted → generate compensation instructions (reverse dependency order, core/scripts/saga-compensate.py)
  committed and non-compensable → escalate to human
≥2 mismatches on the same task → audit that task's classification quality (leader misclassification rate)
```

**Classification authority**: the compile-time rule table + the task spec's `decision_class` field (an instance parameter filled by the leader, human-locked). Classification ambiguity → escalate to the accountable for a **one-shot classification ruling** (the human only rules "which rule it belongs to"; no aggregation is executed).

## 6. Type Closure (C-1)

- an entry's `type` in decision_log is a **closed enum**, defined by a type registry (a registry file in CAP-STORE), each entry carrying a **semantic-dimension tag**
- `type_dimension_mismatch` (the same artifact touched by types of different dimensions) = **hard conflict, caught at layer-1 validation**
- a new type must pass critic review to enter a registry version; **inventing types at runtime is forbidden**
- a type not covered by the registry = schema violation (the binding layer pre-provisions the full set at deployment)
