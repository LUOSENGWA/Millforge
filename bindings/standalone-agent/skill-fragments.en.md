# Skill Fragments (CAP-SPAWN / CAP-EXEC Binding Implementation)

> This file is the skill-surface specification of `bindings/standalone-agent/`; the mapping is in `mapping-table.md`.
> Generic-word discipline: this directory is the only legitimate surface for runtime-specific names (`core/protocol/00-OVERVIEW.md` §S).

## 1. In-Tree Script List (core/scripts/, 9 items)

The scripts ship with the core (no runtime rewrite required); exit-code semantics are in each script's header comment (CAP-EXEC Y2).

| Script | Mechanism | Binding trigger surface (this binding) |
|------|------|-----------|
| `aggregate-vote.sh` | R2 weighted-majority voting | leader-side agent skill; triggered on attention timeout or when enough votes arrive |
| `validate-decision-log.sh` | B-1 layer-1 schema validation | parent agent skill, executed **before acceptance** (not at spawn return — spawn is an LLM and cannot self-validate) |
| `detect-conflict.py` | B-2 conflict detection Step 1–3 (no LLM, pure field comparison) | parent agent skill, called after B-1 layer 1 passes; candidate conflict pairs written to `decisions/<task_id>/conflict-candidates.json` (local path) |
| `contract-revalidate.sh` | B-3 revalidation (semver + fingerprint + compatibility report) | parent agent skill before acceptance; or the critic layer 3 falls back to it on a fingerprint mismatch |
| `attention-stall.sh` | B-5 attention stall detection | `qwenpaw cron` scan surface (spec in `../agentteams/cron-spec.md`); the count is written to task meta `attention_stall_count` (local JSON) |
| `verification-mismatch-window.sh` | B-6 verification_mismatch count + 24h window | `qwenpaw cron` scan surface; the 24h timeout keeps the original spec |
| `saga-compensate.py` | B-10 saga compensation directive generation | reads the dependency graph + forward operation log → reverse compensation sequence; triggered by the protocol layer / leader |
| `consistency-check.py` | C-3 rule-layer consistency (field-level / enum-level binary comparison) | called before the R6 answer write-back; escalates to the restricted-classification spawn only when the rule layer cannot decide |
| `timer-derive.sh` | CAP-TIMER idempotent derivation | `qwenpaw cron` callback payload; see `../agentteams/cron-spec.md` |

**8 core-script I/O discipline**: they only touch local files / stdin / stdout and **must not invoke any object-storage CLI** — this binding has no object storage; I/O = local filesystem / shared volume (a legal CAP-STORE implementation).

## 2. Spawn Fragment (CAP-SPAWN, production-verified)

- **The worker native session = scheduling + review only; it performs no implementation work.** All implementation work goes into `spawn_subagent(fork=False)` (fresh session, does not inherit the parent session — **fork=True violates X1**).
- This mechanism is **production-verified** on this binding's runtime (X1 ✅).
- Structured return (X2); state is passed via the return value (X3); the parent session does not read the child session's context.
- X4 (enforced bound) = upstream gap (same as the agentteams binding, PR line); until it lands, the binding layer uses the timeout parameter best-effort (not enforced); a hang with no return is handled with `bounded_failure` semantics, escalation after 3 times.

## 3. Review-Chain Fragment (B-1 three-layer validation, order not interchangeable)

```
spawn returns
  → layer 1: validate-decision-log.sh (schema field validation, parent agent, before acceptance)
  → layer 2: detect-conflict.py (pure field comparison, outputs candidate conflict pairs)
  → layer 3: the critic acceptance script checks the fingerprint (authority = local `decisions/<task_id>/<spawn_id>.decision.json`;
             task meta only stores the {ref, sha256_8, validated} index)
```

- Validation is not left to the LLM: layers 1/2 are deterministic scripts; the only LLM participation = the **restricted-classification spawn** when the C-3 rule layer cannot decide (it only outputs `{contradict, criterion_id, reason}`, not free generation).
- Validation is not left to the spawn-return moment: spawn is an LLM, self-validation is invalid — validation runs **before the parent agent accepts**.

## 4. Heartbeat / cron Fragment

One-line pointer: fallback-wake semantics, registration/cleanup, U1–U4, redlines = the same as the agentteams binding (see `../agentteams/cron-spec.md`). The skill surface only supplies the cron callback payloads (`timer-derive.sh` / `attention-stall.sh` / `verification-mismatch-window.sh`).
