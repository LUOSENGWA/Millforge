# taskforge/ — TaskForge distribution

TaskForge is the task-management module for AgentTeams. This directory publishes downloadable TaskForge artifacts and the version index.

> **Status**: no version is published yet; once published, the entry goes into the matching channel file under `releases/{alpha,beta,stable}/channels.json`.

**中文**: [README.md](README.md)

## Artifact layout

```text
releases/taskforge/<version>/
  taskforge-<version>-linux-amd64.tar.gz
  taskforge-<version>-linux-arm64.tar.gz
  taskforge-<version>.manifest.json
  sha256sums.txt
```

Each archive contains:

- the `taskforged` executable;
- database migrations;
- install/upgrade/rollback scripts or service templates;
- module contract files.

## Version index

Example `taskforge` entry in `releases/stable/channels.json` (beta/alpha share the shape):

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
      "protocol_version": "1",
      "commit": "<40hex>",
      "published_at": "2026-11-08T00:00:00Z",
      "deprecated": false
    }
  }
}
```

## Runtime requirements

- Linux amd64/arm64; run a single instance (no concurrent writers across replicas).
- **Production: a seekdb server**; embedded seekdb is for local development only.
- v1 does not support SQLite or OceanBase as the TaskForge backend.
- TaskForge owns `work` task data only; artifact bytes stay in external object storage and the task database stores references.
- Controller calls TaskForge through its internal gateway; do not expose the task port directly.
- Authentication and authorization are handled by Controller; TaskForge accepts Controller service calls only and does not offer end-user login.

Exact version, compatibility-window and database requirements are declared in `manifest.json` and the release notes for that version.

## Install and upgrade

1. Choose a version from `channels.json` and download the artifact for the target platform.
2. Verify every `sha256`; stop if any mismatch.
3. Read the version and compatibility requirements in `manifest.json`.
4. Stop the old instance and back up the existing database.
5. Apply the migrations included in the archive.
6. Start the new version and check health.
7. Run only one instance at a time; never start old and new instances in parallel during an upgrade.
8. On failure, stop the new instance, restore the database backup, and start the old version.

## Rollback

Keep the full archive of the previous version and the pre-upgrade database backup. To roll back:

1. Stop the current instance.
2. Restore the pre-upgrade database backup.
3. Start the previous version.
4. Check health and task-service status.

## Verification

```bash
cd releases/taskforge/<version>
sha256sum -c sha256sums.txt
```

