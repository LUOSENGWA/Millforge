# Cron Spec (CAP-TIMER Binding Parameters)

> This file is the CAP-TIMER binding spec for `bindings/agentteams/`. Generic-terminology discipline: see the `README.md` header.

## 1. Invariant Status (U1–U4)

| Invariant | Binding implementation | Status |
|---|---|---|
| **U1** due_at persistent | due_at stored in CAP-STATE (state files under `.qwenpaw/workspaces/default/`), clock = container clock | ✅ |
| **U2** callback idempotent | `timer-derive.sh` idempotent derivation: a repeated callback re-derives but never double-acts | ✅ |
| **U3** verdict recomputable | the due verdict is recomputed from state (read due_at + current state); **no "processed" marker stored** | ✅ |
| **U4** granularity declared | granularity = cron check period; binding-declared value = **default 5min**; windows with due_at precision ≤5min must be explicitly declared in the binding | ⚠️ (declaration item) |

## 2. Registration and Cleanup

```
register per active task (derived by timer-derive.sh):
  qwenpaw cron create --agent-id <worker> \
    --schedule "every 5m" --task "timer-check" \
    (payload = run timer-derive.sh --task-meta <ref> → due action)
granularity declaration: 5 minutes (U4); windows with due_at precision ≤5min must be declared
cleanup: task terminal state (completed/cancelled) → cron delete (prevents orphan timers)
```

- Idempotent derivation = after a container rebuild / cron loss, `timer-derive.sh` recomputes from CAP-STATE and restores missing timers (the ops form of U3).
- Orphan timer = a cron left uncleaned keeps waking checks with no task; the task terminal-state hook must `cron delete`.

## 3. Redline: Fallback Wake Only, Never Real-Time Driving

- **Heartbeat/cron only does fallback wake, never real-time driving.** Real-time driving = event triggers (message arrival) + state-machine side effects (`next_action` progression).
- Rationale: the LLM is message-driven, not flow-driven; injecting the heartbeat as a user message creates same-turn attention conflicts and token waste, and is unreliable.
- Cron roles: ① due actions (due_at reached) ② fallback re-derivation after state loss ③ timeout-window verdicts (R5/B-6 class; planned carriers in `mapping-table.md` §2.1).
- Cadence: active-task check 5min; watchdog-class (*/2) stays disabled until the planned carriers land.

## 4. Failure and Recovery

| Failure | Detection | Recovery |
|------|------|------|
| cron timer lost (container rebuild) | task has due_at but no cron | `timer-derive.sh` idempotent re-derivation (U3: verdict recomputed from state) |
| cron callback storm (state not progressing) | repeated empty wakes for the same task | check whether next_action/state is being advanced by external message triggers; manually restart the worker if needed |
| clock drift (container rebuild / host timezone change) | due_at vs actual due time diverge | always "recompute from state" for verdicts (U3); do not assume a monotonic clock; re-derive on the first round after rebuild |
