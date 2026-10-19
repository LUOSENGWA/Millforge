## Governance: Voting / Ruling / Fuse (condensed load · full text = protocol §09-GOVERNANCE)

**Execution boundary**: vote counting/timeout/escalation triggering are all deterministic scripts (L2) — humans only provide the vote/ruling input; execution units only execute what the protocol computes. An LLM must never "compute the majority" on its own.

**R2/R5 weighted vote** (aggregate-vote): weight = role weight (owner/approver/informed), never model confidence; input = CAP-STATE attention.votes[] (state is authoritative, not the message stream); **a tie never re-votes** (escalate directly); **no vote ≠ consent**; the blocked state forbids abstention counting (defer counts into the denominator against passage).

**R5 reopening protocol**: must include new evidence + affected acceptance criteria; the original locker participates ×2; opposition with new evidence that does not touch the criteria → reopening fails. Locker timeout (B-4): irreversible 24h / reversible 4h; timeout = the ×2 weight is invalidated down to 1.0 (**not default consent**); late arrival → weight restored and recomputed; the old lock is kept, tagged "overridden by R5".

**R6 attention routing**: sent to the accountable (default: project owner; delegable; the delegation chain is queryable), CC approver (read-only, non-blocking). Timeout tiers: reversible 30min (abstention counts; majority stands, otherwise escalate); irreversible 2h (**blocking, never auto-passes** + notify owner). **Two conflicting answers**: if one is the accountable → that person wins (the other records dissent); equal weight with no accountable → escalate; **an execution-unit LLM must never summarize two human answers and pick one to execute**.

**Stall fuse (B-5)**: count open-attention timeouts (derived value): 1 = watch → 2 = **blocked** + escalate owner + abstention counting forbidden → 3 = **frozen** + explicit human unfreeze (no auto-recovery). Any human response → counter resets to zero.

**locked_spec_consistency_check (C-3, the most critical defense)**: a weighted majority can "legally by procedure" overturn a human-locked spec = the hole. Handling: **before** an R6 answer / majority result is written back, a mandatory consistency check: rule layer (mechanical judgment on structured fields) → contradict = reject + spec_conflict escalation chain ｜ undecidable → constrained LLM classification (fixed schema, hash-bound input) → neutral/untrustworthy = escalate to human. **No path may silently write; never auto-release.** Weighted majority is limited to R2/R4/R5 and is **never used for R6 on a locked spec**.

**State mapping (T3)**: protocol substates open/blocked/frozen/paused/spec_conflict overlay the runtime state machine (the upstream 9-state contract is untouched); blocked/frozen/paused/spec_conflict → runtime BLOCKED; open → unchanged. The sole authority for timeout decisions = task_meta's timeout_at/due_at (F-2); write confirmation (F-1): no merge/consume/accept before the CAP-STATE synchronous confirmation.

**Escalation chain**: ambiguity → R6 attention (30min/2h) → stall 2 → blocked → stall 3 → frozen, human unfreeze; tie/no majority/classification ambiguity → accountable → owner → human final ruling; contract major/irreversible timeout/irreparable side effect → straight to human. **Final ruling is always = human.**
