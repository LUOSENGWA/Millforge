# releases/ — beta distribution mirror

This directory mirrors **module artifacts** (`teamharness`, `agentteams-matrix`, `qwen-code-bridge`, `looprunner`).

**Current beta staging (2026-11-04):** `teamharness` 0.1.0 (`teamharness-qwenpaw-0.1.0.zip` / `teamharness.tar.gz`) and `agentteams-matrix` 0.1.0 (`agentteams-matrix-channel-0.1.0.zip` / `agentteams-matrix.tar.gz`); `channels.json` records `pluginId=agentteams-matrix-channel`.
It is not a build directory: artifacts are produced by the upstream release workflow (AgentTeams); this directory only carries **downloadable copies plus the index**.

> Why repository content instead of GitHub Releases: plain git mirrors (including GitCode, which has no release mirroring) only sync repository content. Keeping the artifacts here means GitHub and GitCode both serve them through the same `raw` URLs.

## Layout

```
releases/
├── channels.json            # channel index (single entry point)
├── <module>/
│   └── <version>/
│       ├── <module>-<version>.tar.gz
│       ├── <module>-<version>-qwenpaw.zip
│       ├── sha256sums.txt
│       └── release-manifest.json
```

- `<module>`: `teamharness` / `agentteams-matrix` / `qwen-code-bridge` / `looprunner`.
- `<version>`: betas are `<semver>-beta.N` (e.g. `0.3.0-beta.2`).
- Artifacts are copied verbatim from the upstream release. When `sha256sums.txt` / `release-manifest.json` are provided upstream they are copied as-is; otherwise the sync script generates the checksums.

## channels.json

```json
{
  "schema": 1,
  "channel": "beta",
  "updated_at": "2026-11-03T00:00:00Z",
  "modules": {
    "teamharness": {
      "kind": "plugin",
      "latest": "0.3.0-beta.2",
      "versions": {
        "0.3.0-beta.2": {
          "artifacts": [
            {"name": "teamharness-0.3.0-beta.2.tar.gz", "sha256": "…"},
            {"name": "teamharness-0.3.0-beta.2-qwenpaw.zip", "sha256": "…"}
          ],
          "requires": {"agentteams": ">=1.2.6", "contracts": "1", "tool_schema": "1", "millforge": "1.1.0"},
          "commit": "abc123def456",
          "published_at": "2026-11-03T00:00:00Z",
          "deprecated": false
        }
      }
    }
  }
}
```

- `latest`: highest version per module on this channel.
- `kind` (module level): `plugin` / `bundle` / `runner` — the client/workbench uses it to pick the install path: `plugin` = `teamharness` / `qwen-code-bridge`, `bundle` = `agentteams-matrix`, `runner` = `looprunner`. The Runner module id stays `looprunner`; its display name is **TaskForge** (tentative, 2026-11-04).
- `pluginId` (optional, module level): the plugin id QwenPaw actually installs; defaults to the module name. MX uses `agentteams-matrix-channel` (adapter install). **The current 0.1.0 entry sets `pluginId=agentteams-matrix-channel`**; the controller rejects `kind=bundle` with `pluginId==module` (400) to avoid installing the wrong package.
- The sync script sets `kind` from this table for new module entries; a hand-set `kind` is never overwritten.
- `deprecated: true`: kept on disk, must not be installed by default.
- `requires` comes from the upstream `release-manifest.json`; when missing, the sync script leaves `{}` and warns.
- Clients (installer / workbench) consume only this contract. The stable channel uses the same schema and is hosted elsewhere (official repo / controller default / object-storage mirror — one of the three, configurable).

## Adding a version

1. Upstream tags `<module>-v<semver>-beta.N` (prerelease).
2. Run `tools/sync-beta.sh <tag>` from the repository root (or `tools/sync-beta.sh` to sync the five most recent betas).
3. Review `git diff releases/` and commit (`chore(releases): sync beta artifacts from <tag>`).
4. Push to GitHub and GitCode (dual push, or let the mirror follow).

## Verification

- `sha256sums.txt` lists **package-relative filenames**: `cd releases/<module>/<version> && sha256sum -c sha256sums.txt`.
- When the same version appears on both beta and stable, the sha256 must match; clients must refuse to install on a mismatch.

## Sync script

`tools/sync-beta.sh`: reads the public releases API of the fork (`LUOSENGWA/HiClaw`), downloads assets, computes sha256, writes this directory and updates `channels.json`; it never pushes.
This repository does not use GitHub Actions (removed at the maintainer's request in `b192fc5`; all gates run locally through `make test`).
