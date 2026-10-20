# Invariants: Loop State Machine (14th Primitive)

> The checkable part of §10-LOOP. Loop authoritative state exists only in CAP-STATE (task_meta.loop_state); the driver keeps no independent counter.

## 1. Five-Phase State Machine

```
 DISPATCH ──spawn dispatched OK──▶ EXECUTE
    ▲                              │ X4 bounded return (structured result or bounded_failure)
    │                              ▼
 RE-PLAN ◀──JUDGE: not_achieved + budget left + progress── VERIFY (independent critic)
    │                              │
    │                              ├──JUDGE: achieved──▶ STOPPED(success)
    │                              ├──JUDGE: no progress (convergence_rule)──▶ STOPPED(stalled)
    │                              ├──JUDGE: budget exhausted──▶ STOPPED(exhausted)
    │                              └──JUDGE: undecidable──▶ escalate (R6) → re-JUDGE after resume
    │
    └── RE-PLAN exceeds max_replans ──▶ STOPPED(exhausted)
```

RECORD is the write-to-disk action after each JUDGE (not a standalone phase): `{iteration_index, result_refs[], critic_verdict, progress_signal, budget_consumed}` appended to the loop history.

## 2. Invariant Assertions

1. **I-L1** single point of authoritative state: the loop's current_iteration / budget_remaining / phase / last_verdict live only in CAP-STATE; an execution unit's context is not an authoritative source (driver wake = read + derive, no incremental notes)
2. **I-L2** (idempotency) a repeated request with the same iteration and same input → ALREADY_RESOLVED (idempotency key = hash(loop_id + iteration_index + action_type + input_fingerprint)); same input across iterations = a different request + a "repeated input" alert
3. **I-L3** (achievement verdict) STOPPED(success) can only be derived after the stop_condition predicate / critic writes last_verdict=achieved; the driver must not self-judge achievement
4. **I-L4** (boundedness) iteration_budget is human-locked (max_iterations + max_human_touch); an execution unit self-starting a loop / expanding the budget = protocol violation (golden test assertion: no human_lock record → the loop must not be created)
5. **I-L5** (anti-fragmentation) ≥2 tasks under the same goal_ref with an artifact dependency chain → they must share one loop container; >3 cross-referencing simple tasks → suspected_loop_fragmentation alert
6. **I-L6** (anti-padding) progress_signal is magnitude-aware (acceptance_delta/score_delta below min_score_delta = no progress; pure formatting change does not count); consecutive low_yield counts into no_progress_window
7. **I-L7** (X4 dependency) every spawn inside a loop must declare a deadline + bounded return (structured result or bounded_failure); on a binding without X4, the loop must not run
8. **I-L8** (budget sharing) cross-team reflow consumes the shared iteration_budget pool (not a free retry); default ≤2 full reflows (full tier human-locked ≤4)
9. **I-L9** (semantic stall) 2 consecutive reflows pointing at the same criterion with an unchanged evidence_fingerprint → terminate and escalate immediately (even if budget remains)
10. **I-L10** (human-touch aggregation) max_human_touch is aggregated over the whole loop by goal_ref; a re-plan itself does not touch a human (only a re-plan needing clarification goes through R6 counting)
11. **I-L11** (driver absence) a driver crash does not affect authoritative state; the scheduler keeps triggering; heartbeat beyond the declared bound → escalate; after recovery the driver re-derives idempotently from CAP-STATE (never replaying recorded actions)
12. **I-L12** (native budget) the driver's context keeps only iteration summaries {index, verdict, progress_signal, key_refs[]}; full artifacts go through a review spawn

## 3. Termination Action Sequence (termination_action executed in order)

| Terminal state | Action sequence |
|------|---------|
| success | emit_artifact → write_decision_record → (cross-team) notify the arbitrator to aggregate |
| exhausted | write_decision_record → escalate(accountable, reason=budget) |
| stalled | write_decision_record → escalate(accountable, reason=semantic_stall/no_progress) |

The follow-up to exhausted/stalled = R1 handling (accountable ruling: continue / terminate / redefine goal) — not automatic continuation.
