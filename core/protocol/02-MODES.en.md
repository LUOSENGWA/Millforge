# Deployment Modes (mode)

> v1.0 | Provenance: NMProtocol §4 (ruled 2026-09-03)
> Structural invariant: multi_user ⟹ user isolation ⟹ cross-team does not hold ⟹ the cluster-level coordination role loses its only core value (cross-team relay) ⟹ the role does not exist.
> This is not an operational switch; it is a phase transition of the system form.

## Definition

| mode | Determination | arbitrator | cross-team extension |
|------|------|-----------|-----------|
| `single_user` | the whole cluster serves **one** human | the cluster-level coordination role exists (full function) | **available** (§07-HANDOFF) |
| `multi_user` | ≥2 humans in use | **no cluster-level coordination role**; intra-team arbitration = leader, cross-team none (user isolation) | **unavailable** |

## Communication Topology

**single_user** (classic three layers):

```
human ──channel──▶ arbitrator (cluster-level coordination role, full function)
                      │ NMH (confirm requirements with human)
                      │ route / create project / dispatch
                      ▼
                   leader ──▶ worker ──▶ spawn (sub-execution unit)
                   (one leader per team; cross-team = §07-HANDOFF)
```

**multi_user** (each person has their own team, two layers):

```
human A ──channel──▶ team A: leader A ──▶ worker A*
human B ──channel──▶ team B: leader B ──▶ worker B*
(between team A and team B: no communication path, no shared projects, hard isolation via access control)
```

## How mode Affects Each Part of the Protocol

| Protocol part | single_user | multi_user |
|----------|------------|------------|
| NMH | human may go through the arbitrator or directly to a leader | human goes directly to **their own team's** leader |
| NMA | 🏳️ → arbitrator | 🏳️ → leader (intra-team); directional deadlock → suggest the involved humans talk directly |
| Task lifecycle | identical | identical |
| Dual-channel reporting | cross-team tasks use dual channel; single team = the originating channel is the floor | same as single team (no cross-team) |
| Cross-team | §07-HANDOFF enabled | **does not exist at the protocol level** (not "disabled" — it does not exist) |
| Team creation | arbitrator or human | human (via the binding layer's management interface) |
| Weighted majority (§09) | available for all decision classes (subject to C-3) | same (intra-team); the accountable lock-holding rule is reinforced (B-8) |

**Compilation impact**: when the binding layer compiles role identity files, cross-team fragments (handoff authorship / aggregate closure / cross-team routing) are compiled into the cluster-level coordination role only under `single_user`; no clause of §07-HANDOFF appears in `multi_user` compiled output.
