# Deployment Guide (Bare QwenPaw Binding, exclusive)

> This file is the deployment/operations specification of `bindings/single-agent/`; the mapping is in `mapping-table.md`.

## 1. Topology (this binding's proper-noun surface)

| Primitive | Deployment form |
|------|---------|
| agent (leader/worker) | a single Docker host, multiple QwenPaw agent instances (no K8s / Controller / Team CRD) |
| state | per-agent local JSON state file (host disk; **no off-host replica** — binding declaration) |
| store | local filesystem / shared volume (`storage_adapter: local`) |
| timer | QwenPaw cron (per agent, `qwenpaw cron create --agent-id ...`) |
| notify / attn | QwenPaw channel (console / IM, per configured channel) |
| platform layer | none (no MinIO, no Matrix, no object-storage project space) |

## 2. Compile → Deploy Chain

```
millforge compile <team.json> --out /tmp/build/<team>
  → <role>.soul.md × N          # identity file
  → fragments/protocol-*.md     # protocol layer
  → fragments/industry-*.md
  → spawn-specs/*.md            # spawn injection
  → core/scripts/ 9 scripts (ship with the core)
deploy (per agent):
  1. <role>.soul.md → that agent workspace root SOUL.md
     + fragments/ spawn-specs/ → workspace protocols/
  2. roster JSON + core/scripts/ → a shared location (each agent's executable path)
  3. cron: register per active task per timer-derive (qwenpaw cron)
  4. verify: read the files back + line-count check (wc -l)
```

**Hard constraints**:
- **No off-host state replica** (S4 ⚠️ binding declaration): the host disk is a single point; the host backup strategy is the **deployer's own responsibility** (this binding provides no platform-layer backup).
- **pip always the venv flavor** (same iron rule as the agentteams binding) — the system pip installs to the wrong path; a version misjudgement is a production incident source.
- No docker-restart rollback issue (no platform-layer restore mechanism); a SOUL.md update takes effect in the next session.
- Shared-volume concurrent writes: the single-writer-per-directory convention (the T3 safety precondition).

## 3. Sync Layer

not applicable — there is no async object-storage sync layer; a local write = synchronous completion, so the T2 execution detail degenerates (no uploaded-receipt requirement).

## 4. Failure Sequences and Recovery

| Failure | Detection | Recovery |
|------|------|------|
| host disk failure (total state loss) | host monitoring / state read failure | the binding layer cannot recover (no off-host replica); rely on the host backup strategy (deployer's own responsibility) |
| state-file concurrent-write conflict | CAS CONFLICT | retry under the file-lock CAS; JSONL append is idempotent and replayable (S3) |
| cron timer lost (agent restart) | task has due_at but no cron | `timer-derive.sh` idempotent re-derivation (U3: the judgement is recomputed from state) |
| spawn hang with no return | X4 bound (best-effort) | `bounded_failure` semantics; escalation after 3 times |
| allowlist silent drop | a message disappears without an error log | compare the channel access configuration (same mechanism as the agentteams binding; see `../agentteams/deployment-guide.md` §4) |
| SOUL.md update not effective | behavior drift | check the workspace SOUL.md content; it takes effect in the next session (no restart needed) |
