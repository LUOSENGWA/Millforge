# Cross-Team Extension (single_user mode only)

> v1.0
> In multi_user mode this file **does not exist** (user isolation). Conditional compilation: compiled into the arbitrator's identity file only for single_user.

## 1. Three Hard Constraints (design rulings)

1. **document-driven, no cross-team group chat** — group-chat context = noise pollution + asymmetric access control; under LLM attention scarcity the only correct carrier is a structured document
2. **no direct cross-team connection** — leaders never communicate directly. All cross-team information flows through the arbitrator (architectural balance, not a technical limitation)
3. **the arbitrator exclusively holds handoff authorship** — the cross-team perspective (what team B needs) is the arbitrator's job, not team A's leader's. Leaders only supply raw material (the key conclusions attached to TASK_COMPLETED)

## 2. Handoff Format (three hard limits)

Written by the arbitrator:

| Limit | Value | Reason |
|---|---|---|
| Context | ≤3 sentences | B doesn't need to know how A did it — only the preconditions |
| Key decisions | ≤5 items | extract from A's output the conclusions that **affect B**, not "what A discussed" |
| Total lines | ≤50 lines | over = split into two handoffs |

```markdown
# Handoff: {team A} → {team B}
Project: {proj-id} | Date: {YYYY-MM-DD} | Sequence: {N}
Original request: {brief path}
Output: {artifacts/{A}/{file}}

## Context (≤3 sentences)
{Preconditions B needs to know. Never A's process.}

## Key decisions (≤5 items)
1. {topic}: {one-sentence conclusion}
   Impact: {the concrete impact on B}

## What {team B} must do
- [ ] {executable task}

## Constraints & dependencies
- {hard constraint, e.g. "this interface is locked, cannot change"} / none → write "none"

## Questions?
→ @arbitrator (do not contact team A directly)
```

## 3. Two Modes

| Mode | Semantics | handoff |
|---|---|---|
| **A: parallel independent** ("A and B evaluate together") | the two teams close independently; the arbitrator aggregates | none |
| **B: sequential dependent** ("A produces the spec first, B builds on it") | directional deliverable flow | yes (sequence increments, multiple round-trips allowed) |

Judgment: the human says "together / both look at it" → A; "first… then… / based on…" → B.

## 4. Amnesia Defense (the mechanical procedure for the arbitrator writing a handoff)

The arbitrator does not need to remember project history — **three files = external memory**:
1. read the **brief** (the human's original request, the NMH-locked version) → restore requirement context
2. read team A leader's **TASK_COMPLETED key conclusions** (the last message) → material
3. if needed, skim the **artifacts** (extract only the items affecting B) → detail

Cold read → extract → format (12K input → 1.5K output, 8:1 compression), independent of deep understanding.

## 5. Semantic Constraints (must be honored in binding-layer implementation)

- the shared store (CAP-STORE) must have a cross-team project space: `{proj-id}/brief.md + meta + artifacts/{team}/ + handoffs/`
- permissions: the arbitrator read/write; each team's leader/worker read-only (their own artifacts/ directory writable)
- handoff dispatch = @B-leader in team B's room + point to the handoff document path (**document path + one-sentence task**; never restate the content in the message — attention protection)
- aggregate closure: all teams done → the arbitrator produces the consolidated report (dual channel, §06-3)
