# releases/ — beta 分发镜像

本目录是**模块产物的分发镜像**（`teamharness` / `agentteams-matrix` / 之后的 `looprunner`）。
它不是构建目录：产物由上游仓库（AgentTeams 的发布 workflow）构建，本目录只承载**可下载的副本 + 索引**。

> 为什么放仓库内容而不是 GitHub Releases：普通 git 镜像（包括没有 release 镜像能力的 GitCode）只同步仓库内容。放这里，GitHub 与 GitCode 两侧都能用同一套 `raw` URL 拉取。

## 布局

```
releases/
├── channels.json            # 通道索引（唯一入口）
├── <module>/
│   └── <version>/
│       ├── <module>-<version>.tar.gz
│       ├── <module>-<version>-qwenpaw.zip
│       ├── sha256sums.txt
│       └── release-manifest.json
```

- `<module>`：`teamharness` / `agentteams-matrix` / `looprunner`。
- `<version>`：beta 为 `<semver>-beta.N`（例如 `0.3.0-beta.2`）。
- 产物原样保留上游 release 的资产；`sha256sums.txt` 与 `release-manifest.json` 若上游已提供则原样放入，未提供则由同步脚本生成 sha256。

## channels.json

```json
{
  "schema": 1,
  "channel": "beta",
  "updated_at": "2026-11-03T00:00:00Z",
  "modules": {
    "teamharness": {
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

- `latest` = 该模块最高版本（beta 通道内）。
- `deprecated: true`：标记停用但保留文件；客户端不应默认安装。
- `requires` 来自上游 release 的 `release-manifest.json`；缺失时留空对象并在同步时告警。
- 客户端（安装器 / 工作台）只认这份契约；stable 通道用同一 schema，托管在别处（官方仓 / controller 内置 / 对象存储镜像三选一）。

## 如何新增一个版本

1. 上游打 tag `<module>-v<semver>-beta.N`（prerelease）。
2. 在仓库根运行 `tools/sync-beta.sh <tag>`（或 `tools/sync-beta.sh` 同步最近 5 个 beta）。
3. 检查 `git diff releases/`，提交（`chore(releases): sync beta artifacts from <tag>`）。
4. 推送 GitHub + GitCode（双推，或镜像自动跟随）。

## 校验

- `sha256sums.txt` 使用**包相对文件名**：`cd releases/<module>/<version> && sha256sum -c sha256sums.txt`。
- 同版本号在 beta 与 stable 两个源都出现时，sha256 必须一致；不一致时客户端应拒绝安装。

## 同步脚本

`tools/sync-beta.sh`：只读公开 API 下载 fork（`LUOSENGWA/HiClaw`）的 release 资产，计算 sha256，写入本目录并更新 `channels.json`，**不自动 push**。
本仓库不使用 GitHub Actions（`b192fc5` 起按维护者要求移除；全部门在 `make test` 本地跑）。
