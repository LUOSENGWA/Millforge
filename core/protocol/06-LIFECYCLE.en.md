# Task Lifecycle Contract

> v1.0 | Provenance: NMProtocol §8 (L4 retest, empirically validated)
> The complete contract from NMH locking (or a direct human triad instruction) to task closure. Every orchestration role (arbitrator/leader/worker) obeys the same set, at different granularity.

## 1. Recursive Decomposition Model (every layer is a mini-orchestrator)

```
human → [arbitrator] → leader → worker → spawn (sub-execution unit)
         NMH        NMH/route    NMA dispatch  direct triad
        big decompose  —         mid decompose   small decompose
```

| Layer | Input | Decomposition granularity | Output | Acceptance method |
|----|------|---------|------|---------|
| arbitrator (single_user) | NMH decision tree | team level (which team, what order/parallelism) | routing + project creation | leader reports |
| leader | decision tree / arbitrator instruction / direct human instruction | task level (2–N tasks, DAG/sequential) | dispatch (triad + task spec) | worker deliverable + NMA acceptance |
| worker | task spec | atomic level (2–4 spawn sub-tasks) | spawn sub-tasks | self-review of spawn outputs |
| spawn | atomic task description | — | output files | worker review |

**The core loop is isomorphic at every layer**: task received → judge origin (human → NMH; agent → triad validation) → confirm understanding → decompose → dispatch to the next layer → accept & integrate → report upward.

**Worker context-isolation principle (protocol-level)**: a worker's native session does **scheduling + review only** — decomposition, dispatch, acceptance, integration. All implementation work is done by fresh-session sub-execution units, which read context from **files** (never from conversation history) and are destroyed after writing outputs to files. Three-layer cache chain: shared storage (spawn reads context) → runtime automatic offload (persisted during execution) → hardware KV cache (fallback). **Violating this principle = the root cause of context overflow** (empirically validated three times in L4 testing).

**Dispatch triad** (everyday dispatch needs no protocol, but must have these): task goal / acceptance criteria / delivery location. Missing any = invalid dispatch; the receiver may bounce it.

## 2. Completion Signal (TASK_COMPLETED)

worker/leader finishes a task → send the **TASK_COMPLETED** signal (room @superior):

```
@{leader} TASK_COMPLETED: {task-id}
Output: {artifact path}
Key conclusions (3–5, one sentence each):
1. ...
2. ...
```

**Key conclusions are mandatory** — they are the acceptance raw material + the cross-team handoff raw material (§07) + the superior's amnesia defense. Summarizing in three sentences right after finishing is effortless; it cannot be reconstructed afterwards.

**Baseline guarantee (provided by the binding layer)**: the completion signal should be a state-machine side effect of the mechanism layer (tool commit success = an automatic baseline completion message); what the LLM is responsible for is **quality** (conclusions/summary), not "remembering to report". "Silently not reporting" must be mechanistically impossible.

## 3. Dual-Channel Reporting

| Channel | Duty | Content |
|------|------|------|
| **full report in the project room** (archive floor) | visible to the whole team + human, structured | full conclusions, output paths, open issues, next steps |
| **notice on the originating channel** (delivery floor) | the channel the human actually uses (IM/console) | one line: done + key conclusions + project-room pointer |

- **single-team task**: the originating channel is the floor
- **cross-team task (single_user only)**: both channels — full report in the project room @human + originating-channel notice
- the originating channel is fixed at dispatch time (the binding layer's reply_route equivalent)

## 4. Declaration–Verification Binding (the execution form of P3)

Before any agent claims "X is done/pushed/room created/dispatched", **a corresponding tool call must already have succeeded within the same turn**:

| Claim | Verification that must have run |
|------|----------------|
| room created | the room-creation tool's return value + member check |
| dispatched | dispatch-tool/message-send confirmation + the other side's claim |
| pushed/archived | write confirmation (read-back or tool return value) |
| done | the deliverable exists (path check) + TASK_COMPLETED sent |

**Text output and tool calls are two channels** — "saying" ≠ "doing" (the core lesson of the five Manager problems in the L4 retest, protocolized as a hard rule for all roles).

## 5. Reply Discipline (room noise control)

- @mention only when **the other side must act** (handoff, blocker, direct question, task dependency)
- pure acknowledgment messages ("thanks" / "received" / "confirmed") → **do not reply** (anti ping-pong deadlock)
- after a completion report is sent, stop — wait for the next task; don't keep the conversation going
- never report completion twice for the same task

## 6. Failure Recovery SOP (the orchestrator never does the work)

```
Worker anomaly (Internal error / context exceeded / no response >2min)
  Step 0: stop hands. The orchestrator (arbitrator/leader) never opens the artifact and does it themselves.
  Step 1: restart that worker (binding layer mechanism)
  Step 2: wait → re-dispatch the same task
  Step 3: still failing after 3 attempts → escalate to the human (originating channel, with the three attempt records)
bad quality ≠ failure → go through the NMA review chain; do not restart
```

**"did it" ≠ it was really done**: a worker's claimed behavior must be cross-verified against system facts (file existence, room messages, tool return values).

## 7. Permission-Wall Fuse (operational layer, mode-agnostic)

**≥2 workers reporting consecutive permission errors (allowlist interception / inability to speak) → re-route to a DM private channel within ≤30s**; stop grinding into the wall. Permission-error signature: no error logs, messages silently vanish — the first diagnostic step is comparing the access-control configuration (the binding layer's duty).

## 8. State-Machine Side-Effect List (L1/L2 layering, P5 discipline)

The following behaviors are **not allowed to be pure L3 behavioral layer** — the binding layer must implement them as state-machine side effects or deterministic scripts:

| Behavior | Layer |
|------|------|
| TASK_COMPLETED baseline emission | L2 (commit success = automatic side effect) |
| completion signal written to persistent state (pending_signals) | L2 |
| decision lock/unlock/reopen | L2 (CAP-STATE CAS) |
| timeout judgment (2h/24h/window) | L2 (CAP-TIMER + derivation scripts) |
| conflict detection / vote counting / consistency checks | L2 (core/scripts/ pure functions) |
| NMH/NMA interaction quality (follow-ups/explanations/wording) | L3 (behavioral layer, quality enhancement) |
| dual-channel report content generation | L3 (quality layer; the delivery itself is an L2 side effect) |

**System correctness may depend only on L1/L2**; L3 failure = quality degradation, ≠ state corruption.
