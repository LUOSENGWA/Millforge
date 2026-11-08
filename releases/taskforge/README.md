# taskforge/ — TaskForge 分发槽位（预留）

本目录是 `taskforge` 模块（TaskForge）的**分发槽位**。**当前未发布**：本目录不落地任何产物（1.2.6 不发；TaskForge 属 1.2.7 规划），
`releases/channels.json` 的 `taskforge` 条目保持占位（`latest: null`、`versions: {}`）。
Runner 真正发布后，按本文契约在本目录落 `<version>/` 子目录（tar.gz + manifest）并填 `channels.json` 条目；
客户端按加载序列下载、校验、安装、握手，**不需要改 TH / ATMX / controller 的任何代码**。

**English**: [README.en.md](README.en.md)

## 槽位现状（1.2.6 占位）

```json
"taskforge": {
  "kind": "runner",
  "latest": null,
  "versions": {},
  "note": "reserved in 1.2.6; the runner is not shipped with this release"
}
```

## 条目契约（channels.json `modules.taskforge`）

契约随 1.2.6 冻结，**字段不再变**。发布后条目填成：

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

- `kind`：固定 `runner`（区别于 `teamharness` 等模块产物）。
- `latest`：该模块在通道内的最高版本；未发布时为 `null`。
- `versions.<v>.artifacts`：可下载产物，逐个带 sha256；**任一不一致即拒绝，不落半态**。
- `versions.<v>.image`：容器镜像引用（repository + digest），可选。
- `versions.<v>.requires`：Runner 依赖的版本窗口（`agentteams` / `contracts` / `tool_schema` / `millforge`）。
- `versions.<v>.protocol_version`：Runner 实现的协议版本，须落在本地 controller/TH 支持的窗口内。
- `versions.<v>.commit`：产出该发布物的上游 commit（溯源）。
- `versions.<v>.published_at`：发布时间（ISO8601 UTC）。
- `versions.<v>.deprecated`：停用标记；保留文件，客户端不应默认安装。

## 加载序列

客户端（安装器 / 工作台）**只认 channels.json**；换托管方不改代码（GitHub raw / GitCode raw 等价）：

```
1. GET <source>/releases/channels.json          # GitHub raw / GitCode raw
2. 选 modules.taskforge.versions[<v>]           # channel=beta 需显式；默认 stable
3. 下载 artifacts[*] → 逐个 sha256 校验（不一致 = 拒绝，不落半态）
4. 读 manifest → 校验 protocol_version 与本地 controller/TH 支持的窗口
5. 安装到 <state>/taskforge/<version>/（单写者：同一时刻只允许一个在跑副本）
6. 启动 → POST /internal/runner/handshake → 握手失败即退出（fail-closed）
7. 握手成功 → controller 把 Loop 的调度权从内置 ticker 切给 runner（同版本窗口内）
```

## 失败语义（逐条可测）

| 失败 | 码 | 行为 |
|:--|:--|:--|
| sha256 不符 | `artifact_digest_mismatch` | 不安装 |
| `protocol_version` 不在支持窗口 | `protocol_unsupported` | 不启动 |
| 握手失败 | `handshake_rejected` | 进程退出，loop 回退到内置降级（内置 ticker） |
| 两个副本同时启动 | `runner_already_active` | 后到者退出（单写者保证） |
