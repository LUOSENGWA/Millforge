# Deployment Guide (AgentTeams + QwenPaw Binding-Specific)

> This file is the deployment/ops spec for `bindings/agentteams/`. Generic-terminology discipline: see the `README.md` header.

## 1. Topology (binding-specific naming surface)

| Primitive | Deployment form |
|------|---------|
| worker / leader | QwenPaw Worker container (`python3 -m copaw_worker.run_copaw_app app`, qwenpaw runtime); leader = compiled artifact deployed to `.qwenpaw/workspaces/default/` |
| arbitrator | Manager container (`agentteams-manager`, qwenpaw runtime, single_user only) |
| state | container-local state files under `.qwenpaw/workspaces/default/` + **MinIO/RustFS backup (mandatory)** |
| notify | QQ original channel / Matrix Room (team / project / DM) |

## 2. Compile → Deploy Chain

```
millforge compile <team.json> --out /tmp/build/<team>
  → <role>.soul.md × N          # identity files (layer 0)
  → fragments/protocol-*.md     # layer 1 (trigger-loaded)
  → fragments/industry-*.md
  → spawn-specs/*.md            # layer 2 (spawn-injected)
  → core/scripts/ 9 scripts (ship with the core, executable in-container)
deploy (per role):
  1. docker cp <role>.soul.md → container .qwenpaw/workspaces/default/SOUL.md
     + workspace-root SOUL.md (dual location! after docker restart the runtime restores the old files — deploy AFTER restart, not before)
  2. fragments/ + spawn-specs/ → container workspace protocols/ directory (symlinks to prevent overwrite)
  3. MinIO sync: mc cp → object store (complete only after the filesync uploaded receipt, T2 execution detail)
  4. verify: docker exec read-back + line-count check (wc -l, path as argument)
```

**Hard constraints**:
- **State must be synced to object-storage backup** — a container rebuild loses state (S4 ⚠️); before the `mc` push confirmation, it is not durable (T2).
- **pip is always the venv version** (`/opt/venv/copaw/bin/pip`) — the system pip installs to the wrong path; version misreads are a production-incident source (runtime constraint).
- Identity files are deployed to **dual locations**; deploying before restart gets overwritten by the runtime's restore.

## 3. filesync Sync Layer (CAP-STORE T2 Execution Detail)

- Container workspace ↔ MinIO/RustFS sync = push_loop (async) + startup mirror_all.
- **Post-write protocol (race protection)**: write → wait ≥45–60s (verify disk + push uploaded log) → only then restart/consume. Evidence: a fast restart after a write is rolled back by the startup mirror_all.
- uploaded receipt = the push log line `push uploaded .../<file>` (polled by the binding layer).

## 4. Failure Sequences and Recovery (T5 production evidence)

| Failure | Detection | Recovery |
|------|------|------|
| Worker container fault (Internal error) | docker logs ERROR | restart → re-dispatch (3 failures → escalate); **stale pydantic = workspace startup failure** (check the version with the venv pip, #176) |
| state written to MinIO but unconfirmed | no uploaded line in the push log | do not consume the ref (T2); re-push + confirm |
| allowlist silent interception | message vanishes with no error log | compare agent.json access control (#160/#169); after restart verify allow_from includes the human |
| cron timer lost (container rebuild) | task has due_at but no cron | timer-derive idempotent re-derivation (U3: verdict recomputed from state) |
| spawn hung with no return | X4 bound (best-effort) | bounded_failure semantics; escalate after 3 |
| SOUL.md rolled back after restart | file mtime/line count | dual-location re-deploy (after restart) |

## 5. Deployment Audit (M4: both ends)

**Why**: the compiler writes provenance into file content (version / fragment hashes / parameter fingerprint),
but once a file is overwritten or rolled back that history is unrecoverable — "which build was actually running"
cannot be answered (the #168 class of incident). The **deployment action itself** must leave a trace, and the
runtime must carry independent evidence; only when both ends agree is the deployment considered successful.

**5.1 Every deployment appends an audit line (control side)**

After pushing a build to a target (container / workspace / object store), append one JSON line to
`<state>/deployments.jsonl`:

```json
{"ts":"2026-11-02T02:10:00Z","target":"hiclaw-worker-sysdev",
 "source":{"team":"biz-team","compile_id":"…","git_commit":"…"},
 "files":[{"path":"SOUL.md","sha256":"…","bytes":12345}],
 "operator":"…","result":"ok"}
```

Hard requirements:
- `files[].sha256` is the hash **read back from the target after deployment**, never the local file hash — it is the
  only evidence against a half-copied file or a runtime rollback.
- `result ∈ {ok, failed}`; **failures are recorded too** (a failure line is root-cause material).
- **No audit line = not deployed** (treated exactly like the failure sequences in §4).

**5.2 Worker startup records the provenance hash (runtime side)**

On container start the Worker writes one line to its startup log with the provenance hash of the active SOUL:

```text
[soul] provenance=<sha256-8> version=<millforge.version> compiled_at=<ts>
```

The binding layer compares the audit line's sha256 with the startup log's provenance hash; a mismatch means the
deployment did not take effect and is rolled back.

**5.3 Relation to filesync**: the audit line is written locally under `<state>/` and synced by push_loop — no new storage.
