# taskforge/ — TaskForge 模块（独立分发包，未发布）

> **状态（2026-11-08）**：TaskForge = 原 LoopRunner；模块 id **`taskforge`**、进程 **`taskforged`**、kind **`runner`**。当前为 **1.2.7 规划占位**，1.2.6 不发布；`releases/channels.json` 的 `taskforge` 条目保持 `latest: null`、`versions: {}`。
>
> **不是 QwenPaw 插件**：TaskForge 是 AgentTeams 后面的任务组件，安装走 TaskForge installer / Controller module host（安装面仍待确认）；API 只经 Controller 网关。旧 #1509/#1510 的 standalone runner API 已由 #1508 撤回，不作为本模块安装面。

**English**: [README.en.md](README.en.md)

## 1. 产物布局

发布时按版本落：

```text
releases/taskforge/<version>/
  taskforge-<version>-linux-amd64.tar.gz
  taskforge-<version>-linux-arm64.tar.gz
  taskforge-<version>.manifest.json
  sha256sums.txt
```

每个 tar 包含：

- `taskforged` 二进制（对应平台）；
- `migrations/`（`work` schema 迁移；版本与 manifest `work_schema` 对齐）；
- `install.sh` / `update.sh` / `rollback.sh`（或等价 systemd/container 启动模板）；
- `contracts/`（TaskForge 内部 API/事件契约；不含 TH/MX 插件）。

源码/构建在 AgentTeams 仓（TaskForge 源），**千锻仓只放可下载产物 + channels 索引**；不在本仓复制源码。

## 2. `channels.json` 条目

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

- `kind` 固定 `runner`（TaskForge 是独立服务，不是 QwenPaw 插件，也不是 TH/MX bundle）。
- `artifacts` 逐项 sha256；安装器必须全验，失败不落半态。
- `requires.work_schema` 是 DB 迁移契约；`protocol_version` 是 Controller/TaskForge API 契约；`agentteams` 是网关/认证最低版本。
- `image` 可选；有 OCI 镜像时安装器优先用 digest，没有则用 tar + install.sh。

## 3. 独立更新流程

TaskForge 更新**不重建 Controller 镜像**；Controller 只保留通用网关/协议窗口：

```text
1. 读 channels.json → 选 taskforge 版本
2. 下载 artifacts → 逐个 sha256 校验
3. 读 manifest → 校验 protocol_version / work_schema / agentteams 窗口
4. 停旧 taskforged（单写者；先停后起，不并行）
5. 备份 seekdb work schema（04 的 snapshot_id 同步）
6. 运行 taskforged migrate（向前兼容；失败则回滚）
7. 启动新版本 → /healthz /readyz → 校验 DB schema_version
8. Controller 只切 TASKFORGE_URL / 网关；不重建 Controller
9. 失败：停新 → 恢复备份 → 启动旧版本；保留旧 tar/DB 备份
```

- **单写者**：同一时刻只允许一个 `taskforged` 活跃副本；先停旧再起新，不可双写。
- **迁移/回滚**：数据库迁移必须向前兼容；降级不保证自动反向迁移，回滚依赖备份。
- **更新窗口**：TaskForge 不可用期间任务写 API 返回 503；不回退文件写（无 meta.json 双写）。
- **Controller 协议变化**：只有 `protocol_version` 超窗时才需要升级 Controller；普通 TaskForge 版本升级不需要重建 Controller。
- **数据/记忆/存储**：TaskForge 只写 `work` schema；不写 memory/resources；artifact bytes 走 04；全量备份需 DB + 对象 `snapshot_id` 对齐。

## 4. 失败语义

| 失败 | 码 | 行为 |
|:--|:--|:--|
| sha256 不符 | `artifact_digest_mismatch` | 不安装，不落半态 |
| protocol/work_schema 不在窗口 | `protocol_unsupported` / `schema_unsupported` | 不启动 |
| 迁移失败 | `migration_failed` | 保持旧版本/备份，Controller 503 |
| health/ready 失败 | `taskforge_unhealthy` | 停新，回旧；不切流量 |
| 两个副本同时启动 | `taskforge_already_active` | 后到者退出（单写者 lease） |
| 任务 API 不可用 | `taskforge_unavailable` | Controller 返回 503，不回退文件写 |

## 5. 边界

- **DB 唯一后端 seekdb**：生产 `server`；embedded 仅本地/单进程（已确认）；SQLite 不进入 TaskForge 运行后端。
- **checkpoint 不用 Git**：DB 逻辑快照 + `task_events`；Git 仅可作产物引用。
- **API 只经 Controller**：TaskForge 内部 API 不暴露公网；TeamHarness/Matrix/Dashboard 都走 Controller 网关。
- **独立 ≠ 独立 runner API**：TaskForge 独立的是版本/产物/安装/升级/回滚；#1508 已撤回 standalone runner API。
- **安装面仍待确认**：自带 installer / Controller module host 尚未拍板；本文只定义产物/更新契约。
- **跨线**：[`13-TaskForge与03-04-11咬合-20261108.md`](../../../../方案与设计/AgentTeams/下版本1.2.6-1.2.7/13-TaskForge与03-04-11咬合-20261108.md)。
