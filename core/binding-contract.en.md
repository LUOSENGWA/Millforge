# Millforge Runtime Binding Contract v1.0

> Version: v1.0 (frozen protocol-layer baseline) | License: Apache-2.0
> The **minimal capability interface** between the Millforge core and any runtime (the sole legal reference surface).
> Core clauses may reference only CAP-* ids and invariants — never any concrete component.
> Paradigm: the contract contains no provider type; the adapter translates concrete runtime semantics into the unified contract.
> durable collaboration is separated from native execution: the harness owns persistent state, the provider is only responsible for execution.
> Runtime-specific-name mapping: see `bindings/agentteams/reference-mappings.md` (English twin `.en.md`) — a non-normative appendix; the contract body contains no runtime-specific names.

## Design Principles

1. The core never references concrete components — only CAP-* ids and invariants
2. Capabilities are a **minimal set**, not a maximal one — a runtime may offer more; the core depends only on the following 8
3. Every capability must declare its invariants — **an invariant violation = an illegal binding**, not an "implementation difference"

---

## CAP-STATE — Task-Level Durable State Store

**Semantics**: provides atomically updatable key-value state for each task; survives process restart/crash.

**Interface contract** (language-agnostic):
```
read(task_id, key) -> value | ABSENT
compare_and_set(task_id, key, expected, next) -> OK | CONFLICT | ABSENT
append(task_id, key, entry) -> new_length      # append semantics, for event streams
list_keys(task_id) -> key[]
```

**Invariants**:
- **S1 write durability**: a write that returns OK must be readable back after a crash (durable custody)
- **S2 atomicity**: compare_and_set is linearizable under concurrency; a CAS failure must not produce a partial write
- **S3 replayability**: append order is consistent on re-read (append-only semantics)
- **S4 no silent loss**: state must not be lost due to cache eviction, notification loss, or temporary-storage cleanup
- **S5 record structure (implementation sub-item)**: state records are versioned JSON (a version field or an append sequence), supporting S3 replay
- **S6 write confirmation (implementation sub-item)**: a write must have a confirmable point; an unconfirmed write is treated as unexecuted, and no merge/consume/accept may be triggered before the confirmation (aligned with the CAP-STORE T2 execution detail)
- **S7 deterministic implementation (implementation sub-item)**: protocol-layer judgments such as timeout judgment / vote counting / conflict detection must be derived by deterministic scripts (L2) reading CAP-STATE — never "the agent remembering to compute"; the binding must declare the scripts' trigger mechanism (e.g. an external scheduler)

**Millforge dependencies**: R1-R6 decision records, NMH lock chain, B-4/B-5/B-6 counts and windows, B-10 classification state, spec and decision_class, loop authoritative state (§10).

> Note: the positioning of object storage (S3 semantics) is **CAP-STORE, not CAP-STATE**. If you implement CAP-STATE with S3 JSON files, use conditional PUT + a version field for optimistic concurrency (retry on failure); do not simulate key-value CAS with object-level conditional writes (hot-key serialization).

## CAP-STORE — Addressable, Fingerprintable Artifact Store

**Semantics**: stores path-addressable immutable content; a cryptographic fingerprint can be computed over the content.

**Interface contract**:
```
write(path, bytes) -> {ref, fingerprint}
append(path, entry) -> new_ref        # see T3
read(ref) -> bytes | ABSENT
fingerprint(ref) -> fingerprint | ABSENT
exists(ref) -> bool
```

**Invariants**:
- **T1 content addressing**: the fingerprint of the same ref is constant while its content is unchanged; a content change must produce a new ref or a new fingerprint
- **T2 write confirmability**: the {ref, fingerprint} returned by write must be returned only after persistence completes; returning means it can be safely consumed downstream
  - **T2 execution detail**: if the write path goes through a sync layer (workspace ↔ object-storage asynchronous sync), before write returns it must confirm the sync layer has persisted the object (uploaded/committed receipt); an unconfirmed write must not return {ref, fingerprint}, and the caller must not consume an unconfirmed ref. The sync-layer implementation (push_loop/mirror/rsync etc.) is a binding parameter; "return only after confirmation" is the mandatory semantics of T2
