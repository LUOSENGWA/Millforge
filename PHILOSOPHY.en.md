# Millforge Design Philosophy (PHILOSOPHY)

> This file is the "why" behind every Millforge design decision. It has two uses:
> 1. **Read** — understand the constraints behind each clause of protocol layer v1.0, instead of memorizing rules.
> 2. **Second-order generation** — copy this file in full + describe your team (members / task types / runtime / pain points), feed it to any LLM, and it can generate your `team.json` instance or a custom industry template. This is the fallback channel for cases the template library does not cover.
>
> This file is frozen in sync with the protocol layer; changing it = changing Millforge's worldview, and requires full review.

---

## 1. Core Worldview: LLMs Are Message-Driven, Not Flow-Driven

An agent has no muscle memory for "I'm on step 3." Each turn, the LLM sees the current context + one new message; "what I was about to do last turn" decays as context scrolls. **Any flow that depends on "remembering to continue" breaks after ~20 turns.**

Three axioms follow:

1. **State externalized**: flow state must live in files (decision state / next action / pending signals). Every turn starts by reading state before reading the message. Messages may be lost; state must not.
2. **Declaration–verification binding**: text output and tool calls are two independent channels. "Done" is text; "tool call succeeded" is fact. The protocol must enforce: before saying X, the tool evidence for X must already have appeared in the same turn.
3. **Attention budget is a hard constraint**: 1M context capacity ≠ 1M attention. LLM attention over context is U-shaped — high at the start and end, low in the middle; after several turns, rule documents are pushed far into the distance. **Capacity ≠ attention.**

## 2. Attention Economics (Millforge's most important engineering judgment)

The cost bottleneck of a multi-agent system is not token money — it is **attention**. Every execution unit has a limited effective attention budget per turn, and every protocol mechanism competes for it:

- **Three-layer loading**: layer 0 resident (identity file, hard line budget ≤500 lines, only "what you need every turn"); layer 1 trigger-loaded (full protocol text; one-line trigger condition, full text read on demand from files); layer 2 spawn-injected (domain specs enter context only at sub-execution-unit start, destroyed on use).
- **The file is the contract**: information across roles/turns/teams always moves by file reference (path + fingerprint), never by message restatement. Group-chat history is noise, not context.
- **Hard line budgets**: an identity file over budget = compile failure, never truncation. Truncation = silent rule loss, which is more dangerous than failure.
- **Hard limits on short deliverables**: TASK_COMPLETED must carry 3–5 key conclusions (a three-sentence summary at completion costs nothing; reconstructing it later is impossible); cross-team handoff ≤50 lines (8:1 compression). **Raw material extracted at the right moment is more reliable than later recall.**

## 3. Checks and Balances: Verifier ≠ Declarer

LLMs confidently claim completion. Single-point trust in any party's self-report = systematic lying risk. Millforge's balance structure:

