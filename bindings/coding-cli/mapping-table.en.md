# Mechanism × Runtime Mapping Table (Claude Code / coding-CLI)

> Provenance: reference binding body, final (2026-10-20). This file is the **single source of truth** for the `bindings/coding-cli/` mapping (the `README.md` "CAP Mapping" table is its consistent summary).
> Positioning: this binding is an **execution backend** (one-shot coding CLI); the 4 missing capabilities (CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER) are provided by the **parent execution unit**; the §1 table is the **combined view** (this runtime + parent execution unit).
> Generic-word discipline: this directory is the only legitimate surface for runtime-specific names (`core/protocol/00-OVERVIEW.md` §S).

## 1. CAP → Mechanism Mapping (8-capability baseline, combined view)

| Capability | Mechanism | Invariant status | Risk / notes |
|------|------|--------------|-----------|
| **CAP-STATE** | provided by the parent execution unit (this runtime is stateless: one-shot, no cross-run state) | S1–S4 delegated to the parent (combined ✅ / standalone ❌) | the state machine is in the upper layer; the CLI only does a single step |
| **CAP-STORE** | coding-runs API (`GET /api/v1/coding-runs`) + local workspace files | T1 ✅ (artifact manifest + checksums = the fingerprint source) T2 ✅ (local read-after-write strong consistency) T3 ✅ (chained / local JSONL, provided by the parent's adapter) | SIG-ARTIFACT / verification fingerprint ↔ coding-runs evidence chain (the fingerprint comparison source at acceptance) |
| **CAP-TIMER** | provided by the parent execution unit (the bound = a single run's `--max-wall-time`, not scheduling) | U1–U4 delegated to the parent (combined ✅ / standalone ❌) | scheduling is the parent execution unit's / upper runtime's job |
| **CAP-NOTIFY** | provided by the parent execution unit | V1–V6 delegated to the parent (combined ✅ / standalone ❌) | no notification surface |
| **CAP-ATTN** | `--approval-mode` ladder + ACP `request_permission` | W2 ✅ (the human final-review record is written to the parent's CAP-STATE) W3 ⚠️ (timeout judgement delegated to the parent's CAP-TIMER) W4 ✅ (request_permission = per-operation identity authorization) W5 ⚠️ (the approval prompt = a synchronous interactive surface, not a revisitable persistent display surface; the persistent surface is the parent's responsibility) W6 ⚠️ (single surface) W7 ✅ (structured tier + structured per-operation authorization) | two complementary layers (10/8 ruling): the platform approval_level (human final-review tier) × the coder-side request_permission (per-operation authorization); the Millforge closure = the auto tier + request_permission (10/13 deep-dive conclusion) |
| **CAP-SPAWN** | one-shot execution (10 flags) + `--max-wall-time` | **X1 ❌ (hard gate)** X2 ✅ (structured return) X3 ✅ (independent process) X4 ✅ (**runtime-enforced** bound; timeout → `exit 55`) | the X1 non-compliance declaration is in §1.1; X4 = this binding's reference implementation |
| **CAP-EXEC** | CLI process execution (exit-code semantics: 0=success, 55=timeout, others=failure) | Y1 ✅ Y2 ✅ Y3 ✅ | the core/scripts/ 9 scripts run as usual (CAP-EXEC ruling item 3: a local filesystem is a legal CAP-STORE implementation) |
| **CAP-ROSTER** | provided by the parent execution unit | Z1–Z3 delegated to the parent (combined ✅ / standalone ❌) | a single execution unit has no weight problem |

### 1.1 CAP-SPAWN X1 Non-Compliance Declaration (hard gate)

**This binding's CAP-SPAWN does not satisfy X1 (context isolation, hard gate). Reasons:**

1. The runtime lacks a fork=False-equivalent session isolation primitive: its context model ① auto-injects a workspace-level memory file (CLAUDE.md) into every session; ② supports session persistence and resume (session history, `--resume`) — both are context-inheritance paths that bypass context_refs.
2. The one-shot process boundary is not a runtime-enforced isolation guarantee: its isolation depends on the caller always using one-shot + a clean workspace (caller discipline), not on runtime enforcement.
3. The contract requires X1 to be enforced by the runtime (`core/binding-contract.md`: "a runtime that does not satisfy X1 must not serve as a legal binding"). Caller discipline ≠ a runtime guarantee → the hard gate is not met.

Boundary note: the one-shot invocation path itself is X1-compliant (a process-level fresh context) and can be used as an execution backend under the parent execution unit's caller discipline; but the binding legality verdict follows the **capability-level (runtime-enforced)** criterion → CAP-SPAWN is non-compliant.

**Legality verdict**: the standalone view = 4/8 capabilities (a partial binding; legal as an execution backend, see the README); the combined view (the parent execution unit provides CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER) = **7/8** — 7 of the 8 capabilities are satisfied; CAP-SPAWN fails the X1 hard gate (see §1.1). **Marked reference, not compliant** (`core/binding-contract.md` § binding-legality verdict, condition 1: the X1/X4 hard gates). Note: X4 is conversely this binding's strength — it is the only runtime-natively-enforced X4 among the three reference bindings (the agentteams binding side is still best-effort).

## 2. Mechanism → Execution Carrier (protocol engagement surfaces, 4 items)

| Protocol surface | Execution carrier | Where state lives | Triggerer |
|---|---|---|---|
| X4 boundedness | one-shot `--max-wall-time` (runtime-enforced; timeout → `exit 55`) | not applicable (stateless; the exit code = the judgement) | runtime timeout |
| SIG-ARTIFACT / verification fingerprint | coding-runs API artifact manifest + checksums | local workspace files; the ref is recorded in the parent's CAP-STATE | the acceptance flow (parent execution unit) |
| human final review | `--approval-mode` ladder + ACP `request_permission` | the parent's CAP-STATE (the human final-review record = a SIG-DECISION event source) | per-operation authorization / final review |
| deterministic scripts | the core/scripts/ 9 scripts (invoked by the parent execution unit) | local files (CAP-STORE = local filesystem) | the parent execution unit's skill |

[NO-CARRIER] gaps = the 4 parent-provided capabilities (CAP-STATE / CAP-TIMER / CAP-NOTIFY / CAP-ROSTER) — this binding provides no carrier for them; the protocol surfaces depending on these 4 capabilities (loop driver, attention routing, vote counting, fuse) must be carried by the parent execution unit.

## 3. Primitive Mapping

| Primitive | Mechanism |
|------|------|
| human | the parent execution unit's channel + the human final review (approval prompt) |
| agent | the parent execution unit (this runtime is an execution backend, not a protocol agent) |
| leader | not applicable (provided by the parent execution unit) |
| worker | this CLI's one-shot execution (the execution surface only) |
| arbitrator | not applicable |
| room | not applicable |
| project | not applicable |
| task | the parent execution unit's CAP-STATE |
| artifact | the coding-runs artifact manifest + local workspace files |
| decision node | the parent execution unit's decision_log |
| channel | not applicable (no notification surface; the parent execution unit's surface) |
| mode | not applicable (a single execution unit) |
| attention | `--approval-mode` ladder + ACP `request_permission` (human final review) |
| loop | not applicable (no CAP-TIMER) |
| signal | the exit code (0 / 55 / others) + the coding-runs evidence chain |
