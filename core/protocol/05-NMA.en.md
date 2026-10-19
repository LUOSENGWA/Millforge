# NMA: Peer Review Protocol

> v1.0 | Provenance: NMProtocol §6 (internal NMA v2.46, instance role table stripped) + B-6 critic dead-loop (round 3) + multi-critic voting MC-1~10 (round 8)
> **In one sentence**: an agent's self-report of "done" is untrustworthy. NMA is the agentified substitute for human peer review — turning "I think it's fine" into "command Y proves X", with executable verification and structured challenge.

## 1. Positioning & Triggers

**NMA is a review protocol, not a general agent↔agent communication protocol.** Task dispatch, coordination, status sync = just send a message (the §06 triad); no NMA needed.

**Trigger scenarios** (any one):
- a worker submits a deliverable that belongs to a **review category** (code/config/plan/document — which categories are defined by the binding layer's role instance table)
- any agent explicitly requests review
- the final review before project acceptance (the leader's acceptance of the final output)

**reviewer ≠ reviewed party** (conflict-of-interest separation; who reviews whom = the binding layer's role instance table).

## 2. Dual Mode

| Mode | Applies to | Core mechanism |
|------|------|---------|
| **Checklist ticket** | code / config / verifiable output | triad scorecard (§3) — each line is an executable command, result reproducible |
| **Peer review** | documents / plans / designs | structured challenge (§4) — per-item opinions + responses + locking |

The deciding criterion: **can the output be verified by command?** Yes → Checklist; no → peer review; mixed outputs take each their own path.

## 3. Checklist Ticket (scorecard triad)

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

**Isolation boundary**: the reviewer cannot run commands inside the reviewed party's workspace. 🔵 items are limited to externally verifiable surfaces — API endpoints, object-storage readable files, public docs.

## 4. Peer Review (documents/plans)

```
reviewer reads the output → sends structured review (@reviewed party)
  [R{n}] {location/section} — {issue or challenge} — severity: blocking/suggestion/question — status: 🔓
reviewed party responds to each line (accept & fix / decline with reason / request clarification)
  status: ✅ (both sides agree) / ⚠️ (rejected, to be fixed) / 🏳️ (deadlock)
all ✅ → pass; any ⚠️ → re-review after fix; any 🏳️ → escalate
```

**Review explanation requirement (learning loop)**: every lock/rejection must carry a one-sentence reason — "why it passed / was rejected". A review without reasons = a black box, a protocol violation.

## 5. Human Peers First

A matching-domain human peer exists and is present → **give it to the human first**. Agent review is a substitute, not a supplement — when a human is available, the human's judgment is the final reference (the agent may add technical verification, never override the human's judgment).
Default practice: when the humans' domains differ, NMA defaults to agent review; humans spot-check + arbitrate (intervene at 🏳️).

## 6. 🏳️ Escalation Path (mode-dependent)

| mode | Escalation target |
|------|---------|
| single_user | the arbitrator |
| multi_user | the leader (intra-team); directional deadlock → suggest the involved humans talk directly |

Escalation content = both positions (one paragraph each) + the divergence point + each side's evidence. **Escalate facts and divergences, never emotions.**

## 7. Multi-Critic Voting (MC-1~10, extending B-6)

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

## 8. B-6: Critic Dead-Loop Protection

The dead-loop boundary for a verification mismatch (the critic bounces the output, but the spec has no ambiguity to fix):

1. the mismatch enters the **spec-clarification channel**: a 24h accountable ruling window (carried by CAP-TIMER)
2. window timeout = **the original spec stands** + the critic records dissent and **must still emit the scorecard** (never empty-handed)
3. the same criterion may be bounced at most 2 rounds; **round 3 freezes** (escalate to human)
4. **final ruling authority = human; the critic is a quality signal, not a veto**

Counting and window judgment = deterministic scripts (`core/scripts/verification-mismatch-window.sh`), not LLM self-awareness.

## 9. Forbidden / Required

- ❌ false verification (marking ✅ without running the command)
- ❌ silent rejection (a rejection must @the reviewed party + reasons)
- ❌ the reviewer overreaching to edit the reviewed party's output (opinions are allowed; acting = role confusion)
- ❌ locking without reasons
- ❌ a critic self-enabling multi-critic via "importance" (MC-1 is human-locked)
- ✅ Checklist output evidence must be pasted verbatim (truncation allowed, fabrication never)
- ✅ acceptance verdicts may cite only marked signals + artifact refs (§11-SIGNAL effect 2)
