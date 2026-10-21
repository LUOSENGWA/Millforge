# AgentTeams Reference Binding

> The mapping between the Millforge core and the **AgentTeams orchestration layer** (controller + worker pool). **This binding is runtime-agnostic**: control plane = AgentTeams; worker runtime is replaceable (reference runtime: QwenPaw; also copaw / OpenClaw / Hermes).
> This binding is a **reference binding, not the only binding** — protocol legality is judged by the 8 capabilities in `core/binding-contract.md`;
> any runtime satisfying the 8 capabilities + invariants constitutes a legal binding (`bindings/standalone-agent` and `bindings/coding-cli` are two other reference implementations).
> **Generic-terminology discipline**: this directory is the **only legal surface** for runtime-specific names (spawn_subagent / QwenPaw cron / channels send / mc / Matrix / MinIO-RustFS / dashboard).
> **Status: reference — not compliant** (`compliance.json`: X4 not enforced; CAP-NOTIFY V3/V5/V6 gaps). Legality: `core/binding-contract.md` §5.


## Index (full documents)

| Document | Content |
|------|------|
| `mapping-table.md` | CAP→mechanism mapping + 14 mechanisms × execution carriers + primitive mapping (**single source of truth**; README §1 is its consistent summary) |
| `skill-fragments.md` | CAP-SPAWN/CAP-EXEC skill surface (9 in-tree scripts + spawn fragments + three-layer review chain) |
| `cron-spec.md` | CAP-TIMER binding spec (U1–U4 + registration/cleanup + fallback-wake redline) |
| `deployment-guide.md` | topology + compile→deploy chain + filesync post-write protocol + failure sequences & recovery |
| `s3-storage.md` | S3 object-storage semantics verification (T1–T3) + CAS positioning + storage_adapter enum + 8-script audit |

> The runtime-specific-name mapping (**cross-binding** non-normative appendix) is at [`../reference-mappings.md`](../reference-mappings.md) (English twin `.en.md`).

## Capability Declaration (CAP-*)

| CAP | Implemented | Coverage level | Mechanism (runtime) | Limitations |
|-----|-------------|----------------|---------------------|-------------|
| CAP-STATE | ✅ | full | worker-local JSON + file-lock CAS; task-level state may live in TeamHarness task meta | container rebuild needs object-storage backup (S4) |
| CAP-STORE | ✅ | full | S3-compatible object storage (MinIO / RustFS) + client-side sha256 | no same-object append on hot keys |
| CAP-TIMER | ✅ | full | runtime cron + `timer-derive.sh` idempotent derivation | granularity = cron period (default 5 min) |
| CAP-NOTIFY | ⚠️ | partial | channel messages + Room @mention | V3/V5/V6 gaps (see §4) |
| CAP-ATTN | ✅ | full | DM Room persistent display surface + state file | single surface (no multi-surface sync) |
| CAP-SPAWN | ✅ | full | fresh-session sub-execution (`fork=False`) | X4 bound best-effort (not enforced) |
| CAP-EXEC | ✅ | full | worker container shell (venv pip) | scripts ship with the core |
| CAP-ROSTER | ✅ | full | Team CRD / agent-config roster | Z2 needs explicit configuration |

## 1. CAP → Mechanism Mapping

