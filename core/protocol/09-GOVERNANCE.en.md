# Governance: Voting, Ruling, State Mapping

> v1.0
> **Aggregation execution boundary**: vote counting, timeout judgment, escalation triggering are all **pure-function logic** (core/scripts/, L2) — humans only supply vote/ruling inputs; execution units only execute the result the protocol layer computes.

## 1. Vote Execution (deterministic)

- **R2/R5 weighted counting** = `core/scripts/aggregate-vote.sh` (exit 0=pass/reject/wait, 80=tie escalation, 81=irreversible timeout block, 82=data unreadable)
- weight = **role weight** (owner/approver/informed × value), never model confidence
- counting input = the attention entry votes[] in CAP-STATE (state is authoritative), never the message stream
- **a tie never re-votes** (escalate directly); **no vote ≠ consent** (absence is not a vote)

## 2. R5 Locker Timeout (B-4)

- window: irreversible **24h** / reversible **4h**
- timeout = the original locker's ×2 weight **fails down to 1.0** (**not default consent**)
- a late reply → weight restored and recomputed
- the old lock is kept and tagged "overridden by R5" (audit chain, never deleted)

## 3. R6 Stall Fuse (B-5)

- the count of unanswered attention timeouts = a **derived value** (`core/scripts/attention-stall.sh`, computed by reading CAP-STATE, never write-accumulated)
- **1st**: watch (record)
- **2nd**: escalate to the accountable stakeholder + task `blocked` + **abstention counting forbidden** (a defer counts in the denominator, against passage)
- **3rd**: task `frozen`, **explicit human unfreeze** (no automatic recovery)
- **any human reply → the counter resets to zero** (derived semantics: only open timeout items opened since the last human reply are counted)

## 4. NMH × multi_user Constraint (B-8)

- **accountable holds the lock**: the locking authority for an R6 spec answer belongs to the accountable stakeholder; no weighted vote
- weighted majority is **limited to R2 resource class** (and R5 reopening) — never used for answers touching a locked spec
- the arbitration side, in any mode, **never produces a substantive decision** — only an "aggregated result" or an "escalation signal"

## 5. locked_spec_consistency_check (C-3, the most critical defense)

**The hole**: a weighted majority can "legally by procedure" overturn a human-locked spec — the human lock is bypassed through procedural legality.

**Handling**: before any R6 answer / weighted-majority result is **written back**, `core/scripts/consistency-check.py` is mandatory:

```
R6 answer / majority result
  → rule layer (mechanical judgment on structured fields: forbidden/allowed_values)
      → contradict → reject → spec_conflict escalation chain (human ruling)
      → consistent → write back
      → undecidable
          → LLM constrained-classification spawn (fixed schema {input_hash, contradict, criterion_id, reason≤50})
              → contradict → reject → escalate
              → neutral / hash mismatch / no fallback → undecidable → escalate to human
              → never auto-release (no path may silently write)
```

**Discipline**:
- the rule layer first; the LLM intervenes only when the rule cannot decide, and its output schema is fixed (reason ≤50 chars, no free play)
- **a non-structured answer is directly undecidable** (never force a rule judgment on it)
- idempotency key = input hash; hash mismatch = stale = untrustworthy = undecidable

## 6. State Mapping (T3: the upstream state machine is untouched)

**Principle**: protocol substates are an **overlay layer**; the runtime's existing task state-machine contract is not modified.

| Protocol decision_status | Runtime mapping | Note |
|---------------------|-----------|------|
| open | RUNNING/QUEUED (unchanged) | normal progress |
| blocked | **BLOCKED** | R6 fuse 2nd time / R5 irreversible timeout |
| frozen | **BLOCKED** | fuse 3rd time; explicit human unfreeze → open |
| paused | BLOCKED | B-10 misclassification pause-reclassify |
| spec_conflict | BLOCKED | escalation after C-3 rejection |

- **the sole authority for timeout judgment = the timeout_at / due_at fields in task meta** (CAP-STATE) — timer/watchdog caches only deduplicate notifications; they are never the basis of judgment (F-2: idempotent re-derivation)
- **write-confirmation iron rule (F-1)**: after task meta / decision_log is written to CAP-STATE/CAP-STORE, **no merge/consume action is allowed before the synchronization layer confirms (write confirmable, T2)**
- decision_status changes are appended to the task meta history (audit chain)

## 7. Escalation Chain (overall map)

```
execution unit meets ambiguity → R6 attention (accountable, 30min/2h timeout)
  → stall count 2 → blocked + escalate
  → stall count 3 → frozen + explicit human unfreeze
verification bounce → mismatch window 24h → timeout keeps the spec (dissent preserved)
  → same criterion 3 rounds → frozen + human final ruling
tie / no majority / classification ambiguity → escalate accountable → owner → (single_user) human final ruling
contract major / irreversible timeout / non-compensable side effect → straight to human
```

**Final ruling authority is always = human** (agent arbitration only produces escalation signals).
