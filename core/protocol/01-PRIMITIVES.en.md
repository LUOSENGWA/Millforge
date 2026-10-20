# Primitive Set (15 Primitives)

> v1.0 | Provenance: NMProtocol §3 (13 primitives) + round-7 loop (14th) + round-8 signal (15th)
> Semantics are defined exactly once here. The binding layer may only map (primitive → concrete mechanism); it may not redefine.

| Primitive | Definition | Note |
|------|------|------|
| `human` | a human user. The system's final decision-maker and learner | a cluster may have multiple humans (multi-user mode) |
| `agent` | an LLM-driven collaboration unit | has a role |
| `leader` | team orchestrator: understands tasks, decomposes, dispatches, accepts, reports | one per team |
| `worker` | executor: takes atomic tasks, produces deliverables, reports blockers | may include special workers (critic = dedicated reviewer) |
| `arbitrator` | arbiter: the escalation target for decision deadlocks (🏳️); in single-user mode also the cross-team coordinator | mode-dependent (§02-MODES) |
| `room` | a multi-party communication space: team room / task room (project group) / DM | the primary carrier of structured communication |
| `project` | a work unit with an ID, owning a plan, dependencies, and acceptance progress | state managed by the mechanism layer (CAP-STATE) |
| `task` | an atomic work item within a project, with spec / delivery dir / state machine | the unit of dispatch and acceptance |
| `artifact` | a task output file (document/code/data) | stored in object storage (CAP-STORE), with a path contract |
| `decision node` | one node of an NMH/NMA decision tree, with state markers | immutable once locked; evolvable |
| `channel` | the original communication channel between human and agent (IM/email/console) | the "originating channel" of dual-channel reporting |
| `mode` | deployment mode: `single_user` / `multi_user` | determines the arbitrator's form and cross-team extension availability |
| `attention` | a human-attention request: the carrier of R6 decisions/escalations/clarifications, with reply persistence and timeout semantics | 13th primitive; depends on CAP-ATTN |
| `loop` | a goal-driven iteration container: goal locked → iterate (dispatch → independent verification) → achieved? stop : re-plan; runs within budget | 14th primitive (§10-LOOP); contains tasks, not equal to a task |
| `signal` | a protocol marker on key messages: grants an event the qualification to be "cited by review/acceptance/closure" | 15th primitive (§11-SIGNAL); creates no new storage form |

**Capability dependencies**:
- `attention` → CAP-ATTN (idempotent / reply persistence / timeout via CAP-TIMER / trusted identity)
- `loop` → CAP-STATE (authoritative state) + CAP-TIMER (fallback wake) + CAP-SPAWN (X2 structured return + X4 boundedness)
- `signal` → CAP-STATE (event_type field) + CAP-STORE (ref fingerprint verification)

## Role Invariants (all bindings must obey)

- `leader` ≠ `worker` — a task dispatched to a leader = a project-level task (requires creating a room/project), not "DM a task and done"
- a `worker` does not decompose and does not dispatch to other workers (exception: the special worker critic only reviews, never executes)
- the `arbitrator` (single-user mode) does not do a worker's work — the orchestrator is not the implementer (failure SOP in §06-LIFECYCLE 6.6)
- **`leader` ≡ `arbitrator` functional alignment**: the two are the same orchestrator role kind, with the same functional core = task decomposition/dispatch/acceptance + peer review + closure reporting; the only differences are **jurisdiction** (team vs cluster) and **existence condition** (the arbitrator exists only in single_user). Same protocol, different jurisdiction only
- **verifier ≠ declarer** (core of the five clauses): no producer may accept its own output. The critic runs in an independent fresh context (CAP-SPAWN X1)
- **single accountable point**: every project/loop/decision has exactly one accountable stakeholder (CAP-ROSTER Z2); the delegation chain is queryable (Z3); collective lock-holding is forbidden
