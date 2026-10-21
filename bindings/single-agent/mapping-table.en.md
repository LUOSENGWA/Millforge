# Mechanism × Runtime Mapping Table (Bare QwenPaw)

> This file is the **single source of truth** for the `bindings/single-agent/` mapping (the `README.md` "CAP Mapping" table is its consistent summary).
> Generic-word discipline: this directory is the only legitimate surface for runtime-specific names (`core/protocol/00-OVERVIEW.md` §S: core documents may only reference CAP-* numbers + generic words).

## 1. CAP → Mechanism Mapping (8-capability baseline)

| Capability | Bare QwenPaw mechanism | Invariant status | Risk / notes |
|------|------------------------|--------------|-----------|
| **CAP-STATE** | per-agent local JSON state file (`.qwenpaw/` or workspace) + file-lock CAS | S1 ✅ (host-disk durable) S2 ✅ (file lock; single writer per agent on a single host) S3 ✅ (JSONL append) S4 ⚠️ | host disk failure = total state loss; **binding declaration: no off-host state replica**; the host backup strategy is the deployer's own responsibility |
| **CAP-STORE** | local filesystem / shared volume (`storage_adapter: local`) | T1 ✅ (client-side sha256) T2 ✅ (a local write = synchronous completion; no async sync-layer race, the T2 execution detail degenerates) T3 ✅ (same-object JSONL append, safe on local POSIX; or chained) | shared-volume concurrent writes must follow the single-writer-per-directory convention (the T3 safety precondition) |
| **CAP-TIMER** | QwenPaw cron (`qwenpaw cron create --agent-id ...`) + `timer-derive.sh` idempotent derivation | U1 ✅ (due_at in CAP-STATE, host clock) U2 ✅ (idempotent callback re-derivation) U3 ✅ (judgement re-derived from state) U4 ⚠️ granularity = cron check period (binding declaration, default 5min, same as the agentteams binding) | **heartbeat/cron only does fallback wake-up, not real-time driving** (same as the agentteams binding); cron spec: `../agentteams/cron-spec.md` |
| **CAP-NOTIFY** | `qwenpaw channels send` (console / QQ / DingTalk / … per configured channel) | V1 ✅ (notifications are not state) V2 ✅ (state reconstructable from CAP-STATE) V3 ⚠️ (allowlist silent-drop risk, same mechanism as the agentteams binding) V4 ✅ (message_id dedup) V5 ⚠️ (no code-level event surface) V6 ⚠️ (delivered ≠ accepted) | V3/V5/V6 gaps = the same upstream gaps as the agentteams binding; the protocol must not depend on the absence of gaps |
| **CAP-ATTN** | QwenPaw channel DM / console session (persistent display surface = console session + IM DM) | W1 ✅ (idempotency key in state) W2 ✅ (response persisted to CAP-STATE) W3 ✅ (timeout_at in state, cron judges) W4 ⚠️ (DM identity = channel account mapping (usable)) W5 ✅ (DM / console session = persistent display surface: present + revisitable) W6 ⚠️ (single surface available) W7 ✅ (structured options + option_id) | group-chat @mention must not resolve (protocol redline S4); the binding-layer bot must route to DM / console |
| **CAP-SPAWN** | `spawn_subagent(fork=False)` (fresh session) | X1 ✅ (fork=False = does not inherit the parent session; **production-verified**; fork=True violates X1) X2 ✅ (structured return) X3 ✅ (state via return value) X4 ⚠️ (no enforced bound = upstream gap, same as the agentteams binding) | context isolation: the worker native session only schedules + reviews; all implementation goes into spawn; until X4 bounds are enforced, the binding layer uses the timeout parameter best-effort (not enforced) |
| **CAP-EXEC** | agent workspace shell (python3 stdlib) | Y1 ✅ Y2 ✅ (exit-code semantics in the core/scripts header comments) Y3 ✅ | **pip always the venv flavor** (same iron rule as the agentteams binding); scripts ship with the core (no runtime rewrite required) |
| **CAP-ROSTER** | roster JSON file (agent config + human members) | Z1 ✅ (role weights) Z2 ⚠️ (accountable explicitly configured; ABSENT must be returned explicitly by the binding layer) Z3 ✅ (delegation chain = config change record) | a single host defaults to single_user; multi_user is degenerate (no cross-team, no arbitrator) |

**Legality verdict**: this binding is currently = **7.5/8 satisfied** — all 8 capabilities are implemented by QwenPaw native mechanisms + local files; X1 ✅ production-verified; X4 ⚠️ bound best-effort, not enforced (upstream gap); CAP-NOTIFY V3/V5/V6 partially satisfied (the same upstream gaps as the agentteams binding); S4 ⚠️ host-disk single point (binding declaration, no off-host replica). **Marked reference, not compliant, until the X4 enforced bound lands + the V3/V5/V6 upstream gaps close.**

## 2. Mechanism → Execution Carrier (storage-layer substitution + trigger surfaces)

The mechanism → execution-carrier mapping is the same as the agentteams binding (the protocol mechanisms are unchanged; only the storage-layer carrier is substituted):

| Layer | agentteams binding carrier | this binding's carrier |
|---|---|---|
| task-level state (task meta) | TeamHarness task meta | per-agent local JSON state file (workspace state dir) |
| artifact / decision_log | MinIO / RustFS object | local filesystem / shared volume path (`storage_adapter: local`) |
| team roster | Team CRD | roster JSON file |
| room / notification channel | Matrix Room | QwenPaw channel (DM / console session) |
| scheduling | QwenPaw cron (per Worker) | QwenPaw cron (per agent) |
| off-host backup | MinIO | none (binding declaration: the S4 risk is accepted; host backup is the deployer's own responsibility) |

- Trigger surfaces: the protocol-layer skill (each agent's own skill) + `qwenpaw cron` callbacks; the 9 in-tree scripts are unchanged (see `skill-fragments.md` §1).
- [NO-CARRIER] gaps: the same as the agentteams binding (the planned carriers of the R5 timeout window / B-5 stall count / B-6 mismatch window / decision record are unimplemented) — see `../agentteams/mapping-table.md` §2.1; until implemented, those mechanisms run as "protocol-layer trigger + manual fallback".

## 3. Primitive Mapping

| Primitive | Mechanism |
|------|------|
| human | channel account (roster JSON human entry) + console session |
| agent | QwenPaw agent instance (multiple instances on a single host) |
| leader | agent role instance (compiled SOUL.md + fragments) |
| worker | agent role instance + spawn child execution unit |
| arbitrator | not applicable (no cluster-level coordination role in single_user; the cross-team handoff mechanism does not exist) |
| room | QwenPaw channel (DM / console session) |
| project | not applicable (no object-storage project space; a shared volume can simulate it, permissions via directory convention) |
| task | per-agent local JSON state (CAP-STATE) |
| artifact | local / shared-volume file (path contract + client-side sha256 fingerprint) |
| decision node | NMH document decision tree + decision_log (local `decisions/` path) |
| channel | console / IM channel |
| mode | single_user (default) |
| attention | channel DM + console session + state file (CAP-ATTN) |
| loop | CAP-STATE loop_state + cron fallback + spawn X4 (best-effort) |
| signal | CAP-STATE event_type (closed list) + channel message markers (derived view) |
