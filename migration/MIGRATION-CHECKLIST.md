# 迁移人工确认清单（B-7）

> 骨架生成器产出 `team.json` 后，**逐项打勾**才允许进阶段 2（并行双写）。任何一项未确认 = 停。

## A. 角色与名册

- [ ] `roles[]` 覆盖存量团队**全部**角色（对照阶段 1 差异报告，无未知角色）
- [ ] 每个 `kind` 正确（coordinator / leader / worker / critic）——生成器按文件名推断，**必须人工复核**
- [ ] `roster[]` 的人类条目替换为真实身份（`TODO-human-a` 已清除），`weight` 经本人确认
- [ ] `mode` 与团队实际形态一致（single_user = 一个人类；multi_user = 多人类）

## B. 章程与边界

- [ ] `charter.mission` 从存量团队章程**转录**（非改写、非猜测）
- [ ] `scope` / `non_goals` 与迁移前一致；有变化必须在切换记录里写明

## C. 协议参数

- [ ] `protocol.fuse_threshold` / `fuse_window_seconds` 与运维要求一致（默认 2 / 30s）
- [ ] 各角色 `budget`（行预算）按新协议基线核定（coordinator≤500 / leader≤250 / worker≤150 / critic≤150）
- [ ] `decision_class` 标注（R1–R6）经团队人类确认——**分类错 = B-10 saga 补偿成本**

## D. 编译与对比（阶段 1 出口）

- [ ] `millforge validate team.json` 通过
- [ ] `millforge compile team.json --out shadow/` 成功，产物行数在预算内
- [ ] 与存量 SOUL 的差异报告已人工过目（新增片段 = 协议增量，非行为漂移）

## E. 阶段 2 门（并行双写）

- [ ] decision_log 双写样例 ≥ 10 条，人工核对一致
- [ ] contract_snapshot 指纹与契约版本一致（`contract-revalidate.sh` 退出 0）
- [ ] critic 隔离已生效（审核由 native 会话执行，不走 spawn）

## F. 阶段 3 门（切换）

- [ ] 回滚预案已写（旧流程如何恢复、多长时间）
- [ ] 切换窗口与运维确认（避开生产高峰）
- [ ] 切换后首轮 decision_log 无 schema 违规（`validate-decision-log.sh` 退出 0）

---
**未通过任一项 = BLOCKED**，记录原因后再继续；本清单随团队归档，不进 `golden-tests/`。
