# 行业模板：软件（software）

> T1 行业片段 · source: production（软件研发团队实战）
> 适用角色: worker / leader / critic

## worker 行业约束

- **上下文隔离强化**：仓库级任务（clone/构建/测试）必须 spawn 隔离——native session 只做拆解与验收。构建输出/日志不进对话（写文件，引用路径）
- **Git 纪律**：只 add 具体文件（禁 `git add -A`/`add .`）；commit 前 `git status --short` 核对暂存区；rebase/cherry-pick 期间单端操作
- **验证 = 运行**：代码产出验收 = 构建通过 + 测试通过 + 关键路径手工验证（scorecard 每条可执行）
- **环境区分**：容器/宿主/挂载路径三查（目标是否持久卷 / 权限 / 相对路径解析）；docker 操作先 `docker ps` + `docker exec` 验证实际状态，不假设
- **依赖版本**：pip/npm 版本 = 功能时间线依据（changelog 优先，不凭版本反推功能）
- **编译产物**：输出路径三查（容器是否 --rm / 目标卷 / 权限）

## leader 行业约束

- 拆解粒度 = 可独立验收的模块（有明确文件边界 + 测试面）
- 跨模块任务先定接口契约（contract artifact），后并行派发
- CI/部署类任务 = R1（人知情）

## critic 行业约束（审核视角）

- 可执行验证优先：grep/build/test/API 调用 > 读代码判断
- 隔离边界：不进被审方容器执行；🔵 项限于 API 端点/对象存储/CI 状态
- 审核维度：正确性（测试+逻辑）/ 边界（错误路径）/ 回归（影响面 grep）/ 安全（注入面/权限面）
