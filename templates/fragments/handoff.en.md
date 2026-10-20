## Cross-Team Handoff (condensed load · full text = protocol §07-HANDOFF · compiled for single_user only)

**Three hard constraints**: ① document-driven, never a cross-team group chat (attention is scarce; the only correct carrier = a structured document) ② no direct cross-team connection (leaders never communicate directly; information flows through the arbitrator) ③ **the arbitrator exclusively holds handoff authorship** (leaders only supply raw material = TASK_COMPLETED key conclusions).

**Three hard limits**: context ≤3 sentences ｜ key decisions ≤5 items ｜ total ≤50 lines (over = split into two).

**Format**:
```markdown
# Handoff: {A} → {B} | project {proj-id} | date | sequence {N}
Original request: {brief path} ｜ Output: {artifacts/{A}/}
## Context (≤3 sentences) — preconditions B needs; never A's process
## Key decisions (≤5 items) — each: topic: one-sentence conclusion + impact: concrete impact on B
## What {B} must do — an executable task list
## Constraints & dependencies — the authoritative source for contract-surface decisions; none → write "none"
## Questions? → @arbitrator (do not contact team A directly)
```

**Modes**: A parallel-independent (no handoff; arbitrator aggregates) ｜ B sequential-dependent (handoff sequence increments; multiple round-trips allowed).

**Amnesia defense (the mechanical procedure for writing a handoff)**: cold-read three files = brief (recover the request) + TASK_COMPLETED key conclusions (material) + artifact scan if needed (extract only what affects B) → extract → format (12K→1.5K, 8:1 compression). **Depends on neither memory nor deep understanding.**

**Dispatch**: in B's room @B-leader + point to the handoff document path + one-sentence task. **Never restate content in the message** (attention protection).

**Reflow (full-tier loop)**: ≤{{max_reflow}} full reflows consuming the shared budget pool; the same criterion with the same fingerprint 2 consecutive times = semantic stall, terminate immediately and escalate.

**Permissions**: shared space {proj}/brief.md + meta + artifacts/{team}/ + handoffs/; the arbitrator reads/writes, each team read-only (may write its own artifacts).
