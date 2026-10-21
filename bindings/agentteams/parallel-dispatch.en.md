# Parallel Task Dispatch Scene Contract (M4)

> Scene capability = **composite** of CAP-STATE + CAP-STORE + CAP-TIMER + CAP-NOTIFY + CAP-EXEC + CAP-SPAWN: a control plane dispatches N tasks in parallel; each task gets an isolated executor + an isolated working directory; state / receipts / notifications are all on disk and machine-verifiable.
> This document is a **binding fragment** for the AgentTeams line: the 7 invariants are runtime-agnostic (any binding satisfying the 8 capabilities can adopt the scene). Each invariant carries a concrete AgentTeams anchor (file:line, verified by direct read) + seed evidence.
> Re-runnable seed: `golden-tests/fixtures/parallel-9/` (10 task state.json + 7 inbox.jsonl transition events, normalized from a nine-task pilot).
> Executable assertions: `golden-tests/tests/test_parallel_dispatch_contract.py` (`make contract`).
> Budget stance: **no budget by default** (enforced only on explicit declaration; see `core/protocol/10-LOOP.en.md`); the rc=55 / rc=137 mechanisms are retained as a zero-cost backstop.

## 0. Seed data (fixtures/parallel-9/)

| Task | Terminal state | exit_code | wall_s | Notes |
|------|----------------|-----------|--------|-------|
| P2a / P2b / P2e | running | — | — | In flight: session_id + pid + updated_at all present (watchdog inputs) |
| P2c / P2d | blocked-by-gate | — | — | Rejected at dispatch: no session_id / pid / started_at (zero execution cost) |
| P3b / P3k | done | 0 | 63 / 59 | Normal completion |
| P4b | failed-budget | 55 | 46 | X4 bounded failure (rc=55 under an explicitly declared budget) |
| P4k | done | 0 | 251 | Normal completion (long task) |
| P4x | killed | 137 | 30 | Externally killed; terminal state still persisted |

Terminal set (closed): `done` / `failed-budget` / `killed` / `blocked-by-gate`; in-flight: `running`.

## 1. Seven invariants (PD-1 … PD-7)

### PD-1 Single source of truth on disk (CAP-STATE S1/S2/S3)

**Invariant**: task state is the single source of truth; it must be written atomically (tmp + rename) and be re-readable at any time; transition events are append-only (inbox); dashboards / notifications / watchdogs are **derived views**, never a second data source.

**AgentTeams anchor**:
- The attention record `{kind, question≤500, attempt, requestedAt, resolved, eventId}` is written to task state first (sync-first: the caller is told "closed" only after shared-storage sync is confirmed; sync failure = `retryable: true`, the notification is retained, the state does not blow up) — `plugins/teamharness/mcp/server.py:6076–6087` (retryable block), `:6215–6227` (record write + `record["eventId"]` backfill)
- Seed evidence: `parallel-9/*/state.json` — one state file per task; `inbox.jsonl` — append-only, 7 events; readers (watchdog/dashboard) derive only from disk

### PD-2 Dispatch-time conflict gate (new invariant)

**Invariant**: at dispatch time, if a candidate task's `files_to_touch` intersects any active task's → **reject the dispatch** (write a `blocked-by-gate` state + an inbox event, with the reason); rejection happens **before spawn** — **zero execution cost** (no session created, no tokens spent).