- **T3 append-only (chain-simulable)**: `append(path, entry) -> new_ref`. The implementation may be: ① JSONL append to the same object (when the runtime supports safe concurrency) ② chained append of new objects (entry_ref = path+seq, append returns the chain tail) ③ any other equivalent semantics. The core only requires that read(ref) returns all entries in append order, and **does not require the same physical object**
- **T4 immutability (recommended)**: an accepted artifact is frozen; a content change must produce a new version (new ref)
- **T5 path contract**: artifact paths follow `<root>/<kind>/<id>…` (kind ∈ artifacts/decisions/nmh-docs/contracts/…), stable and predictable
- **T6 fingerprint algorithm declaration**: the fingerprint algorithm must be declared by the binding (e.g. sha256-8); different bindings may differ, but within the same binding it must be consistent

**Millforge dependencies**: decision_log landing, contract artifact, handoff, decision record, saga compensation instructions.
**decision_log landing rule**: the write to CAP-STORE returns {ref, fingerprint} and satisfies T2; a spawn's return carries only ref + fingerprint; the ref must be written into CAP-STATE.

## CAP-TIMER — Due-Time Trigger

**Semantics**: registers a timer that "triggers a derived action after a persisted point in time comes due"; the triggered action is deterministic (read state, derive due, execute a predefined action).

**Interface contract**:
```
schedule(task_id, timer_id, due_at, action_spec) -> OK | ALREADY_EXISTS
cancel(task_id, timer_id) -> OK | ABSENT
on_due(callback)   # called after due_at; callback idempotent
```

**Invariants**:
- **U1 monotonicity + clock authority**: due_at is based on the timestamp in the persisted state; the trigger must not fire earlier than due_at. **timeout_at must be written by CAP-STATE, using the time of the clock source where CAP-STATE resides; the "now" compared when the timer fires must come from the same clock source** (or an equivalently calibrated source)
- **U2 at most once**: the same timer_id must not fire twice; a late trigger is allowed, and the callback must be idempotent
- **U3 state authority**: a timer must not maintain an independent "processed" marker as the basis for judgment; the judgment must be re-derived from CAP-STATE (idempotent re-derivation)
- **U4 granularity declaration**: the runtime must declare the minimum check granularity (e.g. 2 minutes); the caller must not assume finer precision
- **U5 trigger mode**: supports one-shot and periodic triggering; periodic triggering is for fallback-wake (watchdog/heartbeat) scenarios; the period is a binding-declared parameter
- **U6 self-contained payload**: the trigger payload must be self-contained; it must not assume the receiving session still remembers the context
- **U7 dedup key formula**: dedup key = `hash(task_id + trigger_kind + due_at)` (the concretization of U2 at-most-once)

**Millforge dependencies**: R6 30min/2h timeouts, R5 24h/4h windows, B-5 stall, B-6 mismatch windows, loop fallback wake, watchdog three modes.

## CAP-NOTIFY — Best-Effort Notification

**Semantics**: delivers a notification to a human or Agent; loss is allowed (on loss, the state must be rebuildable from CAP-STATE); **protocol events must have a code-level subscription surface; IM text is not the sole observation point**.

**Interface contract**:
```
send(recipients[], message, event_ref?)
  -> delivery_report {delivered[], failed[], gaps[]: {recipient, reason}}
subscribe(event_types[], callback) -> subscription_id   # code-level event surface
unsubscribe(subscription_id) -> OK | ABSENT
```

**Invariants**:
- **V1 a notification is not state**: no decision/due/count may exist only in a notification
- **V2 loss is rebuildable**: after a notification is lost, CAP-STATE + CAP-TIMER must suffice to rebuild "who needs to know what"
- **V3 no silent drop**: when the runtime knows a recipient is unreachable (not in the allowlist / channel does not exist / identity unverified) → it must return the reason in delivery_report.gaps[]; gaps do not block send, but the caller must be able to observe them
- **V4 notifications are repeatable**: repeated delivery of the same message produces no state side effects; the receiver dedups by message_id
- **V5 code-level subscription**: every protocol event (attention create/resolve/timeout, decision lock/reopen, circuit-breaker state change, contract snapshot change) must be subscribable by code, and the event carries an event_ref (pointing to the authoritative record in CAP-STATE); an IM text notification is a **derived view** of the code-level event, not the sole observation surface
- **V6 receipts queryable**: delivery_report must distinguish delivered (the runtime confirms delivery to the channel) from accepted (the channel confirms receipt); accepted alone does not constitute "the human saw it" — evidence that a human saw it can only be a CAP-ATTN resolve or an explicit read receipt on the channel side
- **V7 channel declaration**: the binding must declare which channels exist (project room / DM / originating channel) and their relative positions
- **V8 originating-channel notification layering**: the delivery of the originating-channel notice is an L2 mechanism (the delivery_report is observable); the generation of the report's content is the L3 behavioral layer; what is lost can be rebuilt from CAP-STATE per V2; never rely on "remembering to send"

