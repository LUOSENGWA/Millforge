# taskforge/ — TaskForge distribution slot (reserved)

This directory is the **distribution slot** for the `taskforge` module (the TaskForge).
**Not released yet**: this directory carries no artifacts (1.2.6 does not ship it; TaskForge is planned for 1.2.7), and the `taskforge` entry in
`releases/channels.json` stays a placeholder (`latest: null`, `versions: {}`).
When the Runner is actually released, this directory gains a `<version>/` subdirectory (tar.gz + manifest)
and the `channels.json` entry is filled in, per the contract below; clients download, verify, install, and
handshake following the load sequence — **no code changes to TH / ATMX / controller are required**.

**中文**: [README.md](README.md)

## Slot state (1.2.6 placeholder)

```json
"taskforge": {
  "kind": "runner",
  "latest": null,
  "versions": {},
  "note": "reserved in 1.2.6; the runner is not shipped with this release"
}
```

## Entry contract (channels.json `modules.taskforge`)

The contract is frozen with 1.2.6; **fields will not change**. After a release, the entry is filled as:

```json
"taskforge": {
  "kind": "runner",
  "latest": "0.1.0-beta.1",
  "versions": {
    "0.1.0-beta.1": {
      "artifacts": [
        {"name": "taskforge-0.1.0-beta.1.tar.gz", "sha256": "<64hex>"},
        {"name": "taskforge-0.1.0-beta.1.manifest.json", "sha256": "<64hex>"}
      ],
      "image": {"repository": "ghcr.io/luosengwa/taskforge", "digest": "sha256:<64hex>"},
      "requires": {"agentteams": ">=1.2.6", "contracts": "1", "tool_schema": "1", "millforge": ">=1.1.0"},
      "protocol_version": "1",
      "commit": "<40hex>",
      "published_at": "2026-11-04T00:00:00Z",
      "deprecated": false
    }
  }
}
```

- `kind`: fixed to `runner` (distinct from module artifacts such as `teamharness`).
- `latest`: the module's highest version on this channel; `null` until a release lands.
- `versions.<v>.artifacts`: downloadable artifacts, each with a sha256; **any mismatch is refused — no half-state is left behind**.
- `versions.<v>.image`: container image reference (repository + digest), optional.
- `versions.<v>.requires`: version windows the Runner depends on (`agentteams` / `contracts` / `tool_schema` / `millforge`).
- `versions.<v>.protocol_version`: the protocol version the Runner implements; it must fall within the window supported by the local controller/TH.
- `versions.<v>.commit`: the upstream commit that produced this release (traceability).
- `versions.<v>.published_at`: publication time (ISO8601 UTC).
- `versions.<v>.deprecated`: deprecation flag; files are kept, and clients must not install by default.

## Load sequence

The client (installer / workbench) **consumes only channels.json**; swapping the host does not change code
(GitHub raw and GitCode raw are equivalent):

```
1. GET <source>/releases/channels.json          # GitHub raw / GitCode raw
2. pick modules.taskforge.versions[<v>]        # channel=beta must be explicit; default is stable
3. download artifacts[*] → verify each sha256 (mismatch = refuse, no half-state)
4. read the manifest → check protocol_version against the local controller/TH supported window
5. install to <state>/taskforge/<version>/ (single writer: at most one running copy at a time)
6. start → POST /internal/runner/handshake → on handshake failure, exit (fail-closed)
7. handshake OK → the controller hands Loop scheduling over from the built-in ticker to the runner (within the same version window)
```

## Failure semantics (individually testable)

| Failure | Code | Behavior |
|:--|:--|:--|
| sha256 mismatch | `artifact_digest_mismatch` | do not install |
| `protocol_version` outside the supported window | `protocol_unsupported` | do not start |
| handshake failure | `handshake_rejected` | the process exits; the loop falls back to the built-in degradation (built-in ticker) |
| two copies start at the same time | `runner_already_active` | the later one exits (single-writer guarantee) |
