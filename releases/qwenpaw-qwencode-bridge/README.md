# 模块：`qwenpaw-qwencode-bridge`

> QwenPaw 的编码 CLI 桥接插件（dispatch / 状态 / 唤醒 / 审批映射 / 原生 web 控制台）。
> 源码：`agentscope-ai/AgentTeams` → `plugins/qwen-code-bridge`（#1411 合并提交 `c31dc45df`）。
> 本目录只承载**可下载产物 + 发布清单**；源码与测试在上游仓。

## 1. 身份

| 字段 | 值 |
|---|---|
| 模块键（索引 `modules.<key>`） | `qwenpaw-qwencode-bridge` |
| QwenPaw plugin id | `qwen-code-bridge` |
| `kind` | `plugin` |
| `runtime` | `qwenpaw`（专属，无 adapters 分层；不宣称 runtime-neutral） |
| 后端包 / HTTP 前缀 | `qwen_code_bridge` / `/api/qwen-code-bridge` |
| 依赖 | `qwenpaw >=2.2.0 <2.3.0`、`qwen-code-cli 0.26.x` |

## 2. 版本与通道

| 通道 | latest | 说明 |
|---|---|---|
| **stable** | **0.3.0** | 首个 stable；版本号 = 上游清单版本（不再做发布侧重写） |
| beta | `null` | 模块已开位，无版本 |
| alpha | `null` | 模块已开位，无版本 |

版本纪律：`releases/<module>/<version>/` 的版本 = 产物内 `plugin.json` 的 `version` = 索引条目的版本，三者必须一致；任何预发布用 `-alpha.N` / `-beta.N` 后缀。

## 3. 产物

| 项 | 值 |
|---|---|
| 文件 | `qwenpaw-qwencode-bridge-0.3.0.zip` |
| 大小 | 126,422 B |
| 文件数 | 34（根目录 `qwen-code-bridge/`，已排除 `tests/`、`__pycache__`、`web-shell/dist`） |
| sha256 | `01efceee…`（完整值见同目录 `sha256sums.txt`） |
| 源码 commit | `c31dc45df` |

校验：`cd releases/qwenpaw-qwencode-bridge/0.3.0 && sha256sum -c sha256sums.txt`

## 4. 安装

**A. 集群内（推荐，走后端模块更新）**
```bash
# worker 平面
curl -X POST http://<controller>/api/v1/workers/<worker>/plugins/install \
  -H 'Content-Type: application/json' \
  -d '{"module":"qwenpaw-qwencode-bridge","source":"github","repo":"LUOSENGWA/millforge","ref":"main","channel":"stable"}'
# team 平面（按 workerMembers 滚动，失败即停）
curl -X POST http://<controller>/api/v1/teams/<team>/modules/qwenpaw-qwencode-bridge/install -d '{"source":"github","channel":"stable"}'
```
省略 `version` 用索引 `latest`；后端重读索引取 sha256，body 的 sha256 不一致返回 409。

**B. 单机 QwenPaw（下载后热加载）**
```bash
unzip qwenpaw-qwencode-bridge-0.3.0.zip -d "$QWENPAW_WORKING_DIR/plugins"
# 或走官方上传（热加载）
curl -X POST http://127.0.0.1:8088/api/plugins/upload?force=true \
  -F 'file=@qwenpaw-qwencode-bridge-0.3.0.zip;type=application/zip'
curl -s http://127.0.0.1:8088/api/plugins | grep qwen-code-bridge   # 确认 loaded
```

## 5. 接口（前缀 `/api/qwen-code-bridge`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/version` | `{plugin, started_at, python, qwen_cli, state_dir}` |
| GET | `` | 路由总览 |
| GET | `/dispatch` | 任务列表（`?format=table` 出状态表） |
| POST | `/dispatch` | 派单（202，返回 `task_id`） |
| GET | `/dispatch/{id}` | 任务详情 |
| GET | `/dispatch/{id}/progress` | 进度（turns/elapsed/stalled/phase/last_target） |
| GET | `/dispatch/{id}/log` | 日志流 |
| GET | `/dispatch/{id}/pending` | 待人工回答的问题 |
| POST | `/dispatch/{id}/answer` | 回答问题 |
| POST | `/dispatch/{id}/cancel` | 取消（SIGTERM→grace→SIGKILL） |
| POST | `/dispatch/{id}/stop` | 停止 |
| POST | `/dispatch/cleanup` | 清理终态任务 |
| GET | `/dispatch/{id}/run` · `/qwen/status` · `/dispatch/{id}/qwen-status` | 运行时状态 |
| GET | `/approvals` | 审批回执审计（`task_id`/`behavior`/`since`/`limit`） |
| GET | `/chat/{chat_id}` · POST `/sidebar` | 会话侧栏 |
| GET/PUT | `/{cli_id}/settings` | CLI 设置 |
| POST | `/{cli_id}/install` · GET `/{cli_id}/install/{task_id}` | CLI 安装（202） |

## 6. 升级与回滚

- 升级：重复安装即可（热加载，`loaded=true` 即生效）；在途任务由启动钩子的孤儿清理兜底。
- 回滚：装回上一版本目录；任务文件是字段超集，旧版忽略未知字段。
- 索引 `deprecated: true` 的版本不建议默认安装。

## 7. 已知缺口（上游待修，不影响本产物使用）

| # | 项 | 说明 |
|:--:|---|---|
| 1 | 上游 `README.md` 陈旧 | 测试数写 252p/1s（实测 304p/1s）、示例仍用 0.2.0 zip、通道描述仍写「千锻=beta / releases/channels.json」 |
| 2 | 上游 `CHANGELOG.md` 通道描述陈旧 | 0.3.0 的 Changed 段仍写「AT=stable / 千锻=beta」 |
| 3 | `scripts/package.sh` 未排除 `.pytest_cache` | 在跑过测试的源目录里打包会把缓存打进 zip（本产物从干净源构建，已避开） |
| 4 | 上游 README 缺部分路由 | `/chat/{id}`、`/dispatch/cleanup`、`/qwen/status`、`/dispatch/{id}/run`、`/cancel`、`/stop` 未文档化（本 README 第 5 节已补全） |
