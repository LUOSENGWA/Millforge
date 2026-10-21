# Coding-CLI Binding (reference)

> The mapping between the Millforge core and a **coding CLI** (one-shot coding agent). **This binding is generic across coding CLIs**: product matrix = Claude Code / QwenCode / OpenCode / Codex CLI / … (Claude Code is the reference product); X1 is judged per product.
> The thinnest binding: no team/room/loop driver — it carries only the **task + spawn + acceptance evidence chain** trio.
> Applicable scenario: single-task-level coding work (spec → bounded execution → structured return → fingerprint acceptance), used as an **execution backend** for larger orchestration; it does not carry the full NMH/NMA flow.

## Index (full documents)

| Document | Content |
|------|------|
| `mapping-table.md` | CAP→mechanism mapping (combined view, per-invariant status for the 8 capabilities) + the X1 non-compliance declaration + the 7/8 legality verdict (**single source of truth**; the "CAP Mapping" table of this README is its consistent summary) |
| `skill-fragments.md` | CAP-SPAWN/CAP-EXEC skill surface (spawn surface with the X1 declaration + acceptance evidence chain + approval-tier discipline) |
| `deployment-guide.md` | topology + invocation chain + failure sequences and recovery |

## Capability Declaration (CAP-*)

| CAP | Implemented | Coverage level | Mechanism (runtime) | Limitations |
|-----|-------------|----------------|---------------------|-------------|
| CAP-STATE | ❌ | declared-degraded | state held by the parent execution unit (one-shot, no cross-run state) | cannot host state-dependent protocol surfaces alone |
| CAP-STORE | ✅ | full | coding-runs API + local workspace files + checksums | locally strongly consistent |
| CAP-TIMER | ❌ | declared-degraded | per-run `--max-wall-time` (not scheduling) | scheduling belongs to the parent |
| CAP-NOTIFY | ❌ | declared-degraded | none | notifications belong to the parent |
| CAP-ATTN | ✅ | full | `--approval-mode` ladder + ACP `request_permission` | — |
| CAP-SPAWN | ✅ | full | one-shot execution (10 flags) + `--max-wall-time` | X1 not satisfied (no session isolation) → reference, not compliant |
| CAP-EXEC | ✅ | full | CLI process execution (exit-code semantics) | — |
| CAP-ROSTER | ❌ | declared-degraded | none | single execution body |

## CAP Mapping (only 4/8 capabilities implemented = a legal partial binding)

| Capability | Mechanism | Notes |
|------|------|------|
| **CAP-SPAWN** | one-shot execution (10 flags) + `--max-wall-time` | **X4 boundedness = the reference implementation**: the runtime enforces the bound; timeout → `exit 55` (a direct implementation of the bounded_failure semantics) — this is the **only X4 natively enforced by a runtime** among the 8 capabilities (the AgentTeams binding side is still best-effort) |
| **CAP-EXEC** | CLI process execution (exit-code semantics: 0=success, 55=timeout, others=failure) | Y1/Y2/Y3 ✅; the core/scripts/ 9 scripts can call this CLI directly |
| **CAP-STORE** | coding-runs API (`GET /api/v1/coding-runs`) + local workspace files | **SIG-ARTIFACT / verification fingerprint ↔ coding-runs evidence chain**: the run's artifact manifest + checksums = the fingerprint source for the artifact ref; local read-after-write strong consistency |
| **CAP-ATTN** | `--approval-mode` ladder + ACP `request_permission` | two complementary layers (10/8 ruling): the platform approval_level (human final-review tier) × the coder-side request_permission (per-operation authorization); **the Millforge closure = the auto tier + request_permission** (10/13 deep-dive conclusion) |
| CAP-STATE | ❌ no task-level persistent state (one-shot has no cross-run state) | binding declaration: state is held by the **caller (the parent execution unit)** — the CLI only does a single step; the state machine is in the upper layer |
| CAP-TIMER | ❌ none (the bound = a single run's --max-wall-time, not scheduling) | scheduling is the parent execution unit's / upper runtime's job |
| CAP-NOTIFY | ❌ none | same as above |
| CAP-ROSTER | ❌ none | a single execution unit has no weight problem |

**Legality verdict**: 4/8 capabilities = **a partial binding** — legal as an execution backend (X4 reference implementation + evidence chain + human final-review ladder all present), but it must not independently carry the protocol surfaces requiring CAP-STATE/TIMER/NOTIFY/ROSTER (loop driver, attention routing, vote counting, fuse). The combination view (the parent execution unit completes the 4 missing capabilities) = **7/8** — CAP-SPAWN fails the X1 hard gate (no fork=False-equivalent session isolation primitive) → marked reference, not compliant (the declaration is in `mapping-table.md` §1.1).

## Three Protocol Engagements (binding-layer facts)

| # | Protocol surface | Mechanism engagement |
|---|--------|---------|
| 1 | **X4 boundedness** | one-shot timeout + `--max-wall-time` → `exit 55` = bounded_failure (runtime-enforced; the reference implementation of the X4 semantics) |
| 2 | **SIG-ARTIFACT / verification fingerprint** | the `GET /api/v1/coding-runs` artifact manifest + checksums = the artifact evidence chain (the fingerprint comparison source at acceptance) |
| 3 | **attention / human final review** | the `--approval-mode` ladder + ACP request_permission (two complementary layers: platform tier × per-operation authorization) |

## Approval-Tier Discipline (critical_delivery hard constraint)

- **simple tier**: the default `--yolo` (execution-layer approval bypass) is acceptable
- **critical_delivery (R1 class)**: **yolo forbidden** — must be `the auto tier + request_permission` or a human lock (10/13 risk note: `--yolo` default = execution-layer approval bypass; a critical delivery must not be bypassed)
- the human final-review record = a SIG-DECISION event source (the parent execution unit writes CAP-STATE)

## Deployment / Invocation

```
parent execution unit (AgentTeams worker / single-agent runtime)
  → construct the task spec (core/schemas/spec.schema.json)
  → invoke the coding-CLI (one-shot; flags include --max-wall-time + --approval-mode)
  → exit 0: read the coding-runs evidence chain → fingerprint verification (CAP-STORE T2) → accept
  → exit 55: bounded_failure (log to decision_log; escalate after ≤3 times)
  → others: failure (same as above)
```

This binding has no SOUL.md deployment (the CLI has no identity-file concept); protocol constraints are carried in three places: **task spec + invocation parameters + the parent execution unit's identity file**.
