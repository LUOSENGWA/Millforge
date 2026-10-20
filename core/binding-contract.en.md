# Millforge Runtime Binding Contract (8 Capabilities)

> v1.0 (frozen protocol-layer baseline)
> **Positioning**: this file is the sole "capability interface" the Millforge protocol layer requires of any runtime.
> **Binding layer = runtime-specific implementation**, which must explicitly declare which of the following 8 capabilities it implements.
> A binding not satisfying a capability = **illegal binding** (that capability's protocol clauses automatically degrade to "unsupported", and the binding must declare this in its README).
>
> **Generic-terminology discipline**: the core layer admits only "capability numbers (CAP-*) + generic terms". Concrete runtime API names (spawn_subagent / QwenPaw cron / mc / channels send / specific dashboard components / Matrix / MinIO) **may only appear in this file's "reference mappings" tables and in each bindings/ implementation document**.
>
> **Layering discipline (P5)**: every capability has a "reliability tier" — the binding must state which tier its implementation lands in (L1 platform built-in / L2 deterministic script / L3 behavioral). **System correctness may depend only on L1/L2**; L3 is a quality enhancement only.

---

## Design Principles

1. The core never references concrete components — only CAP-* ids and invariants.
2. Capabilities are a **minimal set**, not a maximal one — a runtime may offer more; the core depends only on the following 8.
3. Every capability must declare its invariants — **an invariant violation = an illegal binding**, not an "implementation difference".

---

## Capability List

| CAP | Capability | Mandatory for | One-line semantics |
|-----|------|-----------|---------|
| CAP-STATE | durable state read/write | ✅ | structured state persistence + CAS + append-only history |
| CAP-STORE | artifact store | ✅ | file write/read + ref + fingerprint |
| CAP-TIMER | timer | ⚠️ soft-mandatory | one-shot / period + dedup + idempotent derivation |
| CAP-NOTIFY | notification channel | ⚠️ soft-mandatory | message send (room/DM) + delivery evidence |
| CAP-ATTN | human attention request | ⚠️ soft-mandatory | idempotent + reply persistence + timeout + trusted identity |
| CAP-SPAWN | sub-execution unit | ✅ (worker present) | X1 fresh context + X2 structured return + X4 boundedness (mandatory for loop) |
| CAP-EXEC | command execution | ⚠️ soft-mandatory | verifiable command execution (NMA 🔵/🟢) |
| CAP-ROSTER | stakeholder registry | ⚠️ soft-mandatory | roles/weights/delegation query |

**Mandatory for** = a binding lacking it cannot be a legal binding (except for the pure "human-only mode" degeneration, which must be explicitly declared).

---

## CAP-STATE — Durable State Read/Write

**Semantics**:
- read/write a **structured state record** (task meta / decision record / loop state / attention entry)
- **CAS** (compare-and-set, optimistic concurrency control)
- **append-only history** (never overwrite; every change leaves a trail)
- **idempotent write** (the same logical write repeated does not duplicate)
- the write has a **synchronous confirmation** (a write-confirmation point: "written and readable by others")

**Sub-requirements**:
- S1 record = versioned JSON (a version field or an append sequence)
- S2 write returns a confirmation result (not fire-and-forget)
- S3 CAS failure returns the current value (not silent failure)
- S4 append-only: the read interface is immutable (historical versions are queryable)
- **T1 single clock source** (all timestamps from the same clock, for causal order)
- **T2 write confirmation** (the write must have a confirmable point; a write without confirmation is treated as unexecuted — **no merge/consume/accept may be triggered before the confirmation**)
- **U1 clock-source unification**: state timestamps (T1) and timer scheduling (CAP-TIMER) derive from the **same clock source**; the protocol requires only "same clock source", not a specific implementation

**Deterministic implementation requirement (P4)**: the protocol layer's **timeout judgment / vote counting / conflict detection** must be **scripts (L2)** reading state and deriving — not "the agent remembering to compute." The binding declares the script's trigger mechanism (external scheduler).

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams (TeamHarness) | project/task meta + decision_log ref in object storage; external one-shot timer (runtime cron) | L2 |
| Bare QwenPaw | workspace JSON state file + git-like append log; runtime cron + HEARTBEAT | L2/L3 |
| claude-code | task file + CLAUDE.md pointer; Task tool + ScheduleWakeup | L2 |

---

## CAP-STORE — Artifact Store

**Semantics**:
- **write / read / list** of files (artifacts / decision_log / NMH documents / contract objects)
- a **path contract** (a stable, predictable path for every kind of artifact)
- **ref** (a reference that can be carried in a message and re-read later)
- **fingerprint** (content hash; tamper evidence)
- **immutability** (an accepted / accepted-for-acceptance artifact is never overwritten; new version = new path)

**Sub-requirements**:
- T3 immutability (optional but recommended): the accepted artifact is frozen; changes produce a new version
- T4 path contract: `<root>/<kind>/<id>...` (kind ∈ artifacts/decisions/nmh-docs/contracts/…)
- **U2 object-storage fingerprinting**: the fingerprint algorithm must be declared (e.g. sha256-8); different binding implementations may differ, but **must be consistent within the same binding**
- **F1 write confirmation** (aligns with CAP-STATE T2): an object write must have a synchronous confirmation (read-back or a write-ack from the storage layer); **a merge/consume/acceptance must not occur before the confirmation**
- **F2 idempotent derivation**: timeout / budget decisions are derived from the state's timestamp fields (the source of truth); timer caches only notify, they do not decide — repeated derivations are idempotent

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | MinIO (object storage, `mc` CLI) + per-team bucket | L1 |
| Bare QwenPaw | workspace directory + a file-sync mechanism (declared) | L2 |
| claude-code | the repo's files/ directory + git (the fingerprint = git hash) | L1 |

---

## CAP-TIMER — Timer

**Semantics**:
- **one-shot / periodic** trigger
- **dedup** (the same trigger key repeated does not fire twice)
- **idempotent derivation** (a timer fires = "go read the state and re-derive next_action", never "directly perform X")

**Sub-requirements**:
- T5 the trigger payload must be **self-contained** (it cannot assume the receiving session still remembers the context)
- T6 dedup key = `hash(task_id + trigger_kind + due_at)`
- **U1** shares a clock source with CAP-STATE
- **F2 idempotent derivation**: the timer is a **notification**; the **judgment** comes from reading CAP-STATE (timeout_at / budget) and re-deriving. **The timer itself does not carry a judgment conclusion** (it may carry a "please derive" hint, but the derivation must be done by the script/driver)

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | runtime cron (a one-shot job per timeout; text self-contained) | L2 |
| Bare QwenPaw | runtime cron + HEARTBEAT (fallback period 10–30min) | L2/L3 |
| claude-code | ScheduleWakeup / loop scheduling | L2 |

**Degradation rule**: a binding without a CAP-TIMER must implement "external polling fallback" (a watchdog reads CAP-STATE on a fixed period) and declare it; a pure L3 "the agent remembers to remind itself" is **not** a legal implementation.

---

## CAP-NOTIFY — Notification Channel

**Semantics**:
- send a message to a **room / DM / originating channel**
- **delivery evidence** (send success ≠ the other side read it; a delivery report is required)

**Sub-requirements**:
- T7 the message carries a routing hint (to whom / to which room)
- T8 a delivery report (delivered / read / failed) — at least "send-confirmed"
- **U3 channel declaration**: which channels exist (project room / DM / originating channel) and their relative positions are declared by the binding
- **F1 write confirmation** (aligns with the dual channel): **the delivery of the originating-channel notice is an L2 mechanism** (CAP-NOTIFY delivery_report); the report's **content generation** is L3 — what is lost can be rebuilt from CAP-STATE; never rely on "remembering to send"

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | Matrix room / DM (channel send) | L1 |
| Bare QwenPaw | channels send (DM) + room @mention | L1/L3 |
| claude-code | the Task result message + the parent session | L1 |

---

## CAP-ATTN — Human Attention Request

**Semantics** (the 13th primitive's runtime support):
- create a **human-attention request** (R6 decision / escalation / clarification)
- **idempotent** (a repeated request for the same decision does not duplicate)
- **reply persistence** (the human's reply enters CAP-STATE and is auditable)
- **timeout** (two-tier: reversible / irreversible; aligned with CAP-TIMER)
- **trusted identity** (only a human's confirmed reply counts; an agent cannot self-resolve)

**Sub-requirements**:
- W1 idempotency key = `hash(task_id + decision_node_id + decision_hash)` (W7 extension: include `responder_id + action` for a resolve)
- W2 the reply must be written to CAP-STATE (the reply itself carries an audit record: who / when / which option)
- W3 timeout = the timeout_at field in CAP-STATE + a CAP-TIMER derivation (the request does not hold its own timer)
- W4 trusted identity: the request may only be resolved by a **human** (roster role = human)
- **W5 persistent display surface**: every attention request must have at least one persistent display surface (a display that persists until timeout, is actively revisitable, and has identity-verified replies); **a group chat is not a persistent display surface**; a channel with trust below the persistent-surface requirement may only notify, not resolve (S4)
- **W6 multi-surface close**: a request may be presented on multiple surfaces; any one surface's resolve → the others close (polling/event sync); the close is a **view behavior**, not a state write (the authoritative state is still in CAP-STATE)
- **W7 structured resolve**: when kind=decision + options, the resolve response must carry back the **option_id** (structured); a free-text choice is rejected (idempotency key = `hash(task_id + request_id + responder_id + action)`)
- **F1 write confirmation**: the human's reply enters CAP-STATE only **after the write confirmation**; subsequent actions (reclassification / re-voting) must not begin before the confirmation
- **F2 idempotent derivation**: the timeout verdict (reversible 30min / irreversible 2h / R5 24h/4h) is derived from the timeout_at/due_at fields (the source of truth); the timer only notifies, the script decides

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | Matrix DM @human + runtime one-shot timer | L2 |
| Bare QwenPaw | DM channel + HEARTBEAT fallback + runtime cron | L2/L3 |
| claude-code | the parent session's AskUserQuestion (a persistent display surface; group chat does not apply) | L1 |

**Persistent-surface examples** (W5, non-normative): IM private chat with a bot, a dashboard todo list, a dedicated approval page, a console interactive prompt. **Group-chat @mention is not one** (buried in messages, not revisitable, identity unreliable).

---

## CAP-SPAWN — Sub-Execution Unit (worker's implementation unit)

**Semantics**:
- X1 **fresh-context** sub-execution unit (isolated from the parent's session history)
- X2 **structured return** (the result is a parseable structured object, not free text)
- **X4 boundedness (mandatory)**: a spawn must declare a **bounded return within a deadline** — a structured result or a bounded failure `{bounded_failure: true, reason, partial_refs?}`; a spawn that hangs / overruns / returns unparseable text is treated as bounded_failure

**Sub-requirements**:
- X3 the spawn's input = a **spec reference** (context_refs), not a long text inlined in the message
- X5 the spawn's context_refs may contain **only marked signals + CAP-STORE artifact refs** (§11-SIGNAL effect 1)
- X6 a spawn's decision_log (if any) is written to CAP-STORE + fingerprinted (S2); the message carries only the ref
- **X4a** the deadline is declared at spawn creation (aligned with CAP-TIMER / task timeout); the deadline is the spawn's own bound, not an external watchdog
- **X4b** the return must conform to a declared return schema (validated by the structured-return validation; schema violation = bounded_failure)
- **X4c** a runtime that does not satisfy X4 is **not a legal binding** for loop / acceptance flows (otherwise iteration_budget and CAP-TIMER become meaningless)

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier | X4 |
|---|---|---|---|
| QwenPaw (bare) | `spawn_subagent` (fork=False; background=false) | L1 | ✅ (a versioned 3600s hard deadline — the runtime enforces it; the binding must state the version) |
| AgentTeams (Worker) | Worker = a CAP-SPAWN instance (the runtime schedules the worker container) | L1 | ✅ (the runtime's task timeout; the binding must state it) |
| claude-code | the `Task` tool (subagent) | L1 | ⚠️ (the Task tool has no built-in deadline; the binding must supplement a deadline via ScheduleWakeup + state derivation; **the supplement must be deterministic (L2), not behavioral (L3)**) |

**Worker context isolation (a protocol-level requirement on the CAP-SPAWN user)**: the worker's native session does scheduling + acceptance only; **all implementation work must go through a CAP-SPAWN sub-execution unit** (reads context from files, writes outputs to files, destroyed). This is a **protocol rule**, not a binding feature — but the binding must provide the means for it.

---

## CAP-EXEC — Command Execution (NMA verification)

**Semantics**:
- execute a **verifiable command** (shell / grep / curl / API call / test)
- return **command + output + exit code** (evidence)

**Sub-requirements**:
- E1 the execution environment is declared (which machine / container / sandbox)
- E2 the output is persisted (written to CAP-STORE or inline; evidence is auditable)
- E3 timeout bound (a command cannot hang forever)

**Isolation boundary (NMA)**: the executor cannot run inside the **reviewed party's workspace** (cross-container / cross-workspace is unreachable) — 🔵 items are limited to externally verifiable surfaces (API / object storage / public docs).

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| QwenPaw (bare) | execute_shell_command (container-local) | L1 |
| AgentTeams | worker container shell + docker exec (host) | L1 |
| claude-code | the Bash tool (sandboxed) | L1 |

---

## CAP-ROSTER — Stakeholder Registry

**Semantics**:
- register **stakeholders** (humans + agents) with **role / weight**
- **accountable query** (who is accountable for this task/project/loop)
- **delegation chain** (who delegated to whom; queryable)

**Sub-requirements**:
- Z1 weight = role-based (owner/approver/informed × value), never model confidence
- Z2 a single accountable per task/loop/decision (exactly one; no collective)
- Z3 the delegation chain is queryable (a delegation record with timestamps)

**Reference mappings** (non-normative):

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | the team roster in object storage (team.json / agent config) | L2 |
| Bare QwenPaw | workspace roster file (roster.json) | L2 |
| claude-code | a project-level roster file | L2 |

---

## Security Redlines (cross-capability, S1-S5)

See `protocol/12-REDLINES.md` §1 (artifact data redlines / decision_log anti-forgery / contract dual confirmation / group chat is not a response surface / replay protection) — all five are execution details of the CAP interfaces; violating any = an illegal binding.

## Binding Legality Determination

A runtime is a **legal binding** if and only if:
1. all 8 capabilities are implemented and all invariants hold (X1/X4 are hard gates);
2. it provides CAP-EXEC able to run `core/scripts/` (or declares an equivalent implementation that passes the golden tests);
3. it declares: runtime version matrix / primitive mapping table (every §01 primitive → concrete mechanism) / mode matrix / timer granularity / persistent display surfaces;
4. it passes the `golden-tests/` regression (L5).

## Binding Declaration Format

A binding's README **must** contain:

```
## Capability Declaration (CAP-*)
| CAP | Implemented | Tier (L1/L2/L3) | Mechanism (concrete runtime API) | Limitations |
|-----|-------------|------------|-------------------------|------|
| CAP-STATE | ✅ | L2 | … | … |
| CAP-STORE | ✅ | L1 | … | … |
| CAP-TIMER | ✅ | L2 | … | … |
| CAP-NOTIFY | ✅ | L1 | … | … |
| CAP-ATTN | ⚠️ partial | L2/L3 | … | the persistent display surface is only the DM |
| CAP-SPAWN | ✅ | L1 | … | the X4 deadline is 3600s (version vX) |
| CAP-EXEC | ✅ | L1 | … | the isolation boundary is … |
| CAP-ROSTER | ✅ | L2 | … | … |

## Illegal-Capability Degradation
(declares, per capability, which protocol clauses this binding "does not support / must degrade")

## Known Issues
(the runtime's known bugs and their impact on protocol execution)
```

**A binding that fails to declare = an illegal binding** (it cannot host any Millforge protocol flow).

## Protocol ↔ Binding Dependency Summary

| Protocol piece | Dependent capabilities | Missing = |
|----------|---------|--------|
| §03 decision aggregation | CAP-STATE + CAP-TIMER (scripts) | the aggregation mechanism is unavailable (degrades to "human single-point only") |
| §04 NMH | CAP-STORE (NMH documents) | the decision tree is not persisted (the file is not the contract — illegal) |
| §05 NMA | CAP-EXEC + CAP-STORE | the checklist is not executable (degrades to "peer review only") |
| §06 lifecycle | CAP-NOTIFY + CAP-STATE | dual-channel reporting / completion signals are unavailable |
| §07 handoff | CAP-STORE (cross-team space) | cross-team is unavailable (single_user only; a multi_user binding may omit) |
| §08 contract | CAP-STORE (fingerprint) + CAP-STATE (snapshot) | contract pinning is unavailable (degrades to "no pinning, re-verify every time") |
| §09 governance | CAP-STATE + CAP-TIMER + CAP-ATTN | the stall fuse / timeouts are unavailable |
| §10 loop | CAP-SPAWN(X4) + CAP-STATE + CAP-TIMER | the loop is unavailable (degrades to "no iteration") |
| §11 signal | CAP-STATE (event_type) + CAP-STORE (fingerprint) | the signal is unavailable (degrades to "acceptance cites full history" — a weakened mode, must be declared) |
