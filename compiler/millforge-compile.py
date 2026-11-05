#!/usr/bin/env python3
"""millforge compiler — 6 段管线 CLI 入口（确定性，同输入同输出）

用法:
  millforge compile <team.json> [--out <dir>] [--budget-override <role>=<lines>] [--lang zh|en]
  millforge validate <team.json>          # 只跑到 Validate 段
  millforge list-fragments                # 列出 INDEX.yaml 注册的全部片段

双语: team.json `lang: "zh"|"en"`（默认 zh），CLI `--lang` 覆盖。
lang=en → 全部模板取 .en.md 孪生文件（缺失 = Compile fail，双语完整性硬门）；
产出（.soul.md + fragments/ + spawn-specs/）整树为英文。

唯一实现 = compiler/pipeline/（六段纯函数）。本文件是薄 CLI 入口：
参数解析、墙钟注入（compiled_at）、落盘、退出码——不保留任何管线逻辑。

6 段（任一段 fail = 整体 fail，绝不截断产出）:
  ① Parse    — JSON 解码 + 顶层结构预检                                   exit 2
  ② Validate — JSON Schema（team.schema.json）+ 交叉一致性（roster/mode）+ lang  exit 2
  ③ Budget   — 行预算解析（override > role.budget > 种类默认）+ 上下文档位      exit 4
  ④ Compile  — skeleton 选择 + 触发指针表 + 片段部署清单（= 旧 Assemble）     exit 3
  ⑤ Render   — 占位符解析（零残留门在 ⑥ 按固定序执行）                       exit 5
  ⑥ Verify   — 行硬门 → 档位 token 门 → 零残留 → scrub 词表 → 指针完整性
               + provenance 头 + 指标（= 旧 SelfCheck + Provenance）        exit 4/5/6

旧段名映射（2026-11-05 前的命名）: Validate→②, Assemble→④, Budget→③,
Render→⑤, SelfCheck/Provenance→⑥。退出码对外兼容:
Validate=2 / Compile(=旧 Assemble)=3 / Budget=4 / Render=5 / Verify(=旧 SelfCheck)=6 / usage=64。

三层装载架构（§12-REDLINES，U 形注意力 + 行天花板）:
  第 0 层 常驻（身份文件，受行硬门）: skeleton（身份+铁律+核心循环）+ 协议触发指针表（一行一个）+ 角色参数
  第 1 层 按需（运行时触发装载）: 协议片段全文 fragments/protocol-*.md + 行业片段 fragments/industry-*.md
  第 2 层 参考/注入: 域片段 spawn-specs/*.md（派发 spawn 时注入 task spec，不占身份文件）
  触发机制 = 绑定层实现（能力触发/read_file）；核心只要求触发描述常驻 + 片段文件部署。
  域片段 ≠ 身份文件内容（header 已声明"派发时注入 spawn 的 task spec"）——不编译进 .soul.md。

确定性: 无 LLM；片段装载顺序固定（INDEX 声明序）；时间戳只进 provenance 头（不进正文）。
"""
import json
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from pipeline import (  # noqa: E402
    BUDGETS,
    EXIT_BUDGET,
    EXIT_COMPILE,
    EXIT_OK,
    EXIT_RENDER,
    EXIT_USAGE,
    EXIT_VALIDATE,
    EXIT_VERIFY,
    PipelineError,
    SCRUB_WORDS,
    STAGES,
    TIER_CAPS,
    estimate_tokens,
    load_index,
    load_team_schema,
    parse,
    run_pipeline,
    tier_exceeded,
    validate,
)
from pipeline import default_root  # noqa: E402

# 旧退出码别名（历史名 → 新段名，值不变）
EXIT_ASSEMBLE = EXIT_COMPILE
EXIT_SELFCHECK = EXIT_VERIFY


def _now_iso():
    """墙钟（ISO8601 UTC 秒级）——只注入 provenance 头，不参与正文。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fail(stage, code, msg, extra=None):
    out = {"ok": False, "stage": stage, "error": msg}
    if extra:
        out.update(extra)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(code)


def compile_team(doc, outdir, overrides=None, lang=None):
    """六段管线 + 落盘（唯一写盘点）。成功：打印报告并返回 EXIT_OK；
    任一段 fail：打印错误并 sys.exit（该段退出码），零产出（绝不截断）。"""
    try:
        result = run_pipeline(
            json.dumps(doc, ensure_ascii=False, sort_keys=True),
            default_root(),
            outdir=outdir,
            overrides=overrides,
            cli_lang=lang,
            compiled_at=_now_iso(),
        )
    except PipelineError as e:
        fail(e.stage, e.code, e.error, e.extra)
    os.makedirs(outdir, exist_ok=True)
    for name, text in result["artifacts"].items():
        with open(os.path.join(outdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    for rel, text in result["fragment_artifacts"].items():
        target = os.path.join(outdir, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(text)
    report = {k: v for k, v in result.items() if k not in ("artifacts", "fragment_artifacts")}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return EXIT_OK


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(EXIT_USAGE if not args else EXIT_OK)
    cmd = args[0]
    if cmd == "list-fragments":
        idx = load_index(default_root())
        print(json.dumps({"skeletons": list(idx["skeletons"]), "industry": list(idx["industry"]),
                          "domains": list(idx["domains"]), "protocol": list(idx["protocol"]),
                          "teams": list(idx["teams"])}, ensure_ascii=False, indent=1))
        sys.exit(EXIT_OK)
    if cmd not in ("compile", "validate"):
        fail("usage", EXIT_USAGE, f"unknown command: {cmd}（compile|validate|list-fragments）")
    if len(args) < 2:
        fail("usage", EXIT_USAGE, "missing <team.json>")
    with open(args[1], encoding="utf-8") as f:
        text = f.read()
    try:
        doc = parse(text)
        if cmd == "validate":
            validate(doc, schema=load_team_schema(default_root()), index=load_index(default_root()))
            print(json.dumps({"ok": True, "team": doc["name"], "validations": "schema+xcheck passed"}, ensure_ascii=False))
            sys.exit(EXIT_OK)
    except PipelineError as e:
        fail(e.stage, e.code, e.error, e.extra)
    outdir = None
    overrides = {}
    cli_lang = None
    i = 2
    while i < len(args):
        if args[i] == "--out":
            outdir = args[i + 1]; i += 2
        elif args[i] == "--budget-override":
            k, v = args[i + 1].split("=", 1); overrides[k] = int(v); i += 2
        elif args[i] == "--lang":
            cli_lang = args[i + 1]; i += 2
        else:
            i += 1
    outdir = outdir or os.path.join(os.getcwd(), "out", doc["name"])
    sys.exit(compile_team(doc, outdir, overrides, cli_lang))


if __name__ == "__main__":
    main()
