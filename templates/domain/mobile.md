# 域片段：移动端（mobile）

> T2 域片段 · source: production | 适用: worker | spawn 域: mobile-app（Android/iOS）

## 上下文输入（spawn 从文件读）

- 项目结构 + 目标模块代码路径（ref）
- 目标平台/SDK 版本矩阵（spec 结构化字段）
- UI 设计稿（如有）

## 执行约束

- 平台版本锁定：minSdk/targetSDK/部署目标 = spec 字段（漂移 = 返工）
- 真机/模拟器验证标注：无法在环 = "功能验证待具备完整环境后执行"，不假装通过
- 权限声明变更 = contract 面（权限 = 用户可见契约）
- 构建验证：assemble 通过 + 目标 Activity/页面可启动（scorecard 附日志证据）
- 产物 = patch/ref + 关键日志（文件引用）

## 验收要点（critic 视角）

- 构建 + 静态检查 + 可在环部分的操作路径验证
- 边界：权限拒绝/设备低配/网络断连三态
- 回归：改动面引用检查（跨模块调用）
