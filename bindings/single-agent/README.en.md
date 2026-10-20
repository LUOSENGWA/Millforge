# Single-Agent Runtime Binding (reference)

> The mapping between the Millforge core and a **single-agent runtime** (no orchestration layer). **This binding is generic across single-agent runtimes**: product matrix = QwenPaw / OpenClaw / Hermes / … (QwenPaw is the reference product).
> Applicable scenario: a single Docker host, multiple QwenPaw agent instances (no K8s/Controller/Team CRD), no MinIO (local disk / shared volume as object storage).
> The difference from `bindings/agentteams` = removing the platform orchestration layer; **all capabilities are carried by QwenPaw native mechanisms + local files**.

## Index (full documents)

| Document | Content |
|------|------|
| `mapping-table.md` | CAP→mechanism mapping (per-invariant status for the 8 capabilities) + storage-layer substitution + primitive mapping (**single source of truth**; the "CAP Mapping" table of this README is its consistent summary) |
| `skill-fragments.md` | CAP-SPAWN/CAP-EXEC skill surface (9 in-tree scripts + spawn fragment (production-verified) + three-layer review chain) |
| `deployment-guide.md` | topology + compile→deploy chain + failure sequences and recovery |

## CAP Mapping

| Capability | Mechanism | Notes |
|------|------|------|
| CAP-STATE | per-agent local JSON state file (`.qwenpaw/` or workspace) + file-lock CAS | single host, no cross-node issue; S4 risk = host disk failure (binding declaration: no off-host state replica) |
| CAP-STORE | local filesystem / shared volume (`storage_adapter: local`) | T1 client-side sha256; T2 a local write = synchronous completion (no async sync-layer race); T3 same-object JSONL append (safe on local POSIX) or chained |
| CAP-TIMER | QwenPaw cron (`qwenpaw cron create --agent-id ...`) | same cron specification as the agentteams binding §3.2 |
| CAP-NOTIFY | `qwenpaw channels send` (console / QQ / DingTalk / … per configured channel) | V3 silent-drop risk same as the agentteams binding (same allowlist mechanism); V5 no code-level event surface |
| CAP-ATTN | QwenPaw channel DM / console session (persistent display surface = console session + IM DM) | group-chat @mention must not resolve (S4) |
| CAP-SPAWN | `spawn_subagent(fork=False)` | same as the agentteams binding (X4 bound best-effort); the spawn mechanism is **production-verified** |
| CAP-EXEC | agent container / host shell | same venv pip iron rule (QwenPaw environment) |
| CAP-ROSTER | roster JSON file (agent config + human members) | a single host is usually single human (single_user) or multiple humans each managing their own agents (multi_user degenerate: no cross-team) |

**Mode**: default `single_user` (without an arbitrator role, the cross-team extension is unavailable — the coordinator can be taken by any leader or a human; the protocol handles this per the §02-MODES phase transition: no cluster-level coordination role = the cross-team handoff mechanism does not exist).

## Capability Gap vs the agentteams Binding

| Surface | agentteams | bare-qwenpaw |
|----|-----------|--------------|
| cross-team handoff | ✅ (MinIO project space + Manager) | ❌ (no object-storage project space; a shared volume can simulate it, permissions via directory convention) |
| multi-user isolation | Controller + Matrix permissions | none (same host, same permissions = isolation is not guaranteed at the protocol layer; the deployment layer owns it) |
| team/roster management | Team CRD | manual roster file |
| off-host state replica | MinIO | none (host disk is a single point) |

**Applicability verdict**: personal experiments / single-team production / quick protocol-behavior validation → bare-qwenpaw is enough (the L1–L3 protocol layer is fully usable); multi-team + cross-team handoff + multi-human isolation → use agentteams.

## Deployment

```
1. compile: millforge compile <team.json> --out /tmp/build/<team>
2. per agent: <role>.soul.md → that agent workspace root SOUL.md
   + fragments/ spawn-specs/ → workspace protocols/
3. roster file + core/scripts/ → a shared location (each agent's executable path)
4. cron: register per active task per timer-derive
```

No docker-restart rollback issue (no platform-layer restore mechanism); a SOUL.md update takes effect immediately (next session).
