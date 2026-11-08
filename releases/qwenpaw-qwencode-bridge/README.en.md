# Module: `qwenpaw-qwencode-bridge`

> QwenPaw coding-CLI bridge plugin (dispatch / status / wake / approval mapping / native web console).
> Source: `agentscope-ai/AgentTeams` → `plugins/qwen-code-bridge` (merged in #1411, commit `c31dc45df`).
> This directory carries only **downloadable artifacts + release manifests**; source and tests live upstream.

## 1. Identity

| Field | Value |
|---|---|
| Module key (`modules.<key>`) | `qwenpaw-qwencode-bridge` |
| QwenPaw plugin id | `qwen-code-bridge` |
| `kind` | `plugin` |
| `runtime` | `qwenpaw` (runtime-specific; no adapter split; not claimed runtime-neutral) |
| Backend package / HTTP prefix | `qwen_code_bridge` / `/api/qwen-code-bridge` |
| Requirements | `qwenpaw >=2.2.0 <2.3.0`, `qwen-code-cli 0.26.x` |

## 2. Versions and channels

| Channel | latest | Notes |
|---|---|---|
| **stable** | **0.3.0** | First stable; version equals the upstream manifest version (no release-side rewrite) |
| beta | `null` | Slot opened; no version |
| alpha | `null` | Slot opened; no version |

Version discipline: the version under `releases/<module>/<version>/` must equal the artifact's `plugin.json` version and the index entry. Prereleases use `-alpha.N` / `-beta.N`.

## 3. Artifact

| Item | Value |
|---|---|
| File | `qwenpaw-qwencode-bridge-0.3.0.zip` |
| Size | 126,422 B |
| Files | 34 (root `qwen-code-bridge/`; excludes `tests/`, `__pycache__`, `web-shell/dist`) |
| sha256 | `01efceee…` (full value in `sha256sums.txt`) |
| Source commit | `c31dc45df` |

Verify: `cd releases/qwenpaw-qwencode-bridge/0.3.0 && sha256sum -c sha256sums.txt`

## 4. Install

**A. In-cluster (recommended; module update API)**

```bash
# Worker plane
curl -X POST http://<controller>/api/v1/workers/<worker>/plugins/install \
  -H 'Content-Type: application/json' \
  -d '{"module":"qwenpaw-qwencode-bridge","source":"github","repo":"LUOSENGWA/millforge","ref":"main","channel":"stable"}'

# Team plane (rolling by workerMembers; stop on failure)
curl -X POST http://<controller>/api/v1/teams/<team>/modules/qwenpaw-qwencode-bridge/install \
  -d '{"source":"github","channel":"stable"}'
```

Omit `version` to use the index `latest`; the backend re-reads the index and verifies sha256 (mismatch returns 409).

**B. Standalone QwenPaw (download + hot load)**

```bash
unzip qwenpaw-qwencode-bridge-0.3.0.zip -d "$QWENPAW_WORKING_DIR/plugins"
# or upload via the official endpoint (hot reload)
curl -X POST http://127.0.0.1:8088/api/plugins/upload?force=true \
  -F 'file=@qwenpaw-qwencode-bridge-0.3.0.zip;type=application/zip'
curl -s http://127.0.0.1:8088/api/plugins | grep qwen-code-bridge
```

## 5. API (prefix `/api/qwen-code-bridge`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/version` | `{plugin, started_at, python, qwen_cli, state_dir}` |
| GET | `` | Route index |
| GET | `/dispatch` | Task list (`?format=table` for a status table) |
| POST | `/dispatch` | Dispatch a task (202, returns `task_id`) |
| GET | `/dispatch/{id}` | Task detail |
| GET | `/dispatch/{id}/progress` | Progress (turns/elapsed/stalled/phase/last_target) |
| GET | `/dispatch/{id}/log` | Log stream |
| GET | `/dispatch/{id}/pending` | Pending human question |
| POST | `/dispatch/{id}/answer` | Answer a pending question |
| POST | `/dispatch/{id}/cancel` | Cancel (SIGTERM → grace → SIGKILL) |
| POST | `/dispatch/{id}/stop` | Stop |
| POST | `/dispatch/cleanup` | Clean terminal tasks |
| GET | `/dispatch/{id}/run` · `/qwen/status` · `/dispatch/{id}/qwen-status` | Runtime status |
| GET | `/approvals` | Approval receipt audit (`task_id` / `behavior` / `since` / `limit`) |
| GET | `/chat/{chat_id}` · POST `/sidebar` | Session sidebar |

This English twin mirrors the Chinese module README for the bilingual gate; the Chinese file is authoritative for details.
