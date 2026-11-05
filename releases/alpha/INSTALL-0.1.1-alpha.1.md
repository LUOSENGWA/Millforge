# Alpha 通道安装说明（0.1.1-alpha.1）

> 适用于 **alpha** 通道（`releases/alpha/channels.json`）。stable 通道仍只索引正式版。
> 0.1.1-alpha.1 的两个产物都**解压即用**（zip 顶层目录 = 插件 id，无需改名）。

## 1. 取产物

| 模块 | 产物 | 说明 |
|---|---|---|
| `agentteams-matrix` | `agentteams-matrix-channel-0.1.1-alpha.1.zip` | QwenPaw 通道插件（Matrix 通道 + 同步核心） |
| `teamharness` | `teamharness-qwenpaw-0.1.1-alpha.1.zip` | TeamHarness QwenPaw 插件（MCP 工具面 + skills） |
| 两者 | `*.tar.gz` | bundle 源包（含 `plugin.yaml`/`contracts/`/`adapters/`），供 Controller/模块安装使用 |

每个版本目录都带 `sha256sums.txt` 与 `release-manifest.json`；`releases/alpha/channels.json` 是通道索引，
三处 sha256 必须一致（`make test` 会校验）。

## 2. 安装 QwenPaw 插件（两种产物相同）

```bash
# 以 agentteams-matrix 为例；teamharness 同理，顶层目录都是插件 id
cd <QWENPAW_WORKING_DIR>/plugins
unzip -q agentteams-matrix-channel-0.1.1-alpha.1.zip     # 得到 plugins/agentteams-matrix-channel/
# 重启 QwenPaw worker（或它的插件运行时），插件按 plugin.json 的 id 加载
```

- zip 内顶层目录 = 插件 id（`agentteams-matrix-channel` / `teamharness`）——**不要改名**。
- 包内不含 `__pycache__`/`.pyc`（构建时把编译输出放在 staging 之外）。

## 3. 安装 bundle（Controller / 模块安装用）

`*.tar.gz` 的顶层就是 bundle 内容（`plugin.yaml` 或 `plugin.json` + `contracts/` + `adapters/`），
可直接作为模块包使用；`release-manifest.json` 的 `requires` 声明了 `agentteams >= 1.2.6`、
`contracts: 1`、`tool_schema: 1`。

## 4. 校验

```bash
sha256sum -c sha256sums.txt     # 在版本目录内执行
```

## 5. 已知边界（如实）

- 本 alpha 的源码提交来自 AT 集成分支（`commit` 字段为本地构建提交，尚未出现在公开仓）；
  stable 通道不受影响，后续会把同内容随 PR 落地并改写该字段。
- `0.1.1-alpha.1` 只发布 alpha 通道；`stable`/`beta` 不指向它。
- 前端（工作台）入口按计划后续接入，当前请按上面命令手动安装。
