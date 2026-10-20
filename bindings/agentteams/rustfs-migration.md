# RustFS 迁移（MinIO → RustFS，S3 语义核验）

> Provenance：生产化+开源就绪审查（第六轮，2026-10-18）定案；采纳状态 = 采纳。本文件是 `bindings/agentteams/` 的对象存储迁移规格。本层允许点名 MinIO/RustFS（通用词纪律见 `README.md` 头注）。

## 1. CAP-STORE T1–T3 在纯 S3 语义下的可实现性

| 不变式 | S3 语义下的实现 | 可行性 |
|---|---|---|
| **T1 内容寻址** | 客户端计算 SHA-256（S3 的 ETag 不保证是内容哈希，多段上传的 ETag 是分片哈希的哈希，不能直接作为内容指纹）。客户端算哈希作为 `fingerprint`，S3 的 ETag 作为传输校验的辅助。 | ✅ 可实现；**关键**：fingerprint 由客户端算，不能依赖 ETag |
| **T2 写入可确认** | S3 提供**强 read-after-write 一致性**（PUT 成功后 GET 立即可见）；2024 年后支持 **conditional writes**（If-None-Match: * 创建，If-Match: ETag 覆盖），失败返回 412 PreconditionFailed。write 返回 `{ref, fingerprint}` 前：① PUT 对象；② PUT 成功后用 conditional GET/HEAD 验证存在和 ETag；③ 返回。 | ✅ 可实现 |
| **T3 append 可选** | S3 没有原生 append。同 key 追加在并发下不安全（conditional PUT 串行化，热 key 吞吐上限低）。**替代方案**：append-only 用"新对象 + 旧对象链"模拟——每条记录写一个新对象（`decisions/<task>/<seq>.json`），append 返回链尾 ref；读取时按 seq 排序。 | ✅ 可实现（链式模拟，不用同 key append） |

**T3 核心表述（已进 CAP-STORE）**：

```
“append(path, entry) -> new_ref。实现可以是：① 同对象 JSONL 追加
（若运行时支持安全并发）；② 新对象链式追加（entry_ref = path +
seq，append 返回链尾）；③ 其他等价语义。核心只要求
read(ref) 能按 append 顺序返回所有条目，不要求物理同对象。”
```

## 2. CAS 定位（CAP-STATE vs CAP-STORE）

- S3 的 conditional writes（If-None-Match / If-Match）是**对象级**的，不是键值级的 CAS。
- **CAP-STATE 不要用对象存储的 conditional PUT 来模拟 CAS**，除非能接受同 key 并发上限。需要"原子更新多个字段"的状态由 CAP-STATE 的实现负责（本地文件锁或专用 KV），对象存储只做 CAP-STORE。

## 3. T2 执行细则（同步层确认）

```
“若写入路径经过同步层（工作区 ↔ 对象存储的异步同步），
write 返回前必须确认同步层已将该对象持久化到对象存储
（同步层的 uploaded/committed 回执）。未确认的写入不得
返回 {ref, fingerprint}；调用方不得消费未确认的 ref。
同步层的实现（push_loop、mirror、rsync 等）是绑定参数，
但‘确认后才返回’是 T2 的强制语义。”
```

归属：T2 语义进 CAP-STORE；具体确认机制（push 日志轮询、回执文件）是绑定参数（见 `deployment-guide.md` §3 写后协议）。

## 4. storage_adapter 枚举 + 8 脚本审计

**枚举**：`"local" | "s3"`（s3 覆盖 MinIO / RustFS / 任意 S3 兼容存储）。核心只要求 s3 和 local；其他（gcs/azure-blob）是绑定扩展。

**8 脚本硬编码检查（结论：核心脚本不得调用任何对象存储 CLI）**：

| 脚本 | 可能的硬编码 | 处置 |
|---|---|---|
| `validate-decision-log.sh` | 无（纯 JSON 校验） | 不需要 |
| `detect-conflict.py` | 无（纯 Python） | 不需要 |
| `contract-revalidate.sh` | 可能调用 `mc cat` 读兼容性报告 | 改为从 stdin 或 `--report-path` 读本地文件；对象存储读取由调用方（CAP-STORE adapter）负责 |
| `attention-stall.sh` | 无（读 CAP-STATE） | 不需要 |
| `verification-mismatch-window.sh` | 无 | 不需要 |
| `saga-compensate.py` | 可能调用 `mc` 写补偿指令 | 改为写本地路径，由 CAP-STORE adapter 上传 |
| `consistency-check.py` | 无 | 不需要 |
| `aggregate-vote.sh` | 无 | 不需要 |

脚本只处理本地文件 / stdin / stdout；所有对象存储 I/O 由 CAP-STORE adapter 负责。若现有脚本有 `mc` 调用，必须抽象掉。

## 5. RustFS 迁移检查清单

```
1. 确认 RustFS 版本支持 S3 conditional writes（If-None-Match/If-Match）
   和 read-after-write 强一致性；用 32 并发 If-None-Match: * PUT
   验证 exactly-one-winner。
2. 确认 filesync 同步层（容器↔RustFS）的 uploaded 回执机制与 MinIO
   时期一致；如果不一致，更新 CAP-STORE T2 的绑定参数。
3. 验证 mc mirror / rclone 迁移后对象指纹一致（客户端 SHA-256
   对比）；bucket 策略、IAM、生命周期规则逐条检查。
4. 检查 8 个核心脚本中是否有 `mc` 调用；有则替换为本地文件读写 +
   CAP-STORE adapter。
5. 用 golden test 跑一遍 Full 档跨团队任务，确认 decision_log /
   contract / handoff 在 RustFS 上行为与 MinIO 一致。（不得删）
```

**实测注记**：RustFS 的 S3 兼容性矩阵覆盖 object put/get/delete/copy/head 与校验和，但 conditional writes 矩阵中未明确列出 If-None-Match——**必须实测**（清单第 1 条），不得以兼容矩阵代替。