**AgentTeams anchor (adjacent semantics + gap statement)**:
- Idempotent dispatch-state foundation: re-delegation compares via `_canonical_assignee` — re-dispatch to the same assignee reuses the existing state (no duplicate event); only a different assignee raises a new notification — `plugins/teamharness/mcp/server.py:2994` (function), `:5421` (comparison, #1324)
- **Gap**: the conflict gate itself is a pre-dispatch gate at the protocol layer (new in this contract); the AgentTeams upstream has no dispatch-time equivalent. The two correct rejections in the seed (P2c/P2d, `detail: "files_to_touch overlap with active task"`) come from the control-plane dispatch tool, not from this runtime. A runtime adopting this contract must implement the gate (or declare the degradation explicitly in its binding).

### PD-3 Terminal state before cleanup

**Invariant**: cleanup (deregister: release session / delete timers) is allowed only **after** the terminal state is written to state + inbox; cleanup failure is non-fatal — the truth is already on disk; cleanup is only view convergence.

**AgentTeams anchor**:
- Sync-first, same as PD-1: the terminal/resolved state must land in shared storage **before** the caller is notified; the failure path retains the notification and marks it `retryable` — `plugins/teamharness/mcp/server.py:6076–6087`
- The cleanup action in this binding = task terminal → `cron delete` (see `cron-spec.md`); ordering redline = state/inbox first, cron after
- Seed evidence: all 5 terminal tasks (P3b/P3k/P4b/P4k/P4x) have `finished_at` in state.json **and** a matching inbox event; cleanup only happens after both are present

### PD-4 The receipt is a first-class artifact (CAP-STORE T1/T2/T5)

**Invariant**: a terminal task must produce a **structured receipt**: `status` enum + `exit_code` + `wall_s` (+ `files_to_touch` / receipt ref / worktree / tokens, per binding capability); `self_check` per acceptance item; `known_gaps` declared explicitly. The receipt is addressable, fingerprintable, machine-verifiable — **bounded failures (rc=55/137) are first-class terminal states**, not error codes.

**AgentTeams anchor**:
- Coding-runs read contract (run records: status / exit_code / wall readable via API — one API, one dashboard) — `agentteams-controller/internal/server/http.go:162–163` (`GET /api/v1/coding-runs`, `GET /api/v1/coding-runs/{taskID}/runs/{run}`, #1365/#1381)
- False-completion guard (receipts must be honest: a no-output turn is marked "no output this turn", never "completed") — `plugins/agentteams-matrix-channel/agentteams_matrix/channel.py:4510` (#1320)
- Task artifact endpoint (addressable surface for receipts) — `agentteams-controller/internal/server/http.go:151`
- Seed evidence: all 5 executed terminal tasks carry `exit_code` + `wall_s`; P4b `rc=55` (bounded budget failure), P4x `rc=137` (killed)

### PD-5 Notifications are 3-line pointers (CAP-NOTIFY; tiering clause in `core/protocol/09-GOVERNANCE.en.md` §8)

**Invariant**: a task-transition notification = a fixed 3 lines (task id + terminal state + pointer), **no payload** (no inlined artifact content), **no reply required**, **no questions**; full content is always obtained by reading state / receipt (pointer form). The human tier uses a fixed 3-line plain-language format, and failure states must enter the human tier too (no silent failures).

**AgentTeams anchor (current state + gap)**:
- Current state: `_send_attention_notification` — single-path Matrix text that **inlines question≤500** (payload + question form — the two ways this invariant is violated) — `plugins/teamharness/mcp/server.py:5205`; idempotent txn `attention-{task_id}-{kind}-{attempt}` — `:5253`
- **Gap**: AgentTeams notifications are currently in "question + inlined preview" form, not converged to the 3-line pointer tier format; this binding declares the gap in `compliance.json` / README §4; until upstream converges, the protocol must not assume a notification can carry a full payload

### PD-6 Watchdog backstop (CAP-TIMER U3/U5)

**Invariant**: a watchdog scans disk on a declared period (binding granularity): `updated_at` timed out while pid is alive = **stall** (human-visible alert); pid dead while state is non-terminal = **crash** (re-dispatch or escalate). Judgments are derived by a deterministic script from CAP-STATE (idempotent re-derivation, U3); it must not rely on "remembering the last check".

**AgentTeams anchor**:
- Project event feed (read-only transition history; the watchdog can cross-check state against history) — `agentteams-controller/internal/server/http.go:156` (`GET /api/v1/projects/{id}/events`, #1233)
- `timer-derive.sh` (core reference implementation, CAP-TIMER U3 idempotent re-derivation) + this binding's cron period = declared scan granularity (`cron-spec.md`, default 5min, U4)
- Seed evidence: running tasks (P2a/P2b/P2e) all carry a numeric `pid` + `updated_at` (both watchdog inputs present); terminal tasks have inbox `ts` == state `finished_at` (transitions derivable and reconcilable)

### PD-7 Isolation = self-built worktree (CAP-SPAWN X1)

**Invariant**: each task runs in a **self-built worktree** (own branch + own directory); executors get a fresh context (no parent conversation history inherited — X1 hard gate); cross-task visibility is only via state / receipts (disk), never a shared working directory.

**AgentTeams anchor**:
- Unique `session_id` per task (seed: 8 spawned tasks = 8 distinct UUIDs) + the fresh-session mechanism (this binding's CAP-SPAWN = `fork=False`, see `README.en.md` §1; fork=True violates X1)
- The worktree tooling (`git worktree add`) and branch naming = **binding parameters** (control-plane dispatch tool details); the X1 context-isolation semantics are at the protocol layer. The seed carries only the verifiable part (session_id uniqueness)

## 2. Adoption criteria (for any runtime)

1. PD-1…PD-7 implemented one by one, or declared degraded in `compliance.json` gaps (undeclared = illegal binding, see `core/binding-contract.en.md`)
2. The seed fixture is re-runnable: `test_parallel_dispatch_contract.py` is fully green on `golden-tests/fixtures/parallel-9/`
3. The terminal set is closed (§0); adding a terminal state requires updating this document + the fixture + the tests first (runtimes must not invent private states)

## 3. Interface to M5 (notification tiering)

PD-5 is the **pointer-form** constraint; `core/protocol/09-GOVERNANCE.en.md` §8 is the **tier declaration** constraint (machine / agent / human). The two are orthogonal: the same transition event is delivered to different surfaces per tier, and every surface's payload must satisfy PD-5 (3 lines, no payload, no questions).
