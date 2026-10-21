# Task 5: Final Self-Adversarial — the 3 Places You Will Hit in Production Week 1

> Version: v1.0 | License: Apache-2.0

## 5.1 Protocol Self-Versioning: task meta Field Compatibility of In-flight Tasks

**Problem**: when the protocol evolves from v1.0 → v1.1 (e.g., adding a `decision_status` sub-state, changing fields of `attention[]`), the in-flight task's task meta is in the v1.0 structure, while the new core scripts expect v1.1 fields. What happens when they run mixed?


**Fix**:

```
Core clause addition (protocol versioning):
1. The task meta must contain a `protocol_version` field (written at task creation).
2. Before reading the task meta, the core scripts must check protocol_version:
   - if == current version → execute normally.
   - if < current version → migrate in place via the registered upgrade function
     (upgrade_vX_to_vY); the migration is deterministic and does not rely on an LLM.
   - if > current version (an old core reading new state) → refuse to execute, report
     `PROTOCOL_VERSION_TOO_OLD`. No silent downgrade.
3. Upgrade functions are shipped with the core (core/scripts/upgrade/); each major version
   must provide a migration path from the previous version.
4. The protocol version of an in-flight task does **not** change automatically with a global
   upgrade; new tasks use the new version, and an old task is marked deprecated after it
   completes. The binding must support at least two versions of the core scripts coexisting
   (version routing is decided by `protocol_version`).
```

**Attribution**: core clauses + core/scripts/upgrade/. The binding layer is responsible for version routing (which version of the script to invoke).

## 5.2 Native Context Budget: X1 Protects spawn — Who Protects native?

**Problem**: CAP-SPAWN's X1 guarantees that a spawn is a fresh context, but the parent Worker's native session carries scheduling + review + merge adjudication + B-2 Step 5 conflict adjudication + critic coordination — this work continuously inflates the native context. In production week 1, the native session will hit compaction due to an over-long context and lose early decisions.


**Fix (binding rule + core constraint)**:

```
Core clause addition (native context budget):
"The execution unit (native session) carrying scheduling/review/adjudication must declare
its context budget and trigger structured eviction when the budget approaches its limit —
evicting detailed logs of completed subtasks first, retaining: decision log references,
the list of open conflicts, and the current task's acceptance_criteria. Eviction must not
lose the authoritative state in CAP-STATE."

Binding rules (reference binding):
1. Native session context usage ≥60% → trigger a compaction early warning (the 60%
   early-warning threshold is a mature pattern in long-running agent runtimes);
   ≥80% → force structured eviction.
2. Eviction strategy: retain the open attention items, the current task spec, and the
   critic's open mismatches; evict the full decision_log of merged spawns (keep only
   the ref).
3. Each eviction is written into the provenance (evicted_refs[], tokens_saved).
4. If the native needs to read multiple decision_logs for adjudication, the adjudication
   input must come from the merge spawn's summary, not from the native reading the full
   logs directly (B-2 Step 5 is already this pattern, but it must be made explicit in
   the native budget rule).
```

**Source basis**: compaction of long-running agent sessions is a known problem; the 60% threshold and structured eviction in existing long-running agent runtimes (priority regions, lower priority evicted first) is a mature pattern. The protocol only requires "declared budget + structured eviction + no loss of authoritative state"; the concrete thresholds are binding parameters.

## 5.3 Long Tasks Without a Human: the Owner Is on Vacation for a Week — Does the Delegation Chain's Operational Path Work?

**Problem**: every R1 irreversible decision blocks for 2h×N; the Z3 delegation chain exists, but in the "owner on vacation" scenario, the **initiation** of delegation, the **scope of the delegate's authority**, **batch delegation during the vacation**, and **how to audit the delegate's decisions after the return** — these operational paths are not refined in the protocol.


**Fix**:

```
Core clause addition (execution details of CAP-ROSTER Z3):
1. The accountable stakeholder may set up a **time-limited batch delegation**:
   delegation = {delegatee, scope: decision_class[], valid_from, valid_until, max_uses?}.
   valid_until auto-expires on the due date, without relying on manual revocation.
2. A delegation must be recorded in an NMH or an explicit confirmation; an Agent must
   not initiate a delegation on its own.
3. Vacation scenario: before the vacation, the owner sets up the delegation covering
   R1/R2/R5/R6, valid_until = the return date; the delegatee's decisions are written
   into the decision record marked `via_delegation: true`.
4. After the owner returns, they must review the decision records of the delegation
   period; before the review, the delegation is marked `pending_owner_review`, but this
   does not affect the validity of the decisions already executed (decisions do not
   become invalid because of a post-hoc review).
5. If the owner has not set up a delegation and is absent → per the B-5/R6 timeout
   rule: R1 blocks, escalate to the project owner; if the project owner is also absent
   → arbitrator freeze. No automatic release.
```

**Attribution**: core clauses (extension of CAP-ROSTER Z3) + the binding's roster storage implementing batch delegation.

**Source basis**: the decision-authority framework of governance constraints emphasizes that "whose constraints count" must have an explicit rule; the SRE freeze-exit also requires that only "the engineering lead and the product owner together" can unfreeze — a long-term absence must have a pre-authorized delegation mechanism, otherwise the system stalls.

## 5.4 Appendix: the Clock Problem (the Fourth Point You Listed)

**Problem**: U4 declares a monotonic clock, but each of multiple containers has its own clock; who writes `timeout_at`, and whose clock is authoritative?

**Fix**:

```
CAP-TIMER U1 revision (supplementing clock authority):
"timeout_at must be written by CAP-STATE, using the time of the clock source where
CAP-STATE resides; when the timer fires, the 'now' being compared must also come from
the same clock source, or be aligned via a one-time clock offset correction (NTP sync
status queryable). No execution unit may use its local wall clock to directly judge a
timeout."
```

**Attribution**: core clauses (supplement to U1) + the binding implementation (in a single-machine deployment, CAP-STATE and the timer share a clock; in a distributed deployment, NTP or a logical clock alignment is required).


# Self-check Summary

| Task | Self-check question | Result |
|---|---|---|
| **Task 1** | Does the UX hold under the 8 capabilities + 2 new invariants? | Holds; the reference binding's PR is a binding-layer implementation, not a core requirement |
| **Task 2** | Does the security section leak component names? | no runtime-specific names; the mechanism matrix references only CAP-* and protocol rules |
| **Task 3** | Is the cost model derived only from CAP-STATE? | Yes; human_touch_count / spawn_count / artifact_count all come from the CAP-STATE event stream |
| **Task 4** | Are CAP-STORE T1–T3 all implementable under S3? | T1 client-side hash; T2 strong consistency + conditional PUT; T3 chained append emulation. CAP-STATE is not recommended to use object-storage CAS |
| **Task 5** | Are the 3 problems things you hit in production week 1? | versioning / native context / long-term-absence delegation / clock — all production-ops aspects |

