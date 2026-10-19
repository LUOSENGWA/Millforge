## Attention UX (persistent-surface answering · condensed load · full text = CAP-ATTN W1-W7 + 12-REDLINES S4)

**Answering-surface quality (W5)**: every attention request must have at least one **persistent display surface** — present until timeout, actively revisitable, responses identity-verifiable.
- ✅ Persistent surfaces: IM private-chat bot / dashboard todo list / dedicated approval page / console notifications
- ❌ **A group-chat @mention is not one** (buried in messages, not revisitable, identity unreliable)
- a channel with trust below the persistent-surface requirement → may notify only, may not resolve

**Answering semantics**:
- a human expresses intent in a group chat → guide them to explicitly resolve on a persistent surface (bot replies "please confirm in private chat / on the approval page")
- a resolve must verify the responder's identity (runtime member_id mapping; a self-declared role in the payload is invalid)
- kind=decision + options → the response must carry back the **option_id** (W7 structured); free-text choice = rejected
- multi-surface close (W6): any surface resolves → the others close via poll/event sync (view behavior; the authoritative state is not touched)

**Timeout (CAP-TIMER decides, W3)**: reversible 30min / irreversible 2h (blocking, never auto-passes); R5 reopen window 24h/4h; the expiry action = derived (recomputed from CAP-STATE), not "a marker stored in the timer".

**Idempotency (W1/S5)**: a repeated resolve returns the first result; the idempotency key includes task_id + request_id + responder_id + action; cross-task replay = rejected.

**Your duties** (as the initiator):
1. when raising attention, provide options (structured, each with a consequence summary) + an explicit route_to (roster-validated) + timeout_at
2. receiving a delivery_report with gaps (accountable unreachable) → notify immediately + proceed per timeout rules; never pretend it was delivered
3. after the human answers → write CAP-STATE (resolved + surface + timestamp) + derive follow-up actions; **an R6 answer carries a contract_snapshot** (C-2)