| Capability | AgentTeams/QwenPaw mechanism | Invariant status | Risks/notes |
|------|------------------------|--------------|-----------|
| **CAP-STATE** | worker-container-local JSON (state files under `.qwenpaw/workspaces/default/`) + file-lock CAS; task-level state may additionally live in TeamHarness task meta | S1 ✅ (local-disk persistent) S2 ✅ (file lock; single-node single-writer) S3 ✅ (JSONL append) S4 ⚠️ | container rebuild loses state → **state must be synced to a MinIO backup** (see §3 filesync); before the `mc` push confirmation, it is not durable (T2 execution detail) |
| **CAP-STORE** | MinIO / RustFS (S3-compatible), path addressing; `mc cp` writes | T1 ✅ (**client-side sha256**; ETag is not a fingerprint) T2 ✅ (S3 strong read-after-write consistency + sync-layer uploaded receipt) T3 ✅ (**chained simulation**: `decisions/<task>/<seq>.json` new-object chain; no same-key append) | hot keys never appended to the same object (S3 conditional PUT serialization); CAP-STATE must not simulate CAS via object-store conditional PUT (object level ≠ key-value level) |
| **CAP-TIMER** | QwenPaw cron (`qwenpaw cron create --agent-id ...`) + `timer-derive.sh` idempotent derivation | U1 ✅ (due_at in CAP-STATE, container clock) U2 ✅ (callback idempotently re-derives) U3 ✅ (verdict recomputed from state; no "processed" marker stored) U4 ⚠️ granularity = cron check period (binding-declared; default 5min) | **heartbeat/cron only does fallback wake, never real-time driving** ; real-time driving = event triggers + state-machine side effects |
| **CAP-NOTIFY** | QwenPaw `channels send` (QQ/Matrix channels) + Matrix Room @mention | V1 ✅ (notifications not persisted as state) V2 ✅ (state in CAP-STATE, rebuildable) V3 ⚠️ **known defect: allowlist silent drop leaves no gaps** (#160/#169 production-verified) V4 ✅ (message_id dedup) V5 ⚠️ no code-level event surface V6 ⚠️ delivered ≠ accepted | **V3/V5/V6 gaps are known implementation gaps (closed by later versions)**; until they close, the binding marks "partially satisfied"; the protocol must not rely on gaps being absent |
| **CAP-ATTN** | QwenPaw channel DM (DM Room) + local state file recording replies | W1 ✅ (idempotency key in filename/state) W2 ✅ (reply lands in CAP-STATE) W3 ✅ (timeout_at in state, cron verdict) W4 ⚠️ **DM identity = Matrix user_id mapping (usable)**; group-chat @mention must not resolve (S4) W5 ✅ (DM Room = persistent display surface: persists + revisitable) W6 ⚠️ no multi-surface sync (single surface OK) W7 ✅ (structured options + option_id) | group chat not being a response surface is a **protocol redline** (S4); the binding-layer bot must steer to DM |
| **CAP-SPAWN** | QwenPaw `spawn_subagent(fork=False)` (fresh session) | X1 ✅ (fork=False = does not inherit the parent session; **fork=True violates X1**) X2 ✅ (structured return) X3 ✅ (state via return value) X4 ⚠️ **no enforced bound = upstream gap** | context isolation: the worker native session only schedules + reviews; all implementation goes to spawns; until X4 bounds are enforced, the binding layer uses the timeout parameter best-effort (not enforced) |
| **CAP-EXEC** | shell inside the worker container (`/opt/venv/copaw/bin/python3` + stdlib); **pip is always the venv version** (runtime constraint) | Y1 ✅ Y2 ✅ (exit-code semantics see the core/scripts headers) Y3 ✅ | scripts ship with the core (the runtime is not asked to rewrite them); the **scheduling part** of the watchdog is this binding's implementation (cron + state-file paths); the logic part = the core reference implementation |
| **CAP-ROSTER** | Team CRD / agent config (roster file: member_id/role/weight) | Z1 ✅ (role weights) Z2 ⚠️ (accountable is explicitly configured; ABSENT must be explicitly returned by the binding layer) Z3 ✅ (delegation chain = config change records) | roster change = R1 human-locked; allowlist config changes must be verified to take effect (the permission-wall fuse companion) |

**Legality verdict**: this binding is currently **7.5/8 satisfied** — CAP-NOTIFY V3/V5/V6 partially satisfied (until the upstream PR line closes); CAP-SPAWN X4 best-effort, not enforced. **Marked reference, not compliant, until the gaps close + X4 enforced bounds land.**

## 2. Primitive Mapping (each §01 primitive → mechanism)

| Primitive | Mechanism |
|------|------|
| human | Matrix user (the human entry in the roster, e.g. `@human-a`/`@human-b`) + IM channel |
| agent | QwenPaw Worker container (`python3 -m copaw_worker.run_copaw_app app`, qwenpaw runtime) |
| leader | Worker role instance (the skeleton/leader compiled artifact deployed to `.qwenpaw/workspaces/default/`) |
| worker | Worker role instance + spawn sub-execution units |
| arbitrator | Manager container (`agentteams-manager`, qwenpaw runtime, single_user only) |
| room | Matrix Room (team room / project room / DM Room) |
| project | TeamHarness project + MinIO project space `{proj}/brief.md+meta+artifacts/` |
| task | TeamHarness task + task meta (CAP-STATE) |
| artifact | MinIO object (path contract + client sha256 fingerprint) |
| decision node | NMH document decision tree + decision_log (MinIO `decisions/`) |
| channel | the originating QQ channel / console |
| mode | single_user (production status quo: one human, one cluster) |
| attention | DM Room + state file (§CAP-ATTN) |
| loop | CAP-STATE loop_state + cron fallback + spawn X4 |
| signal | CAP-STATE event_type (closed list) + channel message markers (derived view) |

## 3. Deployment Guide (this binding only)

### 3.1 Compile → Deploy Chain

```
millforge compile <team.json> --out /tmp/build/<team>
  → <role>.soul.md × N          # identity files (layer 0)
  → fragments/protocol-*.md     # layer 1 (trigger-loaded)
  → fragments/industry-*.md
  → spawn-specs/*.md            # layer 2 (spawn-injected)
  → core/scripts/ 9 scripts (ship with the core; executable in-container)
Deploy (per role):
  1. docker cp <role>.soul.md → container .qwenpaw/workspaces/default/SOUL.md
     + workspace-root SOUL.md (both locations! after docker restart the runtime restores old files — deploy after the restart, not before)
  2. fragments/ + spawn-specs/ → container workspace protocols/ directory (symlinks prevent overwrite)
  3. MinIO sync: mc cp → object storage (only complete once the filesync confirmation has the uploaded receipt; T2 execution detail)
  4. verify: docker exec read-back + line count check (wc -l, path as an argument)
```

### 3.2 Cron Specification (CAP-TIMER binding parameters)

```
registered per active task (derived by timer-derive.sh):
  qwenpaw cron create --agent-id <worker> \
    --schedule "every 5m" --task "timer-check" \
    (payload = run timer-derive.sh --task-meta <ref> → the due action)
granularity declaration: 5 minutes (U4); windows with due_at precision ≤5min must be declared
cleanup: task terminal state (completed/cancelled) → cron delete (prevent orphan timers)
```

### 3.3 filesync Sync Layer (CAP-STORE T2 execution-detail binding parameters)

- container workspace ↔ MinIO sync = push_loop (async) + startup mirror_all
- **post-write protocol (race protection)**: write → wait ≥45–60s (verify disk + the "push uploaded" log line) → only then allow restart/consume (2026-09 JEV evidence: a quick restart after a write was rolled back by mirror_all)
- the uploaded receipt = the push log line `push uploaded .../<file>` (polled by the binding layer)

### 3.4 Failure Sequences & Recovery (T5 production-verified)

| Failure | Detection | Recovery |
|------|------|------|
| Worker container anomaly (Internal error) | docker logs ERROR | restart → re-dispatch (3 times → escalate); **stale pydantic version = workspace startup failure** (check the version with the venv pip, #176) |
| state write to MinIO unconfirmed | no "uploaded" in the push log | do not consume the ref (T2); re-push + confirm |
| allowlist silent interception | the message vanishes with no error log | compare the agent.json access control (#160/#169); after restart, verify allow_from contains the human |
| cron timer lost (container rebuild) | task has due_at but no cron | timer-derive idempotent re-derivation (U3: verdict recomputed from state) |
| spawn hangs without return | X4 bound (best-effort) | bounded_failure semantics; 3 times → escalate |
| SOUL.md rolled back after restart | file mtime/line count | redeploy both locations (after the restart) |

## 4. Known Gaps (closed by later versions)

| Gap | Protocol clause affected |
|-----|--------------------------|
| delivery_report does not report gaps (allowlist silent drop unobservable) | CAP-NOTIFY V3 |
| No code-level event subscription surface | CAP-NOTIFY V5 |
| delivered / accepted not distinguished | CAP-NOTIFY V6 |
| Dashboard todo list (a second persistent display surface) | CAP-ATTN W5 |
| IM card (optional extra surface) | W6 |
| CAP-SPAWN enforced bound not landed | CAP-SPAWN X4 |

Platform-side hardening (CAP-STATE durability / task reachability / roster completeness / notification generation / runtime startability) proceeds on the implementation side; this table declares gaps, not progress.
