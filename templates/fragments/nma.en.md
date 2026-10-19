## NMA Peer Review (condensed load · full text = protocol §05-NMA)

**Triggers**: a worker deliverable belongs to a review category (code/config/plan/document) ｜ explicit review request ｜ final review before project acceptance. **Routine dispatch/coordination/status sync = just send a message; no NMA.**

**Reviewer ≠ reviewed party** (fixed by the role instance table; reviewing your own output = violation). A human peer is present → give them the review first (agent review is a substitute, not a supplement).

**Dual mode** (judgment: can the output be verified by command?):

**Checklist ticket** (code/config/verifiable output):
```
Reviewer sends [C{n}] {what is checked} — command: {cmd} — expected: {result} — 🔓
Reviewed party executes each line 🟢 and pastes output → ✅ (with evidence)
Reviewer 🔵 verifies independently (external verifiable surfaces only: API / readable object storage / public docs; cannot = ❌ with note, never pretend)
All ✅ = pass ｜ ❌ with substantive issue = ⚠️ reject (with reasons)
```
Missing any of the triad = invalid line. **Isolation boundary**: the reviewer never runs commands inside the reviewed party's workspace.

**Peer review** (documents/plans/designs):
```
[R{n}] {location} — {challenge} — severity: blocking/suggestion/question — 🔓
Reviewed party responds to each line (accept & fix / decline with reason / request clarification) → ✅/⚠️/🏳️
All ✅ = pass ｜ ⚠️ = re-review after fix ｜ 🏳️ = escalate
```

**Escalation (🏳️)**: single_user → arbitrator; multi_user → leader (directional deadlock → suggest the humans of both parties talk directly). Escalation content = both positions + the divergence point + the evidence. **Escalate facts, never emotions.**

**Multi-critic (critical_delivery + R1 + heterogeneous pool satisfied)**: N fresh independent instances (≥2 model families) / independent verdict + dissent ≥1 assumption / strict majority / tie → no re-vote, escalate directly / minority opinion preserved / rejections count mismatches by voting round.

**B-6 deadlock defense**: mismatch = spec-clarification channel (24h accountable ruling window); timeout = original spec stands + critic records dissent and **still emits the scorecard**; same criterion 3 rounds → freeze and escalate to human; **the critic is a quality signal, not a veto; final ruling = human**.

**Forbidden**: false verification ｜ silent rejection ｜ over-boundary editing of the reviewed output ｜ locking without reasons.
