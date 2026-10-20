# Invariants: Decision Node State (NMH Lock / R5 Reopen / Contract Lock)

> Decision node = NMH decision-tree node + contract pin + locked spec field. A lock is not permanently immutable — it means **reopening costs significantly more than the original decision** (R5).

## 1. Node State Machine

```
 🔓 open ──human confirm/modify/veto──▶ ✅ locked
    ▲  │
    │  └──parked 🏳️ / agent-doesn't-know 🏳️──▶ 🏳️ parked
    │
    └── R5 reopen succeeds (weighted majority + new evidence + original locker ×2 valid)
```

| State | Semantics | Outgoing edges |
|------|------|------|
| 🔓 open | exploring / not locked | human reaction table (04-NMH §7) → locked/parked |
| ✅ locked | locked, with the human's own words + timestamp | R5 reopen → locked (v2 supersession record); evolution append → locked+eN |
| 🏳️ parked | explicitly parked | must be handled during execution → escalation path (04-NMH §7); new evidence → open |

## 2. Lock Records (append-only, never overwrite)

- each lock/reopen = a new record `{node_id, version, decision, human_quote, locked_by, locked_at, supersedes?}`
- **R5 supersession**: the old lock record is kept + tagged `superseded_by: <new_version>` (audit chain; "overridden by R5" marker)
- **evolution**: `[D{n}-e{N}]` is appended; the original node text is never modified
- a contract pin supersession = a new semver version; the old version object is retained (CAP-STORE is immutable)

## 3. Invariant Assertions

1. **I-D1** lock records are append-only: no "modify a lock record" operation exists (only a new version)
2. **I-D2** a locked record's `human_quote` is non-empty and `locked_by` ∈ roster (never lock on behalf of the human = machine-checkable: locked_by must be a human member ID)
3. **I-D3** a successful R5 reopen record must contain: new-evidence ref + the affected acceptance-criteria list + vote record ref (aggregate-vote output)
4. **I-D4** B-4 late down-weighting: when the locker's vote.received_at > due_at, weight is recorded as 1.0 (script-derived, not written); a late arrival = recomputation and re-issuance of the count
5. **I-D5** a contract pin's fingerprint matches the CAP-STORE actual value (double verification before merge / at acceptance, S2)
6. **I-D6** before a locked spec field is modified by an R6 answer / weighted majority, it must pass locked_spec_consistency_check (C-3); contradict → the modification does not take effect + spec_conflict
7. **I-D7** types are closed: a decision_log entry's type must be in the current type-registry version (C-1); a dimension conflict = rejected
8. **I-D8** concurrent R5 requests on the same node → deduplicated by idempotency key (hash(task_id+node_id+requester+evidence_fp)); no double reopen

## 4. Escalation Boundaries

- parked past the task completion deadline → treated as "undecided"; at acceptance it is handled as blocked (never a default pass)
- a 🏳️ "agent-doesn't-know" node: an execution unit must not fill it; only a human / external information may clear it