**Millforge dependencies**: attention bypass CC, escalation notifications, freeze/unfreeze notifications, dashboard/IM cards (derived views).

## CAP-ATTN — Human Attention Request and Response

**Semantics**: initiates a request requiring a response to a designated human; the response must be persisted; the same request is idempotent; **the human response must be initiated from at least one persistent display surface, and the initiator's identity must be verifiable**.

**Interface contract**:
```
request(task_id, kind, prompt, options?, route_to, timeout_at, idempotency_key)
  -> {request_id, state, surfaces[]}
resolve(request_id, response, responder_id, surface_id, idempotency_key)
  -> OK | ALREADY_RESOLVED | NOT_FOUND | IDENTITY_UNVERIFIED
status(request_id) -> {state, response?, resolved_at?, resolved_via_surface?}
list_open(task_id) -> request_id[]
```

**Invariants**:
- **W1 idempotency**: requests with the same idempotency_key must not produce multiple independent requests; a duplicate returns the same request_id; resolve is likewise idempotent — a repeated resolve with the same (request_id, responder_id, idempotency_key) returns the first result and produces no second response
- **W2 response persistence**: after a successful resolve, the response (including responder_id, surface_id, timestamp) must be written to CAP-STATE; merely "read/clicked" on the channel does not count as a response
- **W3 timeout judged by CAP-TIMER**: the request does not maintain a wall-clock timeout; timeout_at is written to CAP-STATE, and the due action is triggered by CAP-TIMER
- **W4 trusted identity**: resolve must verify the responder's identity; the role self-declared by the payload must not be trusted; the strength of identity verification is declared by the channel (W5); a channel below the minimum requirement must not serve as a response surface
- **W5 response-surface quality**: each request must have at least one **persistent display surface** supporting the response — it persists until the request times out, can be actively revisited by a human, and the response can complete identity verification on that surface. IM private chat, dashboard todo list, dedicated approval page = persistent display surfaces; **group-chat @mention is not** (messages get buried, cannot be revisited)
- **W6 multi-surface close**: a successful resolve on any persistent display surface → the CAP-STATE state becomes resolved; other display surfaces perceive it via polling/event push and close the todo; closing is a view behavior and does not change the authoritative state
- **W7 option structure**: when kind=decision and options are provided, options must be a structured list `[{option_id, label, consequence_summary?}]`; the response must return the option_id, and **free text must not be returned as a choice**
- **W8 responder restricted to humans**: a request can only be resolved by a human (roster role = human); an Agent must not resolve it on its own
- **W9 idempotency-key formula**: the request idempotency key = `hash(task_id + decision_node_id + decision_hash)`; the resolve idempotency key includes responder_id + action, i.e. `hash(task_id + request_id + responder_id + action)`
- **W10 response write confirmation**: a human response enters CAP-STATE only after the write confirmation; subsequent actions (reclassification / re-voting) must not begin before the confirmation

**Millforge dependencies**: R6 attention, NMH lock confirmation, B-6 escalation, B-10 reclassification ruling, C-3 undecidable escalation.

## CAP-SPAWN — Fresh-Context Execution Unit

**Semantics**: creates an execution unit with a brand-new context, receives a structured task, and returns a structured result.

**Interface contract**:
```
spawn(task_spec, context_refs[], return_schema, timeout?)
  -> {spawn_id, result, decision_log_ref}
```

