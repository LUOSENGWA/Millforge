## 权限墙熔断（精简装载版）

**症状识别**：消息静默消失 / 无法发言 / 无错误日志 → **access control allowlist 静默拦截**（不是 idle_timeout 不是权限墙崩溃）。诊断第一位：对比实际生效的访问控制配置（allow_from / group_allow_from 是否含发起人）。

**熔断规则**：
- **≥{{fuse_threshold}} 个 Worker 连续权限错误 → ≤{{fuse_window_seconds}}s 内切 DM 私聊通道重路由**，不继续撞墙
- 单 worker 权限错误 → 上报 leader（leader 检查该 worker 配置）
- 重路由后仍失败 → 升级 human（附配置对比证据）

**配套**：配置变更（allow_from/roster）后必须验证生效（发测试消息收得到才算），不得假设。
