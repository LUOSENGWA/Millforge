# 域片段：桌面应用（desktop）

> T2 域片段 · source: reference | 适用: worker | spawn 域: desktop

## 上下文输入（spawn 从文件读）

- 项目结构 + 目标模块（ref）+ 目标平台矩阵（OS/架构）
- 现有构建配置（Makefile/cmake/CMakeLists = contract）

## 执行约束

- 跨平台构建：目标平台矩阵全部可构建（scorecard 逐项）
- 平台 API 差异显式处理（条件编译/适配层），不假设单一平台
- 打包产物指纹（校验和）进 scorecard
- 本地验证 = 目标 OS 可执行；交叉平台 = 标注"待该平台环境验证"

## 验收要点（critic 视角）

- 构建矩阵逐项可复现；产物可启动（目标平台）
- 依赖锁定（版本文件指纹）
- 回归：现有测试全绿 + 改动面检查