**Invariants**:
- **X1 context isolation (hard)**: a spawn must not inherit the parent execution unit's conversation history; it can obtain explicit input only through context_refs. **A runtime that does not satisfy X1 must not serve as a legal binding**
- **X2 structured return**: result must conform to return_schema; decision_log_ref must point to a fingerprintable artifact in CAP-STORE
- **X3 independence**: a spawn must not modify the parent execution unit's state; all state changes are passed through the return value
- **X4 boundedness (hard)**: a spawn must be bounded — either return a structured result `{artifact_refs[], decision_log_ref, self_reported_status}` within the declared deadline, or report a bounded failure `{bounded_failure: true, reason, partial_refs?}` within the deadline; it must not hang indefinitely; the deadline is declared by the caller, and the runtime must enforce it. **A runtime that does not satisfy X4 must not serve as a legal binding** (the loop-executability prerequisite: otherwise iteration_budget and CAP-TIMER lose their meaning)
- **X5 input = spec reference**: the spawn input is a task-spec reference (task_spec / context_refs), not a long text inlined in the message
- **X6 context_refs content restriction**: context_refs may contain only marked signals + CAP-STORE artifact refs (§11-SIGNAL)
- **X7 worker context isolation (protocol rule)**: the worker's native session does only scheduling + acceptance; all implementation work must go through a CAP-SPAWN sub-execution unit (reads context from files, writes outputs to files, destroyed on completion). This is a protocol rule, not a binding feature — but the binding must provide the means to implement it

**Millforge dependencies**: worker context isolation (the v2.40 ruling), critic independent execution, C-3 constrained classification, merge-semantics confirmation, loop iteration/re-plan spawn.

## CAP-EXEC — Deterministic Program Execution

**Semantics**: runs a deterministic program (script/binary), passes arguments, and captures structured output and an exit code. The program may ship with the core, or be a runtime-provided equivalent.

**Interface contract**:
```
exec(program_ref, args[], stdin?, timeout?) -> {exit_code, stdout, stderr}
```

**Invariants**:
- **Y1 determinism**: the same program_ref + the same input → the same output (does not rely on LLM sampling)
- **Y2 exit-code semantics**: the exit code is interpreted with the semantics defined by the caller; 0 does not automatically mean "success"
- **Y3 no implicit state**: must not read/write the caller's implicit state; all input is passed explicitly, all output is returned explicitly
- **Y4 execution environment declaration**: the binding must declare the execution environment (which machine / container / sandbox)
- **Y5 output persistence**: execution output must be persisted (written to CAP-STORE or returned inline); the evidence is auditable
- **Y6 timeout bound**: command execution must be bounded; it must not hang forever
- **Y7 NMA isolation boundary**: the executor must not run inside the reviewed party's workspace (unreachable across containers / across workspaces); 🔵 items are limited to externally verifiable surfaces (API / object storage / public docs)

**Ruling on the ownership of the 8 scripts**: the 8+1 scripts in `core/scripts/` **ship with the core protocol**; runtimes are not required to rewrite them —
1. The CAP-EXEC semantics is "run a deterministic program", not "the runtime provides these particular programs"; a runtime rewrite = semantic-drift risk
2. The scripts are **deterministic implementations of the protocol semantics** (B-1 schema validation / B-2 conflict detection / B-3 semver classification …) and should be versioned together with the protocol clauses
3. Runtimes without object storage / group chat (the claude-code adaptation) run the scripts as-is — the input/output paths are resolved by the caller per the CAP-STORE ref (the local file system is a legal CAP-STORE implementation)
4. Exception: the **scheduling part** of the watchdog (scheduler configuration, state-file path) = binding implementation; the logic part (due judgment / action derivation) = the core's CAP-TIMER reference implementation

**Millforge dependencies**: all deterministic scripts for B-1/B-2/B-3/B-5/B-6/B-10/C-3 + timer-derive.

## CAP-ROSTER — Role Roster

**Semantics**: queries the identity, role, and weight of human members.

**Interface contract**:
```
members(team_id) -> [{member_id, role, weight, accountable_for[]}]
accountable(task_id) -> member_id | ABSENT
delegation_chain(task_id) -> [{delegator, delegatee, scope, granted_at}] | []
```

**Invariants**:
- **Z1 weight comes from role**: weight is a role attribute, not model confidence; the core must not infer weight via LLM
- **Z2 single accountable**: each task has at most one accountable stakeholder; ABSENT must be returned explicitly and must not be silently filled with a "default owner"
- **Z3 delegation chain queryable**: when the accountable delegates a response, the delegation chain must be queryable; the core uses the delegation chain when judging "who has the power to lock"