- **Role separation**: the coordinator does not implement, the leader does not code, workers do not dispatch to peers, the critic only reviews and never executes. Every role has a "must not" list, and violating it = protocol violation (auditable).
- **Independent acceptance**: acceptance happens in a fresh context (the critic spawn does not inherit the reviewed party's conversation history). Acceptance evidence = command output / file content / reproducible checks — never "looks right."
- **Human final ruling**: disputes / deadlocks / irreversible decisions — final authority always rests with the human (a single accountable owner). Weighted voting applies to resource-class decisions only, **never** to overturning a human-locked spec.
- **Closed signal set**: completion / decision / acceptance states are expressed with 7 closed markers, produced by event type — never by content, and an execution unit can never self-award one. Acceptance may cite only marked signals + artifact references — **"I'm done" in group chat does not count.**

## 4. Decision Grading: Reversibility Determines Process Weight

Not every decision deserves a heavyweight process. Six grades (R1–R6) by **reversibility × impact**:

| Grade | Examples | Process |
|:--:|------|------|
| R1 | deploy to production / delete artifact / send externally / merge main | single-point decision + human confirmation (irreversible, human final ruling) |
| R2 | new execution unit / long task / external spend | weighted vote (resource class) |
| R3 | naming / format / wording | executor decides; objections go through review |
| R4 | internal implementation detail | auto-pass + logged |
| R5 | overturning a locked decision | explicit reopening protocol (new evidence + affected criteria) |
| R6 | requirement ambiguity / permission boundary / trade-off | escalate to the human accountable (attention routing) |

**When unsure, go one grade up** (reversibility in doubt = treat as irreversible). Grades are also instance parameters — teams can tune them to their risk appetite.

## 5. Failure SOP: The Orchestrator Never Does the Work

When a worker dies (error / context overflow / no response), the orchestrator's instinct is "I'll just do it myself." This is **the most dangerous overreach**: it breaks role separation, and the orchestrator's context lacks the execution context, so the quality of what it produces is uncontrolled. Fixed SOP:

```
Stop hands (never open the artifact and do it yourself) → restart that worker → re-dispatch unchanged → still failing after 3 attempts → escalate to human (attach the three attempt records)
```

Quality problems ≠ failure → go through the review chain (NMA); do not restart. **Every failure-recovery step has an explicit criterion; there is no fuzzy "something feels off" space.**

## 6. Modes: single_user vs multi_user

- **single_user** (one human owner + multiple teams): cross-team information moves via structured handoff documents (the coordinator exclusively holds handoff authorship; leaders only supply TASK_COMPLETED key-conclusion raw material); **cross-team group chat is forbidden** (attention scarcity + no shared context).
- **multi_user** (multiple human users sharing a cluster): no cross-team layer; user isolation (per-user shared space / project rooms); compiled output contains no handoff fragment.

**The two modes differ not in a configuration switch but in the compiled target tree** — the compiler selects different template sets and fragment loading per mode.

## 7. Protocol Freeze & Template Three-Tier

The protocol layer (13 documents) is a **frozen baseline**: changes require review (multi-round review by external strong models + full adoption record), never casual edits. The template layer follows three-tier source discipline:

- **production**: production-validated instances (compilable regression baselines)
- **reference**: derived from production (derivation source annotated)
- **llm**: LLM-generated fallback (compiled output carries the EXPERIMENTAL badge; promoted only after human confirmation)

**How a new industry template is born**: a production team gets it running → extract industry constraints → human review → enter the library (source promotion). The template library is **grown**, not designed.

## 8. Generic-Terminology Discipline (the foundation of open-source reuse)

The core layer admits only **capability numbers (CAP-STATE/CAP-STORE/CAP-NOTIFY…) + generic terms** (subagent / object storage / notification channel / timer). Concrete runtime-specific APIs (each runtime's spawn tool name / cron mechanism / MQ implementation) all belong to the **binding layer**:

- a binding = the adaptation doc for "how a CAP-* capability is implemented on your runtime" + known issues + deployment steps
- changing runtime = changing binding; zero protocol-layer change
- the open-source baseline therefore **carries no deployment environment names / human identifiers / internal incident numbers** (scrub vocabulary CI gate)

## 9. Determinism: the Compiler Is the Last Line of Defense

Protocols can be miswritten, LLMs can forget — but **the compiler does not**. All 6 pipeline stages are deterministic (zero LLM): Validate (schema + cross-checks) → Assemble (template assembly) → Budget (hard line gate) → Render (placeholder rendering, zero residue) → SelfCheck (scrub / pointer integrity / badges) → Provenance (version + fingerprint + instance fingerprint).

- same input, same output (byte-identical golden regression)
- frozen baseline gate: any drift in output from a change requires explicit re-freeze + human review
- production traceability gate: every production protocol clause maps back to a frozen-protocol landing point — **upgrades lose no semantics**

## 10. The Second-Order Generation Prompt for LLMs (the primary use of this file)

When the template library does not cover your industry / team shape:

```
You are the frontend of the Millforge protocol compiler. Below is the full
Millforge design philosophy (PHILOSOPHY).
My team's situation:
- Members: {N agents + role division}
- Task types: {…}
- Runtime: {AgentTeams / QwenPaw / Claude Code / other}
- Top 3 pain points: {…}
Generate:
1. A valid team.json (strictly following the field semantics of Millforge's
   team.schema.json; decision-grade / budget / protocol-switch values must
   cite the axioms in this file as justification)
2. (If the industry template is missing) an industry template draft
   (≤60 lines, each constraint verifiable, no copying from other industry
   templates, marked source: llm pending human review)
Constraints: do not introduce mechanisms this philosophy does not cover;
when unsure → mark "needs human confirmation" instead of guessing.
```

---

*Millforge = a thousand hammers, a thousand forgeings. The protocol is forged, not written.*
