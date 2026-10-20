# 域片段：嵌入式 Linux（embedded-linux）

> T2 域片段 · source: reference | 适用: worker | spawn 域: embedded-linux

## 上下文输入（spawn 从文件读）

- 目标板级说明（SoC/内存/存储/启动链，spec 结构化字段）
- 现有构建系统（Buildroot/Yocto/交叉编译链配置，ref = contract）
- 目标系统当前镜像/根文件系统指纹（baseline）

## 执行约束

- 交叉编译链版本锁定（gcc/glibc/binutils 版本进 spec；漂移 = 返工）
- 根文件系统改动：空间预算显式（嵌入式存储受限——构建后 `du` 证据）
- 启动链改动（init/服务/设备树）= R1（板级破坏性风险，人锁 + 回滚镜像保留）
- 服务/进程变更附 systemd/init 配置 + 启动验证日志
- 在环标注：无开发板 = 构建层验收 + 明确"待板级验证"

## 验收要点（critic 视角）

- 镜像可构建（工具链一致复现）+ 大小在预算内
- 配置一致性（设备树/服务配置 vs spec 逐项）
- 回滚路径：旧镜像指纹保留可恢复（R1 面）
- 板级验证缺口显式声明（不假装）
