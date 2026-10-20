# Skill Fragments (CAP-SPAWN / CAP-EXEC Binding Implementation)

> Provenance: runtime-binding review (round 4, 2026-10-18) finalized + v2.40 context-isolation ruling + in-tree `core/scripts/` verification (9 files). This file is the skill-surface spec for `bindings/agentteams/`. Generic-terminology discipline: see the `README.md` header.
> Verification note: the draft (round 4) marked B-5/B-6 as [NO-CARRIER] with a planned `nmh-watchdog.sh` new mode; in-tree verification shows both are already standalone scripts (`attention-stall.sh` / `verification-mismatch-window.sh`). This file follows the in-tree state; the draft's plan is preserved only in `mapping-table.md` §2.1.

## 1. In-Tree Script Inventory (core/scripts/, 9 files)

Scripts ship with the core (the runtime is not asked to rewrite them); exit-code semantics: see each script's header comment (CAP-EXEC Y2).

| Script | Mechanism | Binding trigger surface |
|------|------|-----------|
| `aggregate-vote.sh` | R2 weighted-majority voting | Leader-side skill; triggered on attention timeout or sufficient votes |
| `validate-decision-log.sh` | B-1 layer-1 schema check | parent Worker skill, **before acceptance** (not at spawn return — a spawn is an LLM and cannot self-validate) |
| `detect-conflict.py` | B-2 conflict detection Step 1–3 (no LLM, pure field comparison) | parent Worker skill after B-1 layer 1 passes; candidate conflict pairs written to MinIO `decisions/<task_id>/conflict-candidates.json` |
| `contract-revalidate.sh` | B-3 revalidation (semver + fingerprint + compatibility report) | parent Worker before acceptance; or critic layer-3 fallback on fingerprint mismatch |
| `attention-stall.sh` | B-5 attention stall detection | cron scan surface (see `cron-spec.md`); count written to task meta `attention_stall_count` |
| `verification-mismatch-window.sh` | B-6 verification_mismatch counting + 24h window | cron scan surface; 24h timeout keeps the original spec |
| `saga-compensate.py` | B-10 saga compensation directive generation | reads dependency graph + forward operation log → reverse compensation sequence; triggered by protocol layer/Leader |
| `consistency-check.py` | C-3 rule-layer consistency (field-level/enum-level binary comparison) | invoked before R6 answer write-back; escalates to a bounded classification spawn only when the rule layer cannot decide |
| `timer-derive.sh` | CAP-TIMER idempotent derivation | `qwenpaw cron` callback payload; see `cron-spec.md` |

**8-core-script I/O discipline**: local files / stdin / stdout only; **no object-storage CLI calls** (`mc` etc.); all object-storage I/O is owned by the CAP-STORE adapter (audit table in `rustfs-migration.md` §4).

## 2. Spawn Fragments (CAP-SPAWN, v2.40 context-isolation ruling)

- **The worker native session = scheduling + review only; it performs no implementation work.** All implementation work goes to `spawn_subagent(fork=False)` (fresh session, no parent-session inheritance — **fork=True violates X1**).
- Structured return (X2); state travels via the return value (X3); the parent session never reads child-session context.
- X4 (enforced bound) = upstream gap (PR line); until it merges, the binding layer uses the timeout parameter best-effort (not enforced); a hung spawn with no return follows `bounded_failure` semantics — escalate after 3.
- Three-tier cache cooperation (binding-layer fact): MinIO artifacts (spawn reads context) → runtime offload (persisted during execution) → model-server KV Cache (hardware backstop).

## 3. Review-Chain Fragments (B-1 three-layer check, order is fixed)

```
spawn returns
  → layer 1: validate-decision-log.sh (schema field check, parent Worker, before acceptance)
  → layer 2: detect-conflict.py (pure field comparison, emits candidate conflict pairs)
  → layer 3: critic acceptance script checks the fingerprint (authoritative = MinIO decisions/<task_id>/<spawn_id>.decision.json;
             task meta stores only the {ref, sha256_8, validated} index)
```

- Checks never live in an LLM: layers 1/2 are deterministic scripts; the only LLM involvement = the **bounded classification spawn** when the C-3 rule layer cannot decide (outputs only `{contradict, criterion_id, reason}`, not free generation).
- Checks never live at spawn-return time: a spawn is an LLM and self-validation is void — checks run **before the parent Worker's acceptance**.

## 4. Heartbeat/cron Fragments

One-line pointer: fallback-wake semantics, registration/cleanup, U1–U4, and the redline = see `cron-spec.md`. The skill surface only supplies the cron callback payloads (`timer-derive.sh` / `attention-stall.sh` / `verification-mismatch-window.sh`).

## 5. Planned Carriers (not implemented — do not cite as current)

`nmh-watchdog.sh` (R5 reopen-window mode) / `emit-class-mismatch.sh` / `write-contract-snapshot.sh` / `write-aggregation-result.sh` / `write-decision-record.sh` — see `mapping-table.md` §2.1. Until implemented, the corresponding mechanisms run as "protocol-layer trigger + manual fallback".
