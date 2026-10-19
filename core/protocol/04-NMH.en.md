# NMH: Human↔Agent Collaborative Exploration Protocol

> v1.0 | Provenance: NMProtocol §5 (full text of the internal NMH v2.46 protocol, runtime-specific weaving stripped)
> **In one sentence**: what the human gives is a direction, not a requirement. NMH is the process in which the human and the agent turn a fuzzy direction into a **locked decision tree**, and simultaneously the human's learning channel.
> **Design provenance**: the core grilling mechanism (branch-by-branch decision-tree interrogation, one question at a time, recommended answers, terminology alignment, inline write-to-disk, restrained escalation) is verbatim-inherited from the QwenPaw community skills `grill-me` / `grill-with-docs` — see [../../ACKNOWLEDGMENTS.md](../../ACKNOWLEDGMENTS.md) §1 for the point-by-point mapping (originals archived at `docs/provenance/grill/`). The explore/lock dual mode, the seven-question self-check, and the structured spec output are Millforge extensions.

## 1. Trigger Rules

**Core rule: whoever receives the human's message invokes NMH — it is about the person, not the role.**

**Mandatory triggers** (any one):
- the request contains planning/design/evaluation/migration/selection/comparison/refactoring/planning-type terms
- the request contains a hidden decision point ("optimize it" — optimize which dimension? where is the boundary?)
- the human proactively says "I'm not sure / what do you think / are there alternatives?"

**No trigger** (execute/answer directly): simple query / an explicit instruction with the triad complete / status query / pure confirmation.

**Trigger-misjudgment costs are asymmetric**: should-have-triggered but didn't = the whole task goes sideways (rework); triggered when it shouldn't = a few extra Q&A rounds (waste). When unsure → trigger.

## 2. Dual-Mode Dynamic Switching

| Mode | State | Behavior |
|------|------|------|
| **Explore** | requirement boundaries unknown | no fixed decision points. Free Q&A + knowledge sharing, sketching the decision-tree skeleton as you talk. Judge the human's knowledge depth and give explanations at the right level (never assume "the human doesn't understand" and never assume "the human understands everything") |
| **Lock** | decision-tree skeleton clear (nodes ≥3, no major unknowns) | lock node by node: options + recommendation + rationale; the human confirms / amends / vetoes |

The modes are not a hard state-machine switch — a new unknown found while locking → back to explore.

## 3. Phase 1: Comprehension

1. **judge knowledge depth**: from wording and past interactions (read the learning summary in the old NMH document) → decide explanation depth
2. **read existing files**: existing decision trees, handoffs, charter in this domain — don't re-ask what is already locked
3. **terminology disambiguation**: when ambiguity is detected, call it out on the spot, unify it, and record it in the terminology-alignment log
4. **sketch the decision points**: 3–8 decision points, marked with dependencies
5. **self-check**: are there decision points in the skeleton that **I don't know**? (🏳️ candidates)

## 4. Phase 2: Interaction Loop

**Question format (per decision point)**:

```
[D{n}] {decision topic}
  Options: A: ... / B: ...
  Recommendation: {A/B} — rationale: {one sentence}
  Impact: {what goes wrong if it's the wrong pick}
```

**drill-deeper conditions** (if the reply satisfies none of these → follow up, max two rounds): not all options covered / a new term introduced / conflicts with a locked node.

**Discipline**: one question at a time (explore mode is the exception — you may ask in sequence, but each question stands as its own paragraph). Never decide for the human — recommendations are allowed; locking requires the human's nod.

## 5. Phase 3: Pre-Lock Self-Check (Seven Questions)

1. Does every decision point have an explicit human confirmation? ("mm-hm" counts; record the original words)
2. Are there contradictions between decisions?
3. Is there a decision point I 🏳️'d that the human could actually rule on but I never asked?
4. Are the constraints (budget / time / compatibility) all in the decision tree?
5. Are the domain-specific known bottlenecks / historical lessons all written in as constraints? (the binding layer injects this instance's list at compile time)
6. Does every conflict in the terminology-alignment log have a unified conclusion?
7. If tomorrow another agent cold-reads this decision tree, could it start executing without asking anyone?

## 6. Phase 4: Write to Disk

The decision tree is written to the **NMH document** (path defined by the binding layer), format:

```markdown
# {requirement topic}
Status: 🔓 exploring / ✅ locked
Date: YYYY-MM-DD
Participants: {human} ↔ {agent}

## Decision Tree
[D1] {topic}
  Options: ...
  Lock: {human's choice + original words} (timestamp)
[D2] ...

## Constraints
- {hard constraint}

## Terminology Alignment Log
| Term | Human meaning | Agent understanding | Unified |

## Learning Summary
- domain knowledge shared: {what the agent shared}
- human's questions: {revealed knowledge gaps}
- human's comprehension: {judgment}
- can skip next NMH: {already understood}
```

**Use of the learning summary**: next time this same human runs NMH, read the old document — no re-teaching. The protocol-layer minimal implementation of the learning loop.

## 7. Locking Rules (Reaction Table)

| Human reaction | Node state | Action |
|-----------|---------|------|
| confirm ("go with A" / "ok") | ✅ locked | record original words + timestamp |
| amend ("A but X needs changing") | ✅ locked (amended) | record the amendment |
| veto ("neither; it should be C") | ✅ locked (C) | record; check downstream node dependencies |
| park ("let's leave this for now") | 🏳️ | explicit parking; annotate the escalation path for when it must be handled during execution |
| agent doesn't know | 🏳️ | honestly declare the knowledge boundary; never fabricate. Annotate "needs human or external information" |

**All nodes ✅ or 🏳️ (no 🔓) = NMH complete.**

## 8. Concurrent NMH

Multiple NMHs on the same agent simultaneously → each is its own document, its own state. The human switches topics → the current NMH is marked "suspended" (not cancelled); the new topic gets a new document.

## 9. Evolution (mutable after locking)

Locking ≠ freezing. Evolution = **append, never overwrite**: `[D{n}-e1] {new constraint} (timestamp, trigger reason)`

- **trigger**: a new constraint found during execution / the human has a new idea / external conditions change
- **linkage**: affected downstream nodes return to 🔓 and need re-confirmation
- **boundary**: affects 1–2 nodes → evolution; affects >3 nodes or changes the core direction → create a v2 document (the old document is kept as an audit record)

## 10. Post-Lock Flow

The NMH output (the locked decision-tree document) = the input of the task lifecycle (§06-LIFECYCLE):
- single team: decision tree → leader decomposes and dispatches
- cross-team (single_user only): decision tree + requirement brief → §07-HANDOFF

**The protocol guarantees only**: the locked decision tree exists as a file (CAP-STORE), and the first input the next layer receives is it.

## 11. Forbidden / Required

- ❌ never lock on behalf of the human (recommendations are allowed; the nod must be the human's)
- ❌ never fabricate domain knowledge to fill a 🏳️ node
- ❌ never start execution before locking (exploration may verify in small steps; deliverables must wait for the lock)
- ✅ every NMH produces a document (even 10 lines) — the file is the contract
- ✅ the learning summary is mandatory (the minimal duty of the learning loop)
- ✅ **spec structuring**: the spec locked by NMH must contain `goal / acceptance[] (structured acceptance_criteria) / out_of_scope / decision_class` (§08-CONTRACT) — natural-language acceptance is the zone the C-3 consistency check cannot mechanically judge; structured fields let the rule layer decide mechanically
