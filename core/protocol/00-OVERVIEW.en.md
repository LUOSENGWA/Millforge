# Millforge Protocol Overview

> Version: v1.0 (frozen protocol-layer baseline, 2026-10-19) | License: Apache-2.0
> Provenance: NMProtocol design v3.0 (semantic base) + eight-round DeepSeek review (2026-10-17~19, fully adopted)
>
> **Generic-terminology discipline (core-layer iron rule)**: this directory (including schemas/, invariants/, scripts/, compiler/, templates/, golden-tests/)
> admits only **CAP-\* capability numbers + generic terms** (subagent, parent execution unit, main session, persistent display surface, runtime scheduler,
> object storage, notification channel, decision log, state store, timer). Runtime-specific API names (spawn_subagent, QwenPaw cron,
> channels send, mc, specific dashboard components, Matrix, MinIO/RustFS, etc.) **may only appear in the `bindings/` layer**.

## 1. Positioning

Millforge is the **protocol layer for multi-agent collaboration**: a runtime-agnostic semantic contract + a deterministic execution implementation + a compiler.
Runtimes (TeamHarness, bare QwenPaw, claude-code, etc.) bind through the 8-capability declaration in `binding-contract.md`;
the protocol does not depend on any specific runtime existing.

## 2. Design Principles (non-negotiable)

| # | Principle |
|---|------|
| P1 | **Attention scarcity is the core of the system** — not too little information, but too much noise. Even a 1M context forgets. Cross-layer information moves via files/references, never via conversational context |
| P2 | **The file is the contract** — never rely on an agent "remembering what was said"; rely on what was written to a file. Verbal commitments do not exist in the protocol |
| P3 | **Declaration–verification binding** — before any "done/sent/created" claim, a corresponding tool call must already have succeeded within the same turn. Text output and tool calls are two channels |
| P4 | **The lower the constraint, the more reliable** — code-level hard constraints (capability gating) > deterministic scripts > behavioral soft constraints. Use the lower layer whenever possible |
| P5 | **Layered reliability** — every rule must be tagged with its layer (L1 platform-builtin / L2 deterministic script / L3 behavioral). System correctness may depend only on L1/L2; L3 is quality enhancement only |
| P6 | **Capacity ≠ attention** — attention over long context is U-shaped; resident content is under hard line budgets, cold paths load on demand |
| P7 | **Minimize custom glue** — reuse every mechanism the platform already has; custom components must be able to answer "why doesn't the platform have this?" |
| P8 | **The protocol is a compiled artifact, not a handwritten draft** — agent SOUL/identity files are compiled from templates + instance parameters; the LLM may only contribute bounded, validated, human-visible fields. Same input, same output — otherwise standardization dies |

## 3. Document Map

| File | Content |
|------|------|
| 01-PRIMITIVES | 15 primitives + role invariants |
| 02-MODES | deployment modes (single_user / multi_user phase transition) |
| 03-DECISIONS | decision classes R1-R6 + decision_log + type closure (B-1/B-10/C-1) |
| 04-NMH | human↔agent collaborative exploration protocol |
| 05-NMA | peer review protocol + multi-critic voting (MC-1~10) |
| 06-LIFECYCLE | task lifecycle contract (recursive decomposition / completion signal / dual channel / failure SOP / fuse) |
| 07-HANDOFF | cross-team extension (single_user only) |
| 08-CONTRACT | contract pinning + structured spec (B-3/C-2/B-9) |
| 09-GOVERNANCE | voting / ruling / state mapping (B-4/B-5/B-8/C-3) |
| 10-LOOP | Loop primitive (14th primitive) |
| 11-SIGNAL | signal primitive (15th primitive) |
| 12-REDLINES | redlines + reliability layering + attention loading |
| ../binding-contract.md | 8-capability interface (CAP-STATE/STORE/TIMER/NOTIFY/ATTN/SPAWN/EXEC/ROSTER) |
| ../schemas/ | JSON Schemas (10) |
| ../invariants/ | state-machine invariants |
| ../scripts/ | 8 deterministic scripts + timer-derive (deterministic implementations of protocol semantics) |

## 4. Versioning

- semantic change = minor; primitive add/remove / mode definition change = major
- bindings version independently, declaring "compatible with Millforge v1.x"
- old version documents are archived, never deleted (audit chain)
- the protocol_version field appears in spec/loop_spec/decision_log and other structured objects; upgrades are never silent

## 5. What We Don't Do (boundaries)

- no framework code modification — the protocol is an overlay; framework bug found → upstream issue + PR
- no new storage engine — the file is the database (carried by CAP-STORE)
- no automatic merge/conflict resolution — locked = immutable; conflicts go to ruling/escalation
- no forced structuring of all communication — everyday conversation needs no protocol
- no cross-user team communication (multi_user) — isolation is a design, not a defect
- no frontend visualization design — protocol output is the data source for visualization; the frontend is a separate project
- no real-time driving via timers/heartbeats — timers are for fallback recovery only; real-time driving uses event triggers + state-machine side effects (L1/L2)