**Millforge dependencies**: R1 owner ruling, R2 weighted majority, NMH locking, attention routing (§03-4), loop driver identity determination (§10-3).

---

## Security Redlines (cross-capability, S1-S5)

See `protocol/12-REDLINES.md` §1 (artifact data redlines / decision_log anti-forgery / contract dual confirmation / group chat is not a response surface / replay protection) — all five are execution details of the CAP interfaces; violating any = an illegal binding.

## Binding Legality Determination

A runtime constitutes a **legal binding** if and only if:
1. all 8 capabilities are implemented and all invariants are satisfied (X1/X4 are hard gates)
2. it provides CAP-EXEC able to run `core/scripts/` (or declares an equivalent implementation and passes the golden tests)
3. it declares: runtime version matrix / primitive mapping table (every §01 primitive → concrete mechanism) / mode matrix / timer granularity / persistent-display-surface list
4. it passes the `golden-tests/` regression (L5)

## Capability List (overview)

| Capability | One-line semantics |
|---|---|
| CAP-STATE | task-level durable state read/write (replayable, atomically updatable) |
| CAP-STORE | addressable, fingerprintable artifact store (append optional) |
| CAP-TIMER | due-time trigger (granularity declaration, idempotent callback) |
| CAP-NOTIFY | best-effort notification channel (loss allowed, state rebuildable) |
| CAP-ATTN | human attention request and response (persistent display surface, idempotent) |
| CAP-SPAWN | fresh-context execution unit (structured return) |
| CAP-EXEC | deterministic program execution (exit-code semantics) |
| CAP-ROSTER | role roster (human members + roles + weights) |

## Binding Declaration Format

The binding's README **must** contain:

```
## Capability Declaration (CAP-*)
| CAP | Implemented | Tier (L1/L2/L3) | Mechanism (runtime API) | Limitations |
|-----|-------------|------------------|--------------------------|-------------|
| CAP-STATE | ✅ | L2 | … | … |
| CAP-STORE | ✅ | L1 | … | … |
| CAP-TIMER | ✅ | L2 | … | … |
| CAP-NOTIFY | ✅ | L1 | … | … |
| CAP-ATTN | ⚠️ partial | L2/L3 | … | the persistent display surface is DM only |
| CAP-SPAWN | ✅ | L1 | … | X4 deadline = 3600s (version vX) |
| CAP-EXEC | ✅ | L1 | … | isolation boundary = … |
| CAP-ROSTER | ✅ | L2 | … | … |

## Illegal-Capability Degradation
(declare, per capability, which protocol clauses this binding "does not support / must degrade")

## Known Issues
(the runtime's known defects and their impact on protocol execution)
```

**Failing to declare = an illegal binding** (it cannot host any Millforge protocol flow).

## Protocol ↔ Binding Dependency Summary

| Protocol piece | Dependent capabilities | Consequence of missing |
|---|---|---|
| §03 decision aggregation | CAP-STATE + CAP-TIMER (scripts) | the aggregation mechanism is unavailable (degrades to "human single-point only") |
| §04 NMH | CAP-STORE (NMH documents) | the decision tree is not persisted (file-as-contract unavailable → illegal) |
| §05 NMA | CAP-EXEC + CAP-STORE | the checklist is not executable (degrades to "peer review only") |
| §06 lifecycle | CAP-NOTIFY + CAP-STATE | dual-channel reporting / completion signals are unavailable |
| §07 handoff | CAP-STORE (cross-team space) | cross-team is unavailable (single_user only; a multi_user binding may omit) |
| §08 contract | CAP-STORE (fingerprint) + CAP-STATE (snapshot) | contract pinning is unavailable (degrades to "no pinning, re-verify every time") |
| §09 governance | CAP-STATE + CAP-TIMER + CAP-ATTN | the stall fuse / timeouts are unavailable |
| §10 loop | CAP-SPAWN(X4) + CAP-STATE + CAP-TIMER | the loop is unavailable (degrades to "no iteration") |
| §11 signal | CAP-STATE (event_type) + CAP-STORE (fingerprint) | the signal is unavailable (degrades to "acceptance cites full history" — a weakened mode, must be declared) |
