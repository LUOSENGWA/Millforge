# Alpha channel install guide (0.1.1-alpha.2)

> For the **alpha** channel (`releases/alpha/channels.json`). The stable channel still indexes
> releases only. Both 0.1.1-alpha.2 plugin zips are install-as-downloaded: the teamharness zip root
> is `teamharness-qwenpaw-0.1.1-alpha.2/`, the matrix zip root is `agentteams-matrix-channel/`.
> The plugin loads by the id in `plugin.json`; do not hand-edit the manifest.

## 1. Artifacts

| Module | Artifact | Purpose |
|---|---|---|
| `agentteams-matrix` | `agentteams-matrix-channel-0.1.1-alpha.2.zip` | QwenPaw channel plugin (Matrix channel + sync core) |
| `teamharness` | `teamharness-qwenpaw-0.1.1-alpha.2.zip` | TeamHarness QwenPaw plugin (MCP tool surface + skills) |
| both | `*.tar.gz` | Bundle source package (`plugin.yaml`/`contracts/`/`adapters/`) for the Controller / module install |

Each version directory carries `sha256sums.txt` and `release-manifest.json`;
`releases/alpha/channels.json` is the channel index, and the three sha256 values must agree
(`make test` enforces it).

## 2. Install the QwenPaw plugin (same for both artifacts)

```bash
# agentteams-matrix shown; teamharness works the same
cd <QWENPAW_WORKING_DIR>/plugins
unzip -q agentteams-matrix-channel-0.1.1-alpha.2.zip     # yields plugins/agentteams-matrix-channel/
# teamharness: unzip -q teamharness-qwenpaw-0.1.1-alpha.2.zip # yields plugins/teamharness-qwenpaw-0.1.1-alpha.2/
# restart the QwenPaw worker (or its plugin runtime); the plugin loads by its plugin.json id
```

- Top directory: matrix = `agentteams-matrix-channel/`, teamharness = `teamharness-qwenpaw-0.1.1-alpha.2/`;
  the plugin loads by the `plugin.json` id — do not hand-edit the manifest.
- The package contains no `__pycache__`/`.pyc` (the build compiles outside the staging tree).

## 3. Install the bundle (Controller / module install)

The `*.tar.gz` top level is the bundle content (`plugin.yaml` or `plugin.json` + `contracts/` +
`adapters/`), usable directly as a module package. `release-manifest.json` declares
`requires`: `agentteams >= 1.2.6`, `contracts: 1`, `tool_schema: 1`.

## 4. Verify

```bash
sha256sum -c sha256sums.txt     # run inside the version directory
```

## 5. Known boundaries (stated honestly)

- `release-manifest.commit` records the source revision used for this build; verify artifact integrity by sha256.
- `0.1.1-alpha.2` is published to the alpha channel only; `stable`/`beta` do not point at it.
