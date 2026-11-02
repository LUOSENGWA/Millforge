#!/usr/bin/env python3
"""Deployment ledger: an append-only ``deployments.jsonl`` at the repository root.

Each line is one JSON object recording a deploy / rollback / pack action —
which module version, which artifact (with its sha256), on which target, by
whom, at what UTC instant — so that "which version was deployed or packed at
that time?" can be answered at any later moment.

The file is opened in append mode only: existing lines are never rewritten,
and a rollback is a new record (``--action rollback``), not an edit.

Zero dependencies (standard library only); never touches the network.

Usage (via tools/deploy.sh):
    deploy.sh record --module <m> --version <v> --target <host:dir> --operator <name>
                     (--artifact <relative path> | --sha256 <64hex> --label <note>)
                     [--action deploy|rollback|pack] [--note <text>]
    deploy.sh verify --module <m> [--artifact <relative path> | --sha256 <64hex>]
    deploy.sh list [--module <m>] [--limit N]

verify exit codes: 0 = the last matching record agrees with the current
value; 1 = mismatch (``mismatch: recorded=… current=…``); 2 = no record (or
the current value cannot be determined locally).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER_NAME = "deployments.jsonl"
ACTIONS = ("deploy", "rollback", "pack")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(repo_root: Path, name: str) -> Path:
    path = Path(name)
    return path if path.is_absolute() else repo_root / path


def read_ledger(ledger: Path) -> list[tuple[str, dict]]:
    """Return (raw_line, record) pairs in file order (chronological: append-only)."""
    if not ledger.is_file():
        return []
    pairs: list[tuple[str, dict]] = []
    for line in ledger.read_text(encoding="utf-8").splitlines(keepends=True):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            print(f"warn: skipping malformed ledger line: {stripped[:80]}", file=sys.stderr)
            continue
        if isinstance(record, dict):
            pairs.append((line, record))
    return pairs


def cmd_record(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    ledger = repo_root / LEDGER_NAME

    if args.artifact and args.sha256:
        print("error: give either --artifact or --sha256 --label, not both", file=sys.stderr)
        return 2
    if args.label and not args.sha256:
        print("error: --label is only valid together with --sha256", file=sys.stderr)
        return 2

    if args.artifact:
        path = resolve(repo_root, args.artifact)
        if not path.is_file():
            print(f"artifact not found: {args.artifact}", file=sys.stderr)
            return 2
        artifact, digest, source = args.artifact, sha256_file(path), "computed"
    elif args.sha256:
        if not SHA256_RE.match(args.sha256):
            print(f"invalid sha256: {args.sha256} (expected 64 hex chars)", file=sys.stderr)
            return 2
        if not args.label:
            print("error: --sha256 requires --label (used as the artifact field)", file=sys.stderr)
            return 2
        artifact, digest, source = args.label, args.sha256.lower(), "provided"
    else:
        print("error: give --artifact <relative path> or --sha256 <64hex> --label <note>", file=sys.stderr)
        return 2

    record = {
        "ts": utc_now(),
        "action": args.action,
        "module": args.module,
        "version": args.version,
        "artifact": artifact,
        "sha256": digest,
        "sha256_source": source,
        "target": args.target,
        "operator": args.operator,
        "note": args.note,
    }
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n"
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(line)
    sys.stdout.write(line)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root)
    ledger = repo_root / LEDGER_NAME

    candidates = [rec for _, rec in read_ledger(ledger) if rec.get("module") == args.module]
    if args.artifact:
        candidates = [rec for rec in candidates if rec.get("artifact") == args.artifact]
    if not candidates:
        print("no record")
        return 2
    last = candidates[-1]

    if args.sha256:
        if not SHA256_RE.match(args.sha256):
            print(f"invalid sha256: {args.sha256} (expected 64 hex chars)", file=sys.stderr)
            return 2
        current = args.sha256.lower()
    elif args.artifact:
        path = resolve(repo_root, args.artifact)
        if not path.is_file():
            print(f"artifact not found: {args.artifact}")
            return 2
        current = sha256_file(path)
    else:
        name = str(last.get("artifact", ""))
        path = resolve(repo_root, name)
        if not path.is_file():
            print(f"cannot verify: {name} not found locally")
            return 2
        current = sha256_file(path)

    recorded = str(last.get("sha256", ""))
    if recorded == current:
        print(f"ok: {args.module} sha256={current}")
        return 0
    print(f"mismatch: recorded={recorded} current={current}")
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    if args.limit is not None and args.limit < 0:
        print("error: --limit must be >= 0", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root)
    ledger = repo_root / LEDGER_NAME
    pairs = read_ledger(ledger)
    if args.module:
        pairs = [(raw, rec) for raw, rec in pairs if rec.get("module") == args.module]
    if args.limit is None:
        selected = pairs
    elif args.limit <= 0:
        selected = []
    else:
        selected = pairs[-args.limit:]
    for raw, _ in selected:
        sys.stdout.write(raw if raw.endswith("\n") else raw + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="deploy",
        description="Append-only deployment ledger (deployments.jsonl at the repository root)",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="repository root holding deployments.jsonl (default: the parent of tools/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_record = sub.add_parser("record", help="append one record to the ledger")
    p_record.add_argument("--module", required=True)
    p_record.add_argument("--version", required=True)
    p_record.add_argument("--target", required=True, help="deployment target, e.g. build-host:/opt/agentteams")
    p_record.add_argument("--operator", required=True)
    p_record.add_argument("--artifact", default=None, help="artifact path relative to the repository root")
    p_record.add_argument("--sha256", default=None, help="caller-provided 64-hex sha256 (mutually exclusive with --artifact)")
    p_record.add_argument("--label", default=None, help="artifact field when --sha256 is used instead of --artifact")
    p_record.add_argument("--action", choices=ACTIONS, default="deploy")
    p_record.add_argument("--note", default="")

    p_verify = sub.add_parser(
        "verify",
        help="compare the last matching record with the current value (exit 0 ok / 1 mismatch / 2 no record)",
    )
    p_verify.add_argument("--module", required=True)
    p_verify.add_argument("--artifact", default=None)
    p_verify.add_argument("--sha256", default=None)

    p_list = sub.add_parser("list", help="print ledger lines in chronological order (raw lines)")
    p_list.add_argument("--module", default=None)
    p_list.add_argument("--limit", type=int, default=None, help="keep only the last N lines")

    args = parser.parse_args()
    if args.repo_root is None:
        args.repo_root = str(Path(__file__).resolve().parents[1])

    if args.command == "record":
        return cmd_record(args)
    if args.command == "verify":
        return cmd_verify(args)
    return cmd_list(args)


if __name__ == "__main__":
    sys.exit(main())
