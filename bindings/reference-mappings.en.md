# Runtime Reference Mappings (non-normative)

> Version: v1.0 | License: Apache-2.0
> Provenance: migrated from the reference-mappings tables of `core/binding-contract.md` (moved out of the core contract body per the generic-terminology discipline); the table content is preserved line by line, no rewrite.
> Scope: non-normative appendix — runtime-specific names appear only in this file and in each `bindings/<runtime>/` implementation document (see the `core/binding-contract.en.md` header).
> Ownership: a **cross-binding appendix**; each binding README's "Capability Declaration" is the authoritative source for that binding's status and coverage level.

## CAP-STATE

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams (TeamHarness) | project/task meta + decision_log ref in object storage; external one-shot timer (runtime cron) | L2 |
| Bare QwenPaw | workspace JSON state file + git-like append log; runtime cron + HEARTBEAT | L2/L3 |
| claude-code | task file + CLAUDE.md pointer; Task tool + ScheduleWakeup | L2 |

## CAP-STORE

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | MinIO (object storage, `mc` CLI) + per-team bucket | L1 |
| Bare QwenPaw | workspace directory + a file-sync mechanism (declared) | L2 |
| claude-code | the repo's files/ directory + git (the fingerprint = git hash) | L1 |

## CAP-TIMER

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | runtime cron (a one-shot job per timeout; text self-contained) | L2 |
| Bare QwenPaw | runtime cron + HEARTBEAT (fallback period 10–30min) | L2/L3 |
| claude-code | ScheduleWakeup / loop scheduling | L2 |

## CAP-NOTIFY

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | Matrix room / DM (channel send) | L1 |
| Bare QwenPaw | channels send (DM) + room @mention | L1/L3 |
| claude-code | the Task result message + the parent session | L1 |

## CAP-ATTN

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | Matrix DM @human + runtime one-shot timer | L2 |
| Bare QwenPaw | DM channel + HEARTBEAT fallback + runtime cron | L2/L3 |
| claude-code | the parent session's AskUserQuestion (a persistent display surface; group chat does not apply) | L1 |

## CAP-SPAWN

| Runtime | Implementation | Tier | X4 |
|---|---|---|---|
| QwenPaw (bare) | `spawn_subagent` (fork=False; background=false) | L1 | ✅ (a versioned 3600s hard deadline — the runtime enforces it; the binding must state the version) |
| AgentTeams (Worker) | Worker = a CAP-SPAWN instance (the runtime schedules the worker container) | L1 | ✅ (the runtime's task timeout; the binding must state it) |
| claude-code | the `Task` tool (subagent) | L1 | ⚠️ (the Task tool has no built-in deadline; the binding must supplement a deadline via ScheduleWakeup + state derivation; **the supplement must be deterministic (L2), not behavioral (L3)**) |

## CAP-EXEC

| Runtime | Implementation | Tier |
|---|---|---|
| QwenPaw (bare) | execute_shell_command (container-local) | L1 |
| AgentTeams | worker container shell + docker exec (host) | L1 |
| claude-code | the `Bash` tool (sandboxed) | L1 |

## CAP-ROSTER

| Runtime | Implementation | Tier |
|---|---|---|
| AgentTeams | the team roster in object storage (team.json / agent config) | L2 |
| Bare QwenPaw | workspace roster file (roster.json) | L2 |
| claude-code | a project-level roster file | L2 |
