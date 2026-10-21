# Invariants: Task State Machine (T3 Overlay Layer)

> The core constrains only the mapping between **protocol substates** (decision_status) and runtime state; it does not rewrite the runtime task state machine.
> The 9-state runtime states (upstream task contract: planned / prepared / assigned / in_progress / submitted / completed / revision / blocked / cancelled) stay untouched.

## 1. decision_status Substate Transitions

```
        blocked ──human unfreeze / condition cleared──▶ open
         ▲                                              │
         │ (stall 2 / R5 irreversible timeout /          │ (stall 3)
         │  C-3 reject / failed paused re-classification) ▼
        frozen ◀──────────────────── open
```

| Transition | Trigger | Deterministic verdict (script) |
|------|------|-------------------|
| open → blocked | R6 stall count = 2 (attention-stall exit 40); R5 irreversible window timeout (aggregate-vote exit 81); C-3 contradict rejection; B-10 re-classification pause | `attention-stall.sh` / `aggregate-vote.sh` / `consistency-check.py` |
| blocked → open | condition cleared (human reply / ruling / re-classification done); **except from frozen** | human action record (CAP-STATE append) |
| blocked → frozen | stall count = 3 (attention-stall exit 41) | `attention-stall.sh` |
| frozen → open | **explicit human unfreeze** (no automatic recovery path) | human action record |
| open → spec_conflict | enters the spec_conflict escalation chain after C-3 rejection | `consistency-check.py` exit 70 |
| spec_conflict → open/blocked | human ruling: revise spec (→open) / keep spec and escalate (→blocked) | human action record |
| open → paused | B-10 mismatch re-classification window (R4→R1 2h) | `saga-compensate.py` event record |
| paused → open | re-classification done + saga compensation succeeded | `saga-compensate.py` |
| paused → blocked | re-classification finds a non-compensable side effect (exit 60) | `saga-compensate.py` |

## 2. Runtime Mapping (one-way; no write-back)

| decision_status | Runtime state | Note |
|-----------------|-----------|------|
| open | unchanged (planned/assigned/in_progress…) | normal progress |
| blocked | **BLOCKED** | recoverable |
| frozen | **BLOCKED** | marked with the frozen substate (metadata) |
| paused | BLOCKED | re-classification window |
| spec_conflict | BLOCKED | inside the escalation chain |

**Forbidden**: the protocol layer writes runtime state directly (only the single BLOCKED convergence point may be written); runtime state changes do not automatically change decision_status (the script derives, then writes back).

## 3. Invariant Assertions (golden-test checkable)

1. **I-T1** decision_status ∈ {open, blocked, frozen, paused, spec_conflict}; no other values
2. **I-T2** frozen has exactly one outgoing edge: "explicit human unfreeze" (no automation script may produce a frozen→open transition)
3. **I-T3** every transition appends to decision_status_history (all four fields: from/to/at/reason)
4. **I-T4** timeout verdicts read only task_meta.timeout_at / attention.due_at (F-2: timer/watchdog caches do not participate in verdicts)
5. **I-T5** no merge/consumption/acceptance may be triggered before the CAP-STATE write receives synchronous confirmation (F-1)
6. **I-T6** the decision_status of an in-loop task does not affect the loop's authoritative state (loop_state is independent, §10-3)
7. **I-T7** the timestamps in one task's decision_status_history are monotonic (single clock source, CAP-TIMER U1)
