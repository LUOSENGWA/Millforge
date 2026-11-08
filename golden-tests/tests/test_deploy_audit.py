#!/usr/bin/env python3
"""End-to-end tests for the append-only deployment ledger (tools/deploy.py).

Exercises the record / verify / list subcommands against a throwaway
repository root (a temp dir), so the real deployments.jsonl is untouched.
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "tools" / "deploy.py"
FIELD_ORDER = ["ts", "action", "module", "version", "artifact", "sha256", "sha256_source", "target", "operator", "note"]

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}: {detail}")


def run(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DEPLOY), "--repo-root", str(repo), *args],
        capture_output=True,
        text=True,
    )


def ledger_lines(repo: pathlib.Path) -> list[str]:
    path = repo / "deployments.jsonl"
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


with tempfile.TemporaryDirectory() as tmp:
    repo = pathlib.Path(tmp)
    artifact = repo / "art" / "x.bin"
    artifact.parent.mkdir(parents=True)
    original = b"millforge deploy fixture\n"
    artifact.write_bytes(original)
    want = hashlib.sha256(original).hexdigest()

    # 1) record with an existing artifact: sha computed, fixed field order, ts format
    r = run(repo, "record", "--module", "teamharness", "--version", "0.3.0",
            "--target", "build-host:/opt/agentteams", "--operator", "alice",
            "--artifact", "art/x.bin")
    check("record_exit0", r.returncode == 0, f"exit {r.returncode} stderr={r.stderr!r}")
    lines = ledger_lines(repo)
    check("one_line", len(lines) == 1, f"{len(lines)} lines")
    check("newline_terminated", bool(lines) and lines[0].endswith("\n"), repr(lines[:1]))
    rec = json.loads(lines[0]) if lines else {}
    check("field_order", list(rec) == FIELD_ORDER, str(list(rec)))
    check("compact_line", bool(lines) and lines[0].rstrip("\n") == json.dumps(rec, ensure_ascii=False, separators=(",", ":")), lines[0])
    check("sha_computed", rec.get("sha256") == want and rec.get("sha256_source") == "computed", str(rec.get("sha256")))
    check("artifact_field", rec.get("artifact") == "art/x.bin", str(rec.get("artifact")))
    check("action_default_deploy", rec.get("action") == "deploy", str(rec.get("action")))
    check("ts_utc_seconds", re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", str(rec.get("ts", ""))) is not None, str(rec.get("ts")))
    first_line = lines[0] if lines else ""

    # 2) second record: append-only — first line byte-identical
    r = run(repo, "record", "--module", "taskforge", "--version", "0.1.0",
            "--action", "pack", "--target", "deploy-host:/opt", "--operator", "alice",
            "--sha256", want, "--label", "releases/taskforge/0.1.0/pack.tar.gz")
    check("record2_exit0", r.returncode == 0, f"exit {r.returncode} stderr={r.stderr!r}")
    lines = ledger_lines(repo)
    check("two_lines", len(lines) == 2, f"{len(lines)} lines")
    check("first_line_unchanged", bool(lines) and lines[0] == first_line, "append-only violated")
    rec2 = json.loads(lines[1]) if len(lines) > 1 else {}
    check("sha_provided", rec2.get("sha256_source") == "provided" and rec2.get("artifact") == "releases/taskforge/0.1.0/pack.tar.gz" and rec2.get("sha256") == want, str(rec2))
    check("action_pack", rec2.get("action") == "pack", str(rec2.get("action")))

    # 3) missing artifact: non-zero exit, message, no new line
    before = "".join(ledger_lines(repo))
    r = run(repo, "record", "--module", "teamharness", "--version", "0.3.1",
            "--target", "build-host:/opt", "--operator", "alice",
            "--artifact", "nope/missing.tar.gz")
    check("missing_artifact_nonzero", r.returncode != 0, f"exit {r.returncode}")
    check("missing_artifact_msg", "artifact not found: nope/missing.tar.gz" in (r.stdout + r.stderr), r.stdout + r.stderr)
    check("no_line_appended", "".join(ledger_lines(repo)) == before, "file changed on failed record")

    # 4) invalid action / invalid sha256: non-zero exit, no write
    before = "".join(ledger_lines(repo))
    r = run(repo, "record", "--module", "teamharness", "--version", "0.3.1",
            "--target", "build-host:/opt", "--operator", "alice",
            "--action", "bogus", "--artifact", "art/x.bin")
    check("bad_action_nonzero", r.returncode != 0, f"exit {r.returncode}")
    r = run(repo, "record", "--module", "teamharness", "--version", "0.3.1",
            "--target", "build-host:/opt", "--operator", "alice",
            "--sha256", "not-a-sha", "--label", "x")
    check("bad_sha_nonzero", r.returncode != 0, f"exit {r.returncode}")
    r = run(repo, "record", "--module", "teamharness", "--version", "0.3.1",
            "--target", "build-host:/opt", "--operator", "alice",
            "--sha256", "g" * 64, "--label", "x")
    check("sha_wrong_chars_nonzero", r.returncode != 0, f"exit {r.returncode}")
    r = run(repo, "record", "--module", "teamharness", "--version", "0.3.1",
            "--target", "build-host:/opt", "--operator", "alice",
            "--sha256", want)
    check("sha_without_label_nonzero", r.returncode != 0, f"exit {r.returncode}")
    check("no_write_on_invalid", "".join(ledger_lines(repo)) == before, "file changed on invalid record")

    # 5) verify: last matching record agrees -> exit 0; corrupted artifact -> exit 1 + mismatch
    r = run(repo, "verify", "--module", "teamharness", "--artifact", "art/x.bin")
    check("verify_ok", r.returncode == 0, f"exit {r.returncode} out={r.stdout!r} err={r.stderr!r}")
    artifact.write_bytes(original[:-1] + b"X")  # one byte changed
    r = run(repo, "verify", "--module", "teamharness", "--artifact", "art/x.bin")
    check("verify_mismatch_code", r.returncode == 1, f"exit {r.returncode}")
    check("verify_mismatch_msg", "mismatch: recorded=" in r.stdout and "current=" in r.stdout, r.stdout)
    r = run(repo, "verify", "--module", "teamharness", "--sha256", want)
    check("verify_sha_form", r.returncode == 0, f"exit {r.returncode} out={r.stdout!r}")

    # 6) verify with no record: exit 2 + "no record"
    r = run(repo, "verify", "--module", "never-deployed")
    check("no_record_code", r.returncode == 2, f"exit {r.returncode}")
    check("no_record_msg", "no record" in (r.stdout + r.stderr), r.stdout + r.stderr)

    # 7) list: chronological raw lines, --module filter, --limit keeps the last N
    r = run(repo, "list")
    check("list_all", r.returncode == 0 and r.stdout.splitlines() == [ln.rstrip("\n") for ln in ledger_lines(repo)], r.stdout)
    r = run(repo, "list", "--module", "teamharness")
    check("list_module", r.returncode == 0 and r.stdout.splitlines() == [first_line.rstrip("\n")], r.stdout)
    r = run(repo, "list", "--limit", "1")
    last = ledger_lines(repo)[-1].rstrip("\n")
    check("list_limit", r.returncode == 0 and r.stdout.splitlines() == [last], r.stdout)

# 8) list on an empty repository root: exit 0, no output
with tempfile.TemporaryDirectory() as tmp:
    r = run(pathlib.Path(tmp), "list")
    check("list_empty_ok", r.returncode == 0 and r.stdout == "", f"exit {r.returncode} out={r.stdout!r}")

if failures:
    print(json.dumps({"ok": False, "failures": failures}, ensure_ascii=False, indent=1))
    sys.exit(1)
print(json.dumps({"ok": True, "tests": 32}, ensure_ascii=False))
