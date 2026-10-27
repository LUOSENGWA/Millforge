## NMH Collaborative Exploration (condensed load · full text = protocol §04-NMH)

**Triggers** (any one → go through NMH, do not execute directly): the request contains planning/design/evaluation/migration/selection/comparison/refactoring/planning-type terms ｜ contains a hidden decision point ("optimize it" = optimize which dimension?) ｜ the human says "I'm not sure / what do you think?". When unsure = trigger (missed trigger = doing the wrong thing and redoing; false trigger = a few extra Q&A rounds).

**Dual mode**: explore (boundaries unknown: free Q&A + sketch the decision-tree skeleton; judge the human's knowledge depth and give explanations at the right level) → lock (≥3 nodes with no major unknowns: per node, present options + recommendation + rationale; the human nods). New unknowns found while locking → back to explore.

**Question format** (one at a time):
```
[D{n}] {topic} — options: A/B — recommendation: {X} (one-sentence rationale) — impact: {what goes wrong if wrong}
```

**Always use the structured channel** (otherwise the human side never shows a decision modal): every `[D{n}]` must call `taskflow` with `action: request_attention` — `kind: "decision"`, `question`: the question text, `options`: structured choices `[{id,label}]` (each with a consequence summary), `suggested`: the recommended option id, `expiresAt`: optional deadline. **Never ask only as chat text** — chat text never reaches the task meta, so the workbench modal cannot read it. After the human answers, close the same-kind record with `resolved: true`.

**Lock reaction table**: confirm ✅ / revise ✅ (revised version) / veto ✅ (new options) / park 🏳️ / you-don't-know 🏳️ (honest declaration, never fabricate). All ✅🏳️ = NMH complete.

**Seven questions before locking**: ① every node has an explicit human confirmation? ② contradictions between nodes? ③ any 🏳️ the human could actually decide that you didn't ask? ④ constraints entered into the tree? ⑤ known domain bottlenecks written as constraints? ⑥ all term conflicts unified? ⑦ could another Agent cold-read this tree and start working without asking anyone?

**Write to disk** (the file is the contract; even 10 lines gets written): decision tree (nodes + options + human's own words + timestamp) / constraints / term-alignment log / learning summary (next NMH reads the old doc, no re-teaching).

**Evolution**: append, never overwrite `[D{n}-e1]`; impact >3 nodes → new v2 (old version kept for audit).

**Forbidden**: locking on behalf of the human ｜ fabricating knowledge to fill 🏳️ ｜ starting production before lock ｜ verbal commitments (the file is the contract).

**Structured spec (mandatory output of locking)**: goal / acceptance[] ({id, check, pass_criteria}, machine-decidable preferred) / out_of_scope / decision_class / contract_refs / critical_delivery.
