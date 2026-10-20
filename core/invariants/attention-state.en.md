# Invariants: Attention Request Lifecycle (CAP-ATTN)

> The carrier for R6 decisions / escalations / clarifications. Authoritative state = CAP-STATE (the CAP-ATTN interface is the access surface, not storage).

## 1. Request State Machine

```
 (request)
    │  idempotency_key = hash(task_id + request_id + responder_expected + action)
    ▼
 pending ──resolve (W4 identity verification passed)──▶ resolved
    │  ▲
    │  └──repeated resolve (same idempotency key)──▶ resolved (returns the first result, ALREADY_RESOLVED)
    │
    ├──timeout_at reached (CAP-TIMER verdict)──▶ expired (two-tier consequences, see §2)
    │
    └──identity verification failed──▶ rejected (IDENTITY_UNVERIFIED; no response is produced)
```

## 2. Timeout Consequences (§03-4 timeout tiers)

| Class | Window | Expiry action |
|------|------|---------|
| reversible (R2/R3/R4) | 30min | abstention counting (a defer counts in the denominator); if the rest form a majority → takes effect; otherwise escalate to the owner |
| irreversible (R1/R5/R6 touching external side effects) | 2h | **task blocked (BLOCKED) + notify the owner and the arbitration side — never auto-pass** |
| R5 reopen window (B-4) | irreversible 24h / reversible 4h | the locker's ×2 weight fails down to 1.0 (not default consent); a late arrival is restored and recomputed |
| B-6 mismatch window | 24h | the original spec stands + the critic records dissent and still emits the scorecard |

**Stall counting** (B-5): a derived value (attention-stall.sh reads CAP-STATE and computes it): 1=watch / 2=blocked + abstention counting forbidden / 3=frozen + explicit human unfreeze; any human reply → reset to zero (only open timeout items opened since the last human reply are counted).

## 3. Invariant Assertions

1. **I-A1** (W1) the same idempotency key → the same request_id; the same (request_id, responder_id, idempotency_key) → the same response (resolve is idempotent)
2. **I-A2** (W2) a resolved record must contain responder_id + surface_id + timestamp, and must already be written to CAP-STATE (not merely "read" on a channel)
3. **I-A3** (W3) timeout_at lives in CAP-STATE; the verdict is triggered only by CAP-TIMER + script derivation; the request itself has no wall-clock timer
4. **I-A4** (W4) the resolve responder's identity is verified through the runtime's member_id mapping; a self-declared role in the payload is invalid; a group-chat surface must not resolve (S4)
5. **I-A5** (W5) every pending request has at least one persistent display surface in surfaces[] (persistently present before timeout + revisitable + identity-verifiable)
6. **I-A6** (W6) multi-surface close: after the first resolved, the other surfaces' states sync; the close does not change authoritative state (view behavior)
7. **I-A7** (W7) when kind=decision + options exist, the resolve response must be an option_id (a free-text choice = rejected)
8. **I-A8** (S5 replay) the resolve idempotency key includes task_id; cross-task request_id replay = NOT_FOUND
9. **I-A9** when two approvers conflict: if one is the accountable → that person wins (the other records dissent); equal weight with no accountable → escalate as "no majority"; **an execution-unit LLM must never summarize two human answers and pick one to execute** (only the protocol's aggregated result may be executed)
10. **I-A10** the escalation chain's final ruling = human; agent arbitration only produces an aggregated result / an escalation signal
