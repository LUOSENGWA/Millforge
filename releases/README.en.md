# releases/ — module distribution mirror (alpha / beta / stable)

This directory mirrors **module artifacts** (`teamharness` / `agentteams-matrix` / `qwen-code-bridge` / `taskforge`).

**Current beta staging (2026-11-04):** `teamharness` 0.1.0 (`teamharness-qwenpaw-0.1.0.zip` / `teamharness.tar.gz`) and `agentteams-matrix` 0.1.0 (`agentteams-matrix-channel-0.1.0.zip` / `agentteams-matrix.tar.gz`); the entries live in `releases/beta/channels.json` and record `pluginId=agentteams-matrix-channel`.

It is not a build directory: artifacts are built by the upstream repository (AgentTeams release workflow); this directory only carries downloadable copies and indexes. **There is no automatic sync**; indexes are committed by the release/manual process, and the front-end checks updates per selected channel.

> Why repository content instead of GitHub Releases only: ordinary git mirrors (including GitCode, which does not mirror releases) sync repository content. Keeping artifacts here gives GitHub and GitCode the same `raw` URLs.

## Layout

```
releases/
├── alpha/channels.json       # alpha channel index
├── beta/channels.json        # beta channel index
├── stable/channels.json      # stable channel index
├── <module>/
│   └── <version>/
│       ├── <module>-<version>.tar.gz
│       ├── <module>-<version>-qwenpaw.zip
│       ├── sha256sums.txt
│       └── release-manifest.json
```

- `<module>`: `teamharness` / `agentteams-matrix` / `qwen-code-bridge` / `taskforge`.
- `<version>`: alpha = `<semver>-alpha.N`, beta = `<semver>-beta.N`, stable = `<semver>`.
- **The channel selects the index file only; artifact paths are always `releases/<module>/<version>/<artifact>`**.
- Keep old version directories; rollback reinstalls an older version.

## channels.json

One index per channel; the `channel` field must match the directory.

```json
{
  "schema": 1,
  "channel": "beta",
  "updated_at": "2026-11-03T00:00:00Z",
  "modules": {
    "teamharness": {
      "kind": "plugin",
      "latest": "0.1.0",
      "versions": {
        "0.1.0": {
          "artifacts": [
            {"name": "teamharness-qwenpaw-0.1.0.zip", "sha256": "…"},
            {"name": "teamharness.tar.gz", "sha256": "…"}
          ],
          "requires": {"agentteams": ">=1.2.6", "contracts": "1", "tool_schema": "1"},
          "commit": "…",
          "published_at": "2026-11-03T00:00:00Z",
          "deprecated": false
        }
      }
    }
  }
}
```

- `latest` is the highest version in that channel; older versions remain selectable.
- `kind`: `plugin` / `bundle` / `runner`; `plugin` = `teamharness` / `qwen-code-bridge`, `bundle` = `agentteams-matrix`, `runner` = `taskforge` (not shipped in 1.2.6).
- `pluginId`: the plugin id QwenPaw actually installs; defaults to the module name. MX uses `agentteams-matrix-channel`.
- `deprecated: true`: keep the files but do not offer the version by default.
- Clients read the selected channel index; the controller fetches `releases/<channel>/channels.json`.

## Channel rules

| channel | tag | GitHub Release | Index / artifacts |
|---|---|---|---|
| alpha | `<module>-v<semver>-alpha.N` | no Release | commit `releases/alpha/channels.json` + artifacts |
| beta | `<module>-v<semver>-beta.N` | prerelease (optional, for records/manual pickup) | copy to `releases/beta/channels.json` + artifacts |
| stable | `<module>-v<semver>` | release (optional) | copy to `releases/stable/channels.json` + artifacts |

**No automatic sync**: beta/stable Releases are not a client dependency and do not write this repo automatically; the index and artifacts must be committed explicitly. Alpha does not create a Release.

## Adding a version

1. Tag and build the upstream artifact for the target channel.
2. Put the artifact in `releases/<module>/<version>/`.
3. Update `versions` and `latest` in `releases/<channel>/channels.json`.
4. Verify sha256, commit, and push to GitHub + GitCode.

**Do not delete old versions**; stable rollback relies on the old directories and `versions` entries.

## Verification

- `sha256sums.txt` uses package-relative names: `cd releases/<module>/<version> && sha256sum -c sha256sums.txt`.
- If the same version appears in beta and stable, the sha256 must match; otherwise clients must refuse to install.

## Scripts

`tools/sync_beta.py` is a **legacy beta-only helper** (handles `-beta.N` and writes `releases/beta/channels.json`); it is not part of the runtime/auto-update flow. Do not use it for alpha/stable. This repository does not use GitHub Actions for automatic sync.

## Download and install: 0.1.1-alpha.2 (alpha channel)

The alpha channel provides accepted TeamHarness/Matrix builds for direct installation from this repository; production users should use the stable channel.

1. Pick the artifact under `releases/<module>/0.1.1-alpha.2/` (`*.tar.gz` bundle, or the `*-qwenpaw-0.1.1-alpha.2.zip` / `agentteams-matrix-channel-0.1.1-alpha.2.zip` single-plugin package).
2. Verify the single file: `grep ' <file>$' sha256sums.txt | sha256sum -c`.
3. Install (QwenPaw): `tar xzf <bundle>.tar.gz && QWENPAW_WORKING_DIR="${QWENPAW_WORKING_DIR:-$HOME/.qwenpaw}" bash scripts/install.sh --adapter qwenpaw`. Re-running is idempotent; `scripts/uninstall.sh` removes exactly the installed files.
4. Cluster auto-update reads `releases/<channel>/channels.json` (bundle entries carry `kind=bundle`, `pluginId=agentteams-matrix-channel`, per-version `artifacts`/`requires`/`commit`/`published_at`/`deprecated`).

Known limits: alpha builds publish no GitHub Release; `release-manifest.commit` records the source revision, and artifact integrity is verified by sha256 across the GitHub and GitCode mirrors.
