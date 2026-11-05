# releases/ — 模块分发镜像（alpha / beta / stable）

本目录是**模块产物的分发镜像**（`teamharness` / `agentteams-matrix` / `qwen-code-bridge` / `looprunner`）。

**当前 beta 暂存（2026-11-04）**：`teamharness` 0.1.0（`teamharness-qwenpaw-0.1.0.zip` / `teamharness.tar.gz`）与 `agentteams-matrix` 0.1.0（`agentteams-matrix-channel-0.1.0.zip` / `agentteams-matrix.tar.gz`）；条目在 `releases/beta/channels.json`，已写入 `pluginId=agentteams-matrix-channel`。

它不是构建目录：产物由上游仓库（AgentTeams 的发布 workflow）构建，本目录只承载**可下载的副本 + 索引**。**不做自动同步**；索引由发布操作/人工提交，前端按 channel 检查更新。

> 为什么放仓库内容而不是只依赖 GitHub Releases：普通 git 镜像（包括没有 release 镜像能力的 GitCode）只同步仓库内容。放这里，GitHub 与 GitCode 两侧都能用同一套 `raw` URL 拉取。

## 布局

```
releases/
├── alpha/channels.json       # alpha 通道索引
├── beta/channels.json        # beta 通道索引
├── stable/channels.json      # stable 通道索引
├── <module>/
│   └── <version>/
│       ├── <module>-<version>.tar.gz
│       ├── <module>-<version>-qwenpaw.zip
│       ├── sha256sums.txt
│       └── release-manifest.json
```

- `<module>`：`teamharness` / `agentteams-matrix` / `qwen-code-bridge` / `looprunner`。
- `<version>`：alpha = `<semver>-alpha.N`，beta = `<semver>-beta.N`，stable = `<semver>`。
- **channel 只决定索引文件；artifact 路径始终是 `releases/<module>/<version>/<artifact>`**。
- 旧版本目录保留，不删除；回滚靠重新安装旧版本。

## channels.json

每个 channel 一个独立索引；`channel` 字段必须与目录一致。

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

- `latest` = 该 channel 内最高版本；旧版本继续保留，安装时可显式指定。
- `kind`：`plugin` / `bundle` / `runner`；`plugin` = `teamharness` / `qwen-code-bridge`，`bundle` = `agentteams-matrix`，`runner` = `looprunner`（1.2.6 暂不发布）。
- `pluginId`：QwenPaw 内实际安装的 plugin id；缺省 = 模块名。MX 为 `agentteams-matrix-channel`。
- `deprecated: true`：标记停用但保留文件；客户端不应默认安装。
- 客户端（安装器 / 工作台）只认所选 channel 的这份契约；controller 取 `releases/<channel>/channels.json`。

## 渠道规则

| channel | tag | GitHub Release | 索引/产物 |
|---|---|---|---|
| alpha | `<module>-v<semver>-alpha.N` | 不建 Release | 直接提交 `releases/alpha/channels.json` + 产物 |
| beta | `<module>-v<semver>-beta.N` | 建 prerelease（可选，人工取件/记录） | 人工/CI 复制到 `releases/beta/channels.json` + 产物 |
| stable | `<module>-v<semver>` | 建正式 release（可选） | 人工/CI 复制到 `releases/stable/channels.json` + 产物 |

**不提供自动同步**：beta/stable 的 Release 不是客户端依赖，也不会自动写入本仓；必须显式提交索引和产物。alpha 不建 Release。

## 如何新增一个版本

1. 上游打对应 channel 的 tag，构建产物。
2. 把产物放到 `releases/<module>/<version>/`。
3. 更新对应 `releases/<channel>/channels.json` 的 `versions` 和 `latest`。
4. 校验 sha256，提交并双推 GitHub + GitCode。

**不要删除旧版本**；stable 回滚依赖旧目录和旧 `versions` 条目。

## 校验

- `sha256sums.txt` 使用**包相对文件名**：`cd releases/<module>/<version> && sha256sum -c sha256sums.txt`。
- 同版本号在 beta 与 stable 两个源都出现时，sha256 必须一致；不一致时客户端应拒绝安装。

## 脚本

`tools/sync_beta.py` 是 **beta-only 的旧助手**（只处理 `-beta.N`，写 `releases/beta/channels.json`），不属于运行时/自动更新流程；alpha/stable 不要依赖它。本仓库不使用 GitHub Actions 自动同步。
