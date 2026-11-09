# taskforge/ — TaskForge 分发包

TaskForge 是 AgentTeams 的任务管理模块。本目录用于发布可下载的 TaskForge 模块产物和版本索引。

> **当前状态**：尚未发布任何版本；发布后条目写入对应通道的 `releases/{alpha,beta,stable}/channels.json`。

**English**: [README.en.md](README.en.md)

## 产物布局

发布后按版本放置：

```text
releases/taskforge/<version>/
  taskforge-<version>-linux-amd64.tar.gz
  taskforge-<version>-linux-arm64.tar.gz
  taskforge-<version>.manifest.json
  sha256sums.txt
```

每个压缩包包含：

- `taskforged` 可执行文件
- 数据库迁移文件
- 安装/升级/回滚脚本或服务模板
- 模块契约文件

## 版本索引

`releases/stable/channels.json` 的 `taskforge` 条目示例（beta/alpha 结构相同）：

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

## 运行要求

- Linux amd64/arm64；单实例运行（不做多副本同时写）。
- **生产：seekdb server**；本地开发可用 embedded seekdb。
- v1 不支持 SQLite、OceanBase 作为 TaskForge 后端。
- TaskForge 只负责 `work` 任务数据；对象字节由外部对象存储保存，任务库只存引用。
- Controller 通过内部网关调用 TaskForge，不直接暴露任务端口。
- 身份认证与权限由 Controller 负责；TaskForge 只接受 Controller 的服务调用，不面向终端用户直接登录。

完整的版本要求、兼容窗口和数据库要求以 `manifest.json` 及对应版本的发布说明为准。

## 安装与升级

1. 从 `channels.json` 选择版本，下载对应平台产物。
2. 逐个校验 `sha256`；不一致时停止。
3. 阅读 `manifest.json` 的版本和兼容要求。
4. 停止旧实例，备份现有数据库。
5. 应用包内迁移文件。
6. 启动新版本并检查健康状态。
7. 同一时间只运行一个实例；升级时不要并行启动新旧实例。
8. 失败时停止新实例，恢复数据库备份并启动旧版本。

## 回滚

保留上一版本的完整压缩包和升级前数据库备份。回滚时：

1. 停止当前实例。
2. 恢复升级前数据库备份。
3. 启动上一版本。
4. 检查健康和任务服务状态。

## 校验

```bash
cd releases/taskforge/<version>
sha256sum -c sha256sums.txt
```

