# 域片段：Web 后端（web-backend）

> T2 域片段 · source: production | 适用: worker | spawn 域: web-backend

## 上下文输入（spawn 从文件读）

- 服务架构说明 + API 路由表（文件引用）
- 目标接口/模块代码路径（ref）+ 数据模型定义
- 测试基线（现有测试清单）

## 执行约束

- 接口变更 = contract 变更（semver + 双确认 S3）；新增接口走 contract 流程
- 向后兼容默认：改接口先查调用方（grep 引用面）
- 错误处理：错误路径必须有显式处理（scorecard 含错误注入验证）
- 测试：新增/修改代码 = 测试同步（无测试 = 验收项 ❌）
- 数据库迁移 = R1（人知情）；migration 可回滚检查

## 验收要点（critic 视角）

- 接口验证 = 实际调用（curl/API 客户端，附响应证据）
- 并发面：写路径的幂等/竞态检查（spec 声明则验证）
- 安全面：输入校验/注入面/权限检查（security 域交叉）
- 回归：现有测试全绿 + 改动面引用检查
