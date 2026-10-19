# 域片段：Web 前端（web-frontend）

> T2 域片段 · source: production | 适用: worker | spawn 域: web-frontend
> 派发时注入 spawn 的 task spec（不是身份文件内容）

## 上下文输入（spawn 从文件读）

- 项目结构说明 + 组件树/路由表（文件引用，不倒源码进对话）
- 目标组件/页面的现有代码路径（ref）
- 设计稿/交互说明（如有）

## 执行约束

- 技术栈以项目锁定版本为准（package.json = contract，不改依赖版本除非 spec 要求——依赖变更 = R2）
- 组件复用优先于新写：先 grep 现有组件库
- 样式遵循现有设计 token/规范（一致性 scorecard 项）
- 构建验证：`build` 通过 + 目标页面可加载（scorecard 附命令输出）
- 产物 = 文件 diff（patch/ref），不贴大段代码进消息

## 验收要点（critic 视角）

- 功能：交互路径逐条可复现（命令/操作步骤）
- 边界：空态/错误态/加载态三态检查
- 回归：改动面 grep（谁引用了改动的组件/工具函数）
- 性能面：无新增明显阻塞（bundle 大小对比，如有基线）
