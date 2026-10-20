# skill 片段（CAP-SPAWN / CAP-EXEC 绑定实现）

> Provenance：参考绑定正文定案（2026-10-20）。本文件是 `bindings/coding-cli/` 的 skill 面规格；映射见 `mapping-table.md`。
> 定位：本绑定是**执行后端**（one-shot coding CLI），不是协议 agent——skill 面 = spawn 面（含 X1 非合规声明）+ 验收证据链 + 审批档位。

## 1. 脚本面（CAP-EXEC）

- 本 CLI 不是脚本的直接执行者：`core/scripts/` 9 脚本由**父执行体**调用（CAP-EXEC 裁决 item 3：无对象存储/群聊的运行时脚本照常运行——输入输出路径由调用方按 CAP-STORE ref 解析，本地文件系统是合法 CAP-STORE 实现）。
- 退出码语义：0=成功，55=超时（bounded_failure），其他=失败（Y2）。
- 8 核心脚本 I/O 纪律：只处理本地文件 / stdin / stdout，**不得调用任何对象存储 CLI**。

## 2. spawn 面（CAP-SPAWN——X1 非合规声明）

- **X1（上下文隔离，硬门）不满足**：运行时缺少 fork=False 等价的会话隔离原语——工作区级记忆文件（CLAUDE.md）自动注入 + 会话持久化/恢复（`--resume`）均构成不经 context_refs 的上下文继承路径；one-shot 进程边界依赖调用方纪律（始终 one-shot + 干净工作区），不是运行时强制保证。契约要求 X1 由运行时强制 → 硬门不满足（细节与判定口径见 `mapping-table.md` §1.1）。
- 后果：本绑定 = **7/8**（组合视角），标注为 reference 而非 compliant。
- 调用路径（调用方纪律下 X1 合规）：one-shot（10 flags）+ `--max-wall-time`；X2 ✅ 结构化返回；X3 ✅ 进程独立；X4 ✅ **运行时强制**时限，超时 `exit 55` = bounded_failure（三个参考绑定中唯一由运行时原生强制的 X4；agentteams 绑定侧仍是尽力）。

## 3. 验收/审核链片段（SIG-ARTIFACT 证据链）

```
CLI exit 0
  → 读 coding-runs 证据链（GET /api/v1/coding-runs：产物清单 + 校验和）
  → 指纹验证（CAP-STORE T2：校验和 = artifact ref 指纹源）
  → 三层审核链（父执行体执行，顺序不可换）:
      第 1 层: validate-decision-log.sh（schema 校验）
      第 2 层: detect-conflict.py（纯字段比对）
      第 3 层: critic 检查指纹（权威 = 父 CAP-STORE artifact）
  → 验收；验收证据链写入父 CAP-STATE
exit 55: bounded_failure（记 decision_log，≤3 次升级）
其他 exit: 失败（同上）
```

- 校验不放 CLI：CLI 是 LLM 执行体，自我校验无效——校验由**父执行体验收前**执行。
- 校验不放单次返回时刻：指纹比对源 = coding-runs 证据链（T2：确认后才消费）。

## 4. 审批片段（CAP-ATTN，人终审）

- 两层互补：平台 `--approval-mode` 阶梯（人终审档位）× coder 侧 ACP `request_permission`（逐操作授权）。
- 千锻闭环 = **auto 档 + request_permission**。
- 审批档位纪律（critical_delivery 硬约束）：
  - simple 档：默认 `--yolo`（执行层审批旁路）可接受
  - critical_delivery（R1 类）：**禁止 yolo**——必须 `auto 档 + request_permission` 或人锁
  - 人终审记录 = SIG-DECISION 事件源（父执行体写 CAP-STATE）

## 5. cron / loop

not applicable（本绑定无 CAP-TIMER；调度由父执行体负责）。
