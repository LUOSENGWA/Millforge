# Alpha channel install guide (0.1.1-alpha.1)

> For the **alpha** channel (`releases/alpha/channels.json`). The stable channel still indexes
> releases only. Both 0.1.1-alpha.1 artifacts are **install-as-downloaded**: the zip root is the
> plugin id, so nothing has to be renamed.

## 1. Artifacts

| Module | Artifact | Purpose |
|---|---|---|
| `agentteams-matrix` | `agentteams-matrix-channel-0.1.1-alpha.1.zip` | QwenPaw channel plugin (Matrix channel + sync core) |
| `teamharness` | `teamharness-qwenpaw-0.1.1-alpha.1.zip` | TeamHarness QwenPaw plugin (MCP tool surface + skills) |
| both | `*.tar.gz` | Bundle source package (`plugin.yaml`/`contracts/`/`adapters/`) for the Controller / module install |

Each version directory carries `sha256sums.txt` and `release-manifest.json`;
`releases/alpha/channels.json` is the channel index, and the three sha256 values must agree
(`make test` enforces it).

## 2. Install the QwenPaw plugin (same for both artifacts)

```bash
# agentteams-matrix shown; teamharness works the same — the top directory is the plugin id
cd <QWENPAW_WORKING_DIR>/plugins
unzip -q agentteams-matrix-channel-0.1.1-alpha.1.zip     # yields plugins/agentteams-matrix-channel/
# restart the QwenPaw worker (or its plugin runtime); the plugin loads by its plugin.json id
```

- The zip's top-level directory **is** the plugin id (`agentteams-matrix-channel` / `teamharness`) —
  do not rename it.
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

- This alpha is built from the AT integration branch; the `commit` field is the local build commit
  and is not yet present in a public repository. The stable channel is unaffected; the same content
  will land through PRs and the field will be rewritten then.
- `0.1.1-alpha.1` is published to the alpha channel only; `stable`/`beta` do not point at it.
- The dashboard (workbench) entry is planned; until then install with the commands above.
