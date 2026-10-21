# NMA: Agent-to-Agent Structured Communication + Peer Review Protocol

> v1.0
> **In one sentence**: collaboration messages between agents must be structured, traceable and verifiable; review turns "I think it's fine" into "command Y proves X".
> **Positioning**: NMA = **Part A communication layer** (delegation / reporting / queries / handoff — the skeleton of everyday collaboration) + **Part B review layer** (acceptance / peer review / multi-critic). Both share one discipline: all collaboration lands on structured messages and resolvable references, never on free text.

## Part A — Agent-to-Agent Structured Communication

### 1. Why not free text

Five problems of free-text collaboration (the original design problem statement):

1. **low information density** — many rounds before all decision points are covered
2. **high omission risk** — with no mandatory coverage list, key items may never be asked
3. **terminology drift** — the same word means different things on the two sides
4. **untraceable** — who asked what and who answered what is scattered across chat logs
5. **not reusable** — the next agent must read the entire chat history to learn the background

The goal of structured communication: **every collaboration message is a typed, required-field, referenced, replayable event** — not a paragraph of prose.

### 2. Message model

(The data model follows A2A 1.0's Task/Message/Part/Artifact layering: tasks have a state machine, messages are turns, content is split into parts, outputs are artifacts.)

**Required fields**:

| Field | Meaning |
|-------|---------|
| `message_id` | globally unique; the idempotency key (duplicate deliveries are deduplicated on it) |
| `task_id` | the task it belongs to; a cross-task message must create a new task reference |
| `project_id` | optional (omitted for single-task scenarios) |
| `from` / `to` | execution-body identities (role/member IDs in the roster) |
| `type` | closed list, see §3 |
| `refs[]` | content references: CAP-STORE artifact ref (with fingerprint) / CAP-STATE event ref / file path |
| `status` | `submitted` / `working` / `input-required` / `completed` / `failed` / `cancelled` |
| `created_at` | timestamp (for audit and ordering) |

**Optional fields**: `correlation_id` (which message this replies to), `deadline`, `deadline_fallback` (the action on timeout), `summary` (one-line summary; **a summary is not evidence**).

**Content parts**: `text` (summary/explanation, may be omitted) / `file_ref` (artifact reference) / `data` (structured fields). **Acceptance, review and closure may only cite artifacts referenced by `refs[]`, never message bodies.**

### 3. Message types (closed list)

| type | Purpose | Direction | Additional required fields |
|------|---------|-----------|----------------------------|
| `DELEGATE` | delegate a task | orchestrator → executor | `goal` / `acceptance[]` (structured acceptance criteria) / `delivery` (where the deliverable goes) — the triad; missing one = invalid delegation, the receiver may return it |
| `ACK` | accept / return | executor → orchestrator | `accepted` (true/false) + reason if returned |
| `PROGRESS` | progress (optional) | executor → orchestrator | `current_step` (carries no acceptance semantics) |
| `COMPLETE` | completion | executor → orchestrator | `artifact_refs[]` + `summary` + `evidence[]`; lands `SIG-COMPLETE` |
| `QUERY` | question (possibly blocking) | any → any | `question` + `blocking` (true/false) |
| `DECISION_REQUEST` | human decision needed | any → human (via CAP-ATTN) | `options[]` + `recommendation` + `impact` + `deadline` (see 04-NMH §8) |
| `HANDOFF` | cross-team handoff | orchestrator → orchestrator | `brief_ref` + `decision_refs[]` + `constraints[]` (see 07-HANDOFF) |
| `ESCALATE` | escalation | any → superior | `reason` + `positions[]` + `evidence[]` (see 09-GOVERNANCE) |

New types require a protocol version change (minor); execution bodies may not define their own types.

### 4. Communication discipline

1. **References, not inline content**: give `refs`, don't stuff long text into the message body (context isolation; a body summary is never acceptance evidence).
2. **Persist to state**: every message is written to CAP-STATE (event log), replayable by `message_id` / `task_id`.
3. **Idempotency**: a duplicate delivery of the same `message_id` takes effect once; retries reuse the same `message_id`.
4. **ACK is mandatory**: a `DELEGATE` must receive an `ACK` within `deadline`; timeout = anomaly — `ESCALATE` or re-delegate, never wait silently.
5. **Read state from state**: task status is whatever CAP-STATE says; never rely on chat memory or "I remember sending it".
6. **Notification surface**: delivery rides CAP-NOTIFY code-level events (V5 subscribable); IM text is only a derived view (V4/V6 semantics apply).
7. **Terminal means terminal**: `completed` / `failed` / `cancelled` tasks accept no further messages (aligned with A2A terminal states); continued collaboration = a new task.

### 5. Relationship to review

- Review (Part B) consumes Part A's `refs[]` and `evidence[]`, not the narrative body.
- Review outcomes are returned as messages: a `COMPLETE` acceptance lands `SIG-VERDICT`; a rejection is a `QUERY` or `ESCALATE` with reasons and evidence.
- The communication layer makes no quality judgments; the review layer defines no message formats. The two are decoupled and joined by references.

## Part B — Review

### 6. Positioning & Triggers

**NMA's review layer is a review protocol**: it verifies that a "done" claim is real.

**Trigger scenarios** (any one):
- a worker submits a deliverable that belongs to a **review category** (code/config/plan/document — which categories are defined by the binding layer's role instance table)
- any agent explicitly requests review
- the final review before project acceptance (the leader's acceptance of the final output)

**reviewer ≠ reviewed party** (conflict-of-interest separation; who reviews whom = the binding layer's role instance table).

### 7. Dual Mode

| Mode | Applies to | Core mechanism |
|------|------|---------|
| **Checklist ticket** | code / config / verifiable output | triad scorecard (§8) — each line is an executable command, result reproducible |
| **Peer review** | documents / plans / designs | structured challenge (§9) — per-item opinions + responses + locking |

The deciding criterion: **can the output be verified by command?** Yes → Checklist; no → peer review; mixed outputs take each their own path.

### 8. Checklist Ticket (scorecard triad)

| Element | Requirement |
|------|------|
| concrete command | a copy-paste-executable shell/grep/curl/API call |
| expected result | an explicit pass criterion (not "looks right") |
| executor tag | 🟢 = executed by the reviewed party / 🔵 = verified by the reviewer / ❌ = not executable (reason stated) |

```
reviewer sends the Checklist (@reviewed party)
  each line: [C{n}] {what is checked} — command: {cmd} — expected: {result} — status: 🔓
reviewed party executes each 🟢 line → pastes command output → ✅ (with output evidence)
reviewer independently verifies 🔵 lines (only external checks the reviewer can access —
  if a cross-workspace file check is impossible, mark ❌; never pretend)
all ✅ → pass; any ❌ with a substantive issue → ⚠️ reject (with reasons)
```

**Source spot-check (pairs with 04-NMH §7)**: the reviewer randomly picks N nodes/items containing factual assertions and requires a resolvable source (file+line / CAP-STORE ref+fingerprint / external doc / the human's own words); no source → that item is ⚠️. **Never ask the model "are you sure"; only check that a source exists and reproduces.**

**Isolation boundary**: the reviewer cannot run commands inside the reviewed party's workspace. 🔵 items are limited to externally verifiable surfaces — API endpoints, object-storage readable files, public docs.

### 9. Peer Review (documents/plans)

```
reviewer reads the output → sends structured review (@reviewed party)
  [R{n}] {location/section} — {issue or challenge} — severity: blocking/suggestion/question — status: 🔓
reviewed party responds to each line (accept & fix / decline with reason / request clarification)
  status: ✅ (both sides agree) / ⚠️ (rejected, to be fixed) / 🏳️ (deadlock)
all ✅ → pass; any ⚠️ → re-review after fix; any 🏳️ → escalate
```

**Review explanation requirement (learning loop)**: every lock/rejection must carry a one-sentence reason — "why it passed / was rejected". A review without reasons = a black box, a protocol violation.

### 10. Human Peers First

A matching-domain human peer exists and is present → **give it to the human first**. Agent review is a substitute, not a supplement — when a human is available, the human's judgment is the final reference (the agent may add technical verification, never override the human's judgment).
Default practice: when the humans' domains differ, NMA defaults to agent review; humans spot-check + arbitrate (intervene at 🏳️).

### 11. 🏳️ Escalation Path (mode-dependent)

| mode | Escalation target |
|------|---------|
| single_user | the arbitrator |
| multi_user | the leader (intra-team); directional deadlock → suggest the involved humans talk directly |

Escalation content = both positions (one paragraph each) + the divergence point + each side's evidence. **Escalate facts and divergences, never emotions.**

### 12. Multi-Critic Voting (MC-1~10, extending B-6)

**Empirical premise**: a panel of 9 frontier LLMs (7 model families) yields effective independent votes ≈2 — majority voting among isomorphic critics is statistically equivalent to a single critic plus noise (panel accuracy 8–22pp lower than independent voting). **Therefore: no blanket adoption — conditional enablement + heterogeneity constraint.**

**Enablement conditions (all must hold)**:
- **MC-1** the delivery is a human-locked critical delivery: `critical_delivery: true` (declared explicitly by the accountable stakeholder in loop_spec/task spec; never self-judged by an execution unit as "this is important")
- **MC-2** the acceptance conclusion is irreversible or high-external-impact (R1 class)
- **MC-3** the critic pool satisfies the heterogeneity constraint (MC-4); otherwise → degrade to **single critic + mandatory dissent record** (must not claim "multi-critic voting")

**Heterogeneity constraint**:
- **MC-4** the N critics must come from ≥2 different model families (or execution units with provably different training distributions); multiple instances of the same family add no independent votes. The binding must declare the critic pool's model-family composition; undeclarable or unsatisfied → may not be enabled
- **MC-5** N critics = N independent fresh subagents (CAP-SPAWN X1), with identical context_refs (spec + artifact ref + signal ref); no sharing of intermediate conclusions, no mutual visibility of scores
- **MC-6** each critic independently records its verdict and reasons; the reasons must include ≥1 "assumption that, if wrong, would break this" (explicit dissent); score-only is not allowed

**Voting rules**:
- **MC-7** strict majority (>N/2) for pass/fail
- **MC-8** tie (even N, split) → **no re-vote**, escalate directly to the accountable (re-voting = correlated errors counted twice)
- **MC-9** each critic's verdict/reasons/dissent are written to the decision record; **even when the majority passes, the minority opinion must be preserved** (input to the next re-plan)
- **MC-10** the B-6 dead-loop boundary is unchanged: a "bounce" on the same criterion counts by **voting round**, not by individual critic (round 1: 2 no-votes + 1 yes-vote = 1 mismatch); round-3 divergence (however many critics) → freeze and escalate to human; a consistent round consumes no mismatch budget

**Cost integration**: N critics = N spawns, all counted in the spawn budget. Budget-exceeded degradation ≠ a pure single critic (that would break the reliability semantics) → **"single critic + mandatory dissent + human-locked acceptance"** (the human must explicitly confirm the single critic's conclusion).

### 13. B-6: Critic Dead-Loop Protection

The dead-loop boundary for a verification mismatch (the critic bounces the output, but the spec has no ambiguity to fix):

1. the mismatch enters the **spec-clarification channel**: a 24h accountable ruling window (carried by CAP-TIMER)
2. window timeout = **the original spec stands** + the critic records dissent and **must still emit the scorecard** (never empty-handed)
3. the same criterion may be bounced at most 2 rounds; **round 3 freezes** (escalate to human)
4. **final ruling authority = human; the critic is a quality signal, not a veto**

Counting and window judgment = deterministic scripts (`core/scripts/verification-mismatch-window.sh`), not LLM self-awareness.

### 14. Forbidden / Required

- ❌ delegating tasks with free text instead of structured messages (the triad must be `DELEGATE` fields)
- ❌ treating a message body/summary as acceptance evidence (only `refs[]` counts)
- ❌ false verification (marking ✅ without running the command)
- ❌ silent rejection (a rejection must @the reviewed party + reasons)
- ❌ the reviewer overreaching to edit the reviewed party's output (opinions are allowed; acting = role confusion)
- ❌ locking without reasons
- ❌ a critic self-enabling multi-critic via "importance" (MC-1 is human-locked)
- ✅ Checklist output evidence must be pasted verbatim (truncation allowed, fabrication never)
- ✅ acceptance verdicts may cite only marked signals + artifact refs (§11-SIGNAL effect 2)
