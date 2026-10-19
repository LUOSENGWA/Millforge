# 部署模式（mode）

> v1.0 | 来源: NMProtocol §4（2026-09-03 定案）
> 结构不变量：multi_user ⟹ 用户隔离 ⟹ 跨团队不成立 ⟹ 集群级协调角色失去唯一核心价值（跨团队中转）⟹ 该角色不存在。
> 这不是运营开关，是系统形态的相变。

## 定义

| mode | 判定 | arbitrator | 跨团队扩展 |
|------|------|-----------|-----------|
| `single_user` | 整个集群服务**一个** human | 集群级协调角色存在（全功能） | **可用**（§07-HANDOFF） |
| `multi_user` | ≥2 个 human 使用 | **不存在集群级协调角色**；团队内仲裁 = leader，跨团队无（用户隔离） | **不可用** |

## 通信拓扑

**single_user**（经典三层）：

```
human ──channel──▶ arbitrator（集群级协调角色，全功能）
                      │ NMH（与 human 确认需求）
                      │ 路由/建 project/派发
                      ▼
                   leader ──▶ worker ──▶ spawn（子执行单元）
                   （每个 team 一个 leader；跨 team = §07-HANDOFF）
```

**multi_user**（每人自己的团队，双层）：

```
human A ──channel──▶ team A: leader A ──▶ worker A*
human B ──channel──▶ team B: leader B ──▶ worker B*
（team A 与 team B 之间：无通信路径，无共享项目，访问控制硬隔离）
```

## mode 对协议各部分的影响

| 协议部分 | single_user | multi_user |
|----------|------------|------------|
| NMH | human 可经 arbitrator 或直达 leader | human 直达**自己团队**的 leader |
| NMA | 🏳️ → arbitrator | 🏳️ → leader（团队内）；方向性僵持 → 建议当事人 human 直接沟通 |
| 任务生命周期 | 完全相同 | 完全相同 |
| 双通道汇报 | 跨团队任务走双通道；单团队 = 原始通道即底线 | 同单团队（无跨团队） |
| 跨团队 | §07-HANDOFF 启用 | **协议层面不存在**（非"禁用"，是不存在） |
| 团队创建 | arbitrator 或 human | human（经绑定层的管理界面） |
| 加权多数（§09） | 全决策类可用（受 C-3 限制） | 同（团队内）；accountable 持锁规则强化（B-8） |

**编译影响**：绑定层编译角色身份文件时，跨团队片段（handoff 写作权/汇总闭环/跨团队路由）仅 `single_user` 条件编译进集群级协调角色；`multi_user` 编译产物中不出现 §07-HANDOFF 的任何条文。
