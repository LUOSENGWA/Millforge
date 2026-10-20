# Skill Fragments (CAP-SPAWN / CAP-EXEC Binding Implementation)

> Provenance: reference binding body, final (2026-10-20). This file is the skill-surface specification of `bindings/coding-cli/`; the mapping is in `mapping-table.md`.
> Positioning: this binding is an **execution backend** (one-shot coding CLI), not a protocol agent — the skill surface = the spawn surface (with the X1 non-compliance declaration) + the acceptance evidence chain + the approval tiers.

## 1. Script Surface (CAP-EXEC)

- This CLI is not the direct executor of the scripts: the `core/scripts/` 9 scripts are invoked by the **parent execution unit** (CAP-EXEC ruling item 3: in a runtime without object storage / group chat, the scripts run as usual — input/output paths are resolved by the caller per the CAP-STORE ref; a local filesystem is a legal CAP-STORE implementation).
- Exit-code semantics: 0=success, 55=timeout (bounded_failure), others=failure (Y2).
- 8 core-script I/O discipline: they only touch local files / stdin / stdout and **must not invoke any object-storage CLI**.

## 2. Spawn Surface (CAP-SPAWN — X1 non-compliance declaration)

- **X1 (context isolation, hard gate) is not satisfied**: the runtime lacks a fork=False-equivalent session isolation primitive — the auto-injection of the workspace-level memory file (CLAUDE.md) + session persistence/resume (`--resume`) are both context-inheritance paths that bypass context_refs; the one-shot process boundary depends on caller discipline (always one-shot + a clean workspace), not on runtime enforcement. The contract requires X1 to be enforced by the runtime → the hard gate is not met (details and the verdict criterion are in `mapping-table.md` §1.1).
- Consequence: this binding = **7/8** (combined view), marked reference, not compliant.
- The invocation path (X1-compliant under caller discipline): one-shot (10 flags) + `--max-wall-time`; X2 ✅ structured return; X3 ✅ process independence; X4 ✅ **runtime-enforced** bound, timeout → `exit 55` = bounded_failure (the only runtime-natively-enforced X4 among the three reference bindings; the agentteams binding side is still best-effort).

## 3. Acceptance / Review-Chain Fragment (the SIG-ARTIFACT evidence chain)

```
CLI exit 0
  → read the coding-runs evidence chain (GET /api/v1/coding-runs: artifact manifest + checksums)
  → fingerprint verification (CAP-STORE T2: the checksums = the artifact ref fingerprint source)
  → the three-layer review chain (executed by the parent execution unit, order not interchangeable):
      layer 1: validate-decision-log.sh (schema validation)
      layer 2: detect-conflict.py (pure field comparison)
      layer 3: the critic checks the fingerprint (authority = the parent's CAP-STORE artifact)
  → accept; the acceptance evidence chain is written to the parent's CAP-STATE
exit 55: bounded_failure (logged to decision_log; escalation after ≤3 times)
other exit: failure (same as above)
```

- Validation is not left to the CLI: the CLI is an LLM execution unit; self-validation is invalid — validation runs **before the parent execution unit accepts**.
- Validation is not left to the single-return moment: the fingerprint comparison source = the coding-runs evidence chain (T2: consume only after confirmation).

## 4. Approval Fragment (CAP-ATTN, human final review)

- Two complementary layers: the platform `--approval-mode` ladder (human final-review tier) × the coder-side ACP `request_permission` (per-operation authorization).
- The Millforge closure = **the auto tier + request_permission**.
- Approval-tier discipline (critical_delivery hard constraint):
  - simple tier: the default `--yolo` (execution-layer approval bypass) is acceptable
  - critical_delivery (R1 class): **yolo forbidden** — it must be `the auto tier + request_permission` or a human lock
  - the human final-review record = a SIG-DECISION event source (the parent execution unit writes CAP-STATE)

## 5. cron / loop

not applicable (this binding has no CAP-TIMER; scheduling is the parent execution unit's job).
