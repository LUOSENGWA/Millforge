# Mechanism × Runtime Mapping Table (AgentTeams + QwenPaw)

> This file is the **single source of truth** for the `bindings/agentteams/` mapping (`README.md` §1 is its consistent summary).
> Generic-terminology discipline: this directory is the only legal surface for runtime-specific names (`core/protocol/00-OVERVIEW.md` §S: core clauses/contracts/templates/tests allow only CAP-* numbers + generic terms).

## 1. CAP → Mechanism Mapping (8-capability baseline)

| Capability | AgentTeams/QwenPaw mechanism | Invariant status | Risks/notes |
|------|------------------------|--------------|-----------|
| **CAP-STATE** | worker-container-local JSON (state files under `.qwenpaw/workspaces/default/`) + file-lock CAS; task-level state may additionally live in TeamHarness task meta | S1 ✅ (local-disk persistent) S2 ✅ (file lock; single-node single-writer) S3 ✅ (JSONL append) S4 ⚠️ | container rebuild loses state → **state must be synced to a MinIO backup** (see `deployment-guide.md` filesync section); before the `mc` push confirmation, it is not durable (T2 execution detail) |
| **CAP-STORE** | MinIO / RustFS (S3-compatible), path addressing; `mc cp` writes | T1 ✅ (**client-side sha256**; ETag is not a fingerprint) T2 ✅ (S3 strong read-after-write consistency + sync-layer uploaded receipt) T3 ✅ (**chained simulation**: `decisions/<task>/<seq>.json` new-object chain; no same-key append) | hot keys never appended to the same object (S3 conditional PUT serialization); CAP-STATE must not simulate CAS via object-store conditional PUT (object level ≠ key-value level) |
| **CAP-TIMER** | QwenPaw cron (`qwenpaw cron create --agent-id ...`) + `timer-derive.sh` idempotent derivation | U1 ✅ (due_at in CAP-STATE, container clock) U2 ✅ (callback idempotently re-derives) U3 ✅ (verdict recomputed from state; no "processed" marker stored) U4 ⚠️ granularity = cron check period (binding-declared; default 5min) | **heartbeat/cron only does fallback wake, never real-time driving** ; real-time driving = event triggers + state-machine side effects |
| **CAP-NOTIFY** | QwenPaw `channels send` (QQ/Matrix channels) + Matrix Room @mention | V1 ✅ (notifications not persisted as state) V2 ✅ (state in CAP-STATE, rebuildable) V3 ⚠️ **known defect: allowlist silent drop leaves no gaps** (#160/#169 production-verified) V4 ✅ (message_id dedup) V5 ⚠️ no code-level event surface V6 ⚠️ delivered ≠ accepted | **V3/V5/V6 gaps are known implementation gaps (closed by later versions)**; until they close, the binding marks "partially satisfied"; the protocol must not rely on gaps being absent |
| **CAP-ATTN** | QwenPaw channel DM (DM Room) + local state file recording replies | W1 ✅ (idempotency key in filename/state) W2 ✅ (reply lands in CAP-STATE) W3 ✅ (timeout_at in state, cron verdict) W4 ⚠️ **DM identity = Matrix user_id mapping (usable)**; group-chat @mention must not resolve (S4) W5 ✅ (DM Room = persistent display surface: persists + revisitable) W6 ⚠️ no multi-surface sync (single surface OK) W7 ✅ (structured options + option_id) | group chat not being a response surface is a **protocol redline** (S4); the binding-layer bot must steer to DM |
| **CAP-SPAWN** | QwenPaw `spawn_subagent(fork=False)` (fresh session) | X1 ✅ (fork=False = does not inherit the parent session; **fork=True violates X1**) X2 ✅ (structured return) X3 ✅ (state via return value) X4 ⚠️ **no enforced bound = upstream gap** | context isolation: the worker native session only schedules + reviews; all implementation goes to spawns; until X4 bounds are enforced, the binding layer uses the timeout parameter best-effort (not enforced) |
| **CAP-EXEC** | shell inside the worker container (`/opt/venv/copaw/bin/python3` + stdlib); **pip is always the venv version** (runtime constraint) | Y1 ✅ Y2 ✅ (exit-code semantics see the core/scripts headers) Y3 ✅ | scripts ship with the core (the runtime is not asked to rewrite them); the **scheduling part** of the watchdog is this binding's implementation (cron + state-file paths); the logic part = the core reference implementation |
| **CAP-ROSTER** | Team CRD / agent config (roster file: member_id/role/weight) | Z1 ✅ (role weights) Z2 ⚠️ (accountable is explicitly configured; ABSENT must be explicitly returned by the binding layer) Z3 ✅ (delegation chain = config change records) | roster change = R1 human-locked; allowlist config changes must be verified to take effect (the permission-wall fuse companion) |

**Legality verdict**: this binding is currently **7.5/8 satisfied** — CAP-NOTIFY V3/V5/V6 partially satisfied (until the upstream PR line closes); CAP-SPAWN X4 best-effort, not enforced. **Marked reference, not compliant, until the gaps close + X4 enforced bounds land.**

## 2. Mechanism → Execution-Carrier Mapping (14 mechanisms)

**Mapping principle**: each mechanism's "execution carrier" must be a concrete component already present in the mechanism map (taskflow action / server.py / watchdog cron / QwenPaw cron / heartbeat / skill script / MinIO file). **State storage prefers task meta or MinIO files**; Matrix is notification only, never state. A missing carrier is marked [NO-CARRIER] with the minimal viable carrier proposal.

| Mechanism | Execution carrier | State location | Restart-survives | Trigger |
|---|---|---|---|---|
| **R2 weighted-majority voting** | skill script `aggregate-vote.sh` (Leader side) + votes already collected in task meta `attention[]` | task meta: `attention[].votes[]` (each vote: `user_id` / `weight` / `decision_class` / `received_at`) | ✅ (task meta persisted in taskflow storage) | protocol layer (attention timeout or sufficient votes) |
| **R5 reopen + 24h/4h timeout window** | **[NO-CARRIER]** → proposal: `nmh-watchdog.sh` new mode `reopen-window` (cron */2 checks `reopen_requested_at` + `decision_class` → timeout downgrades) | task meta: inside `decision_nodes[].lock` — `{locked_by, locked_at, reopen_requested_at, reopen_status}`; task-context.json mirror `pending_reopens[]` | ✅ (task meta + state file) | watchdog cron |
| **R6 attention routing + 30min/2h timeouts** | taskflow `request_attention` (already carries kind/timeout/idempotency); **multi_user routing needs a second routing pass** (see Task 4) | task meta: existing `attention[]` fields + new `routing` sub-field `{accountable, cc[], routed_at, timeout_class}` | ✅ (server.py persists attention[]) | Worker/Leader via taskflow; timeout via watchdog or QwenPaw cron |
| **B-1 decision_log three-layer schema check** | layer 1: skill script `validate-decision-log.sh` (parent Worker runs it **before acceptance**, not at spawn return — a spawn is an LLM and cannot self-validate); layer 2: `detect-conflict.py` (Task 2-2); layer 3: critic acceptance script checks the fingerprint | MinIO: `decisions/<task_id>/<spawn_id>.decision.json` (authoritative); task meta: `decision_logs[]` stores only the `{ref, sha256_8, validated: bool}` index | ✅ (MinIO + task meta index) | parent Worker skill before merge; layer 3 by critic |
| **B-2 conflict detection Step 1–3 pure function** | Python script `detect-conflict.py` (no LLM, pure field comparison) | candidate conflict pairs to MinIO: `decisions/<task_id>/conflict-candidates.json`; task meta: `merge_state: {candidates_ref, resolved: bool}` | ✅ (MinIO file) | parent Worker skill after B-1 layer 1 passes |
| **B-3 revalidation (semver + fingerprint + compat report)** | skill script `contract-revalidate.sh` (compares `contract_ref@semver` vs returned fingerprint + reads the compatibility-report artifact) | task meta: `contract_state: {pinned_ref, pinned_fingerprint, returned_fingerprint, diff_class, revalidated: bool}`; MinIO: compatibility-report path | ✅ (task meta + MinIO) | parent Worker before acceptance; or critic layer 3 fallback on fingerprint mismatch |
| **B-5 attention_stall_count fuse counting** | **[NO-CARRIER] direct counting** → proposal: `nmh-watchdog.sh` new mode `attention-stall` (cron */2 scans `attention[]` for consecutive timeouts with resolved=false); count written to task meta | task meta: `attention_stall_count` (int) + `attention_stall_level` (normal / escalated / frozen); task-context.json mirror `attention_stall` | ✅ (task meta + state file) | watchdog cron |
| **B-6 verification_mismatch counting + 24h window** | **[NO-CARRIER]** → proposal: `nmh-watchdog.sh` new mode `mismatch-window` (cron */2 checks `verification_mismatch[].opened_at` → 24h timeout keeps the original spec) | task meta: `verification_mismatch[]` (each: `{criterion_id, critic_alternative, opened_at, status}`) + `verification_mismatch_count` | ✅ (task meta + state file) | critic via NMA scorecard; watchdog checks timeout |
| **B-10 decision_class_mismatch + saga compensation** | event emission: Leader/Worker skill script `emit-class-mismatch.sh`; compensation-directive generation: `saga-compensate.py` (reads dependency graph + forward operation log → reverse compensation sequence) | task meta: `decision_class_mismatches[]` + `saga_compensation: {required: bool, directive_ref}`; MinIO: compensation directive `saga/<task_id>/compensation.json` | ✅ (task meta + MinIO) | emit script when an agent detects misclassification at runtime; `saga-compensate.py` triggered by protocol layer/Leader |
| **C-3 locked_spec_consistency_check** | **two-layer scheme** (see Task 2-7): ① rule layer: `consistency-check.py` does **field-level/enum-level** binary comparison (when `acceptance_criteria` is structured); ② LLM layer: only when the rule layer cannot decide (natural-language acceptance), invoke a **bounded classification spawn** (not free generation — outputs only `{contradict: true/false, criterion_id, reason}`) | task meta: each `r6_responses[]` entry carries `{response_id, consistency_check: {result, checked_by, checked_at}}`; rejected answers marked `rejected_by_consistency: true` | ✅ (task meta) | before R6 answer write-back, by protocol layer/skill; LLM classification spawn dispatched by parent Worker |
| **C-2 contract_snapshot write-back** | when the R6 answer is written back to the task state machine, skill script `write-contract-snapshot.sh` writes it in sync | task meta: `contract_snapshot: {contract_ref, fingerprint, checked_at}`; task-context.json mirror | ✅ (task meta) | R6 answer write-back flow (protocol layer/skill) |
| **G8 aggregation-result write-back schema** | `write-aggregation-result.sh` (the write-back part of the Task 2-8 voting script) | task meta: `aggregation_result: {decision_id, rule_applied, votes[], outcome, dissent[], decided_at}`; task-context.json mirror `last_aggregation` | ✅ (task meta) | after voting completes, by protocol layer/skill |
| **decision record write** | skill script `write-decision-record.sh` (append-only to MinIO JSONL); task meta stores only `decision_record_ref` | MinIO: `decisions/<task_id>/record.jsonl` (one line each: `{decision_id, type, actor, outcome, dissent[], locked_by, overridden_by[], timestamp}`) | ✅ (MinIO append-only) | after any decision action (R1–R6), by protocol layer/skill |

### 2.1 [NO-CARRIER] carrier gaps (planned, not implemented)

| Gap mechanism | Minimal carrier (planned) | Why not the alternative |
|---|---|---|
| R5 timeout window | `nmh-watchdog.sh` new cron mode | QwenPaw cron works but adds platform coupling; heartbeat granularity 30min is too coarse (R5 reversible window 4h — 30min checks acceptable; but watchdog */2 infrastructure already exists, lowest reuse cost) |
| B-5 stall counting | `nmh-watchdog.sh` new mode | taskflow has no "scan task meta and count" action; an upstream PR could add it but is not required |
| B-6 mismatch window | `nmh-watchdog.sh` new mode | same as above |
| decision record | MinIO append-only JSONL + skill write script | task meta would be bloated; Matrix is unreliable |

> **In-tree status note (verification note)**: among the carriers above, `aggregate-vote.sh` / `validate-decision-log.sh` / `detect-conflict.py` / `contract-revalidate.sh` / `attention-stall.sh` / `verification-mismatch-window.sh` / `saga-compensate.py` / `consistency-check.py` / `timer-derive.sh` are in-tree (`core/scripts/`, 9 files); `nmh-watchdog.sh` / `emit-class-mismatch.sh` / `write-contract-snapshot.sh` / `write-aggregation-result.sh` / `write-decision-record.sh` are planned carriers, **not yet implemented** — until implemented, the corresponding mechanisms run as "protocol-layer trigger + manual fallback".

## 3. Primitive Mapping

| Primitive | Mechanism |
|------|------|
| human | Matrix user (the human entry in the roster, e.g. `@human-a`/`@human-b`) + IM channel |
| agent | QwenPaw Worker container (`python3 -m copaw_worker.run_copaw_app app`, qwenpaw runtime) |
| leader | Worker role instance (skeleton/leader compiled artifact deployed to `.qwenpaw/workspaces/default/`) |
| worker | Worker role instance + spawn sub-execution units |
| arbitrator | Manager container (`agentteams-manager`, qwenpaw runtime, single_user only) |
| room | Matrix Room (team room / project room / DM Room) |
| project | TeamHarness project + MinIO project space `{proj}/brief.md+meta+artifacts/` |
| task | TeamHarness task + task meta (CAP-STATE) |
| artifact | MinIO object (path contract + client-side sha256 fingerprint) |
| decision node | NMH document decision tree + decision_log (MinIO `decisions/`) |
| channel | QQ original channel / console |
| mode | single_user (production status quo: one human per cluster) |
| attention | DM Room + state file (§CAP-ATTN) |
| loop | CAP-STATE loop_state + cron fallback + spawn X4 |
| signal | CAP-STATE event_type (closed list) + channel message marker (derived view) |

## 4. NMA Message Types → Execution Carriers (Part A, communication layer)

| NMA type | Carrier in this binding | Status |
|----------|------------------------|--------|
| `DELEGATE` | taskflow `delegate_task` (`spec` + `assignedTo` + `taskId` + `projectId`) | ✅ in tree |
| `ACK` | taskflow `ack_task` | ✅ in tree |
| `PROGRESS` | taskflow `report_progress` (state unchanged, no leader notification) | ✅ in tree |
| `COMPLETE` | taskflow `submit_task` (`summary` + `deliverables`) + SIG-COMPLETE | ✅ in tree |
| `QUERY` | no structured carrier (taskflow explicitly excludes direct questions) → group-chat text | ⚠️ gap: a structured QUERY needs a new action (or `request_attention(kind=other)` as an interim) |
| `DECISION_REQUEST` | taskflow `request_attention` (kind=decision) + CAP-ATTN W7 | ✅ in tree |
| `HANDOFF` | `07-HANDOFF` document + shared-storage handoff file (no API) | ✅ document carrier |
| `ESCALATE` | taskflow `request_attention` (kind=escalation) | ✅ in tree |

**Field landing and gaps**: `taskId` / `projectId` = action parameters; `refs[]` ≈ `deliverables` / artifact ref. There is no standalone `message_id` parameter — idempotency is guaranteed at the action layer (`submit_task`'s `submissionId` identity + task-state checks); `deadline` / `deadline_fallback` have no carrier (CAP-TIMER provides external fallback).

## 5. NMH §8 Execution-Time Ask → Carriers

| Clause | Carrier | Status |
|--------|---------|--------|
| structured decision request (options / recommendation / impact / deadline) | taskflow `request_attention` (kind=decision; payload shape by call convention, not schema-enforced) | ✅ in tree (option shape not enforced) |
| persistent display surface (W5) | DM Room (W5 satisfied); dashboard todo as a second surface | ✅ DM / ⚠️ dashboard surface gap (see README §4) |
| code-level event (V5) | event subscription surface | ⚠️ gap (V5 not implemented; see README §4) |
| answer written to CAP-STATE → resume from state | `request_attention` `payload.resolved=true` closes the record + task-state re-read | ✅ in tree |
| timeout fallback | CAP-TIMER (due_at + cron judgment) | ✅ in tree (no deadline field; CAP-TIMER external fallback) |
