# taskforge/ — TaskForge module (independent distribution, not released)

> **Status (2026-11-08)**: TaskForge is the former LoopRunner; module id **`taskforge`**, process **`taskforged`**, kind **`runner`**. This is a **1.2.7 planning slot**; 1.2.6 does not ship it. The `taskforge` entry in `releases/channels.json` stays `latest: null`, `versions: {}`.
>
> **Not a QwenPaw plugin**: TaskForge is the task component behind AgentTeams; install goes through the TaskForge installer / Controller module host (install surface still unconfirmed); its API is reachable only through the Controller gateway. The old standalone runner API (#1509/#1510) was withdrawn in #1508 and is not the install surface.

**中文**: [README.md](README.md)

## 1. Artifact layout

```text
releases/taskforge/<version>/
  taskforge-<version>-linux-amd64.tar.gz
  taskforge-<version>-linux-arm64.tar.gz
  taskforge-<version>.manifest.json
  sha256sums.txt
```

Each tar contains:

- `taskforged` binary for that platform;
- `migrations/` (`work` schema migrations; version aligns with manifest `work_schema`);
- `install.sh` / `update.sh` / `rollback.sh` (or equivalent systemd/container template);
- `contracts/` (TaskForge internal API/event contracts; no TH/MX plugin files).

Source/build stays in the AgentTeams repo; the Millforge repo only holds downloadable artifacts and the channel index.

## 2. `channels.json` entry

```json
"taskforge": {
  "kind": "runner",
  "latest": "0.1.0",
  "versions": {
    "0.1.0": {
      "artifacts": [
        {"name": "taskforge-0.1.0-linux-amd64.tar.gz", "sha256": "<64hex>"},
        {"name": "taskforge-0.1.0-linux-arm64.tar.gz", "sha256": "<64hex>"},
        {"name": "taskforge-0.1.0.manifest.json", "sha256": "<64hex>"}
      ],
      "image": {"repository": "ghcr.io/luosengwa/taskforge", "digest": "sha256:<64hex>"},
      "protocol_version": "1",
      "requires": {
        "agentteams": ">=1.2.7",
        "work_schema": "1",
        "contracts": "1"
      },
      "commit": "<40hex>",
      "published_at": "2026-11-08T00:00:00Z",
      "deprecated": false
    }
  }
}
```

- `kind` is `runner` (TaskForge is a service, not a QwenPaw plugin or TH/MX bundle).
- Every artifact carries sha256; installers must verify all before install.
- `requires.work_schema` is the DB migration contract; `protocol_version` is the Controller/TaskForge API contract; `agentteams` is the minimum gateway/auth version.
- `image` is optional; when present, installers may use the digest instead of tar.

## 3. Independent update

TaskForge updates **do not rebuild the Controller image**; Controller keeps only the generic gateway/protocol window:

```text
1. Read channels.json → choose taskforge version
2. Download artifacts → verify every sha256
3. Read manifest → check protocol_version / work_schema / agentteams window
4. Stop old taskforged (single writer; stop before start, never parallel)
5. Back up seekdb work schema (same snapshot_id as storage backup)
6. Run taskforged migrate (forward-compatible; fail → restore)
7. Start new version → /healthz /readyz → verify DB schema_version
8. Controller only switches TASKFORGE_URL/gateway; no Controller rebuild
9. Failure: stop new → restore backup → start old; keep old tar/DB backup
```

- **Single writer**: only one active `taskforged`; stop old first, never dual-write.
- **Migration/rollback**: migrations must be forward-compatible; downgrade is via backup, not automatic reverse migration.
- **Update window**: task write API returns 503 while TaskForge is unavailable; no file/meta.json fallback.
- **Controller protocol**: only a `protocol_version` window change requires a Controller upgrade; normal TaskForge releases do not.
- **Data/memory/storage**: TaskForge writes only `work`; no memory/resources; artifact bytes via 04; backup DB + object `snapshot_id` together.

## 4. Failure semantics

| Failure | Code | Behavior |
|:--|:--|:--|
| sha256 mismatch | `artifact_digest_mismatch` | do not install |
| protocol/work_schema out of window | `protocol_unsupported` / `schema_unsupported` | do not start |
| migration failure | `migration_failed` | keep old/backup; Controller 503 |
| health/ready failure | `taskforge_unhealthy` | stop new, restore old; no traffic switch |
| two instances | `taskforge_already_active` | later instance exits (single-writer lease) |
| task API unavailable | `taskforge_unavailable` | Controller 503; no file fallback |

## 5. Boundaries

- **One DB backend: seekdb** — server in production; embedded only for local/single-process (confirmed); SQLite is not a TaskForge runtime backend.
- **Checkpoints do not use Git** — DB logical snapshots + `task_events`; Git only as an artifact reference.
- **API only through Controller** — TaskForge internal API is not public; TH/Matrix/Dashboard all go through the Controller gateway.
- **Independent ≠ standalone runner API** — independent version/artifact/install/update/rollback; #1508 withdrew the public runner API.
- **Install surface is still unconfirmed** — TaskForge installer vs Controller module host is not decided; this file defines artifact/update contract only.
- **Cross-line**: `方案与设计/AgentTeams/下版本1.2.6-1.2.7/13-TaskForge与03-04-11咬合-20261108.md`.
