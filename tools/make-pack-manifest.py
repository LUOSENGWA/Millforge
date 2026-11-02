#!/usr/bin/env python3
"""Build `dist/pack-manifest.json` + `dist/sha256sums.txt` for `make pack`.

The tarball itself is deterministic (sorted members, fixed mtime/owner, `gzip -n`);
the manifest is intentionally NOT part of the tarball so that its build timestamp
does not break reproducibility of the artifact.

Usage:
    python3 tools/make-pack-manifest.py --pack dist/millforge-pack-1.1.0.tar.gz \
        --version 1.1.0 --commit abc123def456
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_digests() -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted((REPO / "core" / "schemas").glob("*.schema.json")):
        result[path.name] = sha256_file(path)[:16]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True, help="path to the built tarball")
    parser.add_argument("--version", required=True, help="pack version (VERSION file)")
    parser.add_argument("--commit", default="", help="short commit SHA")
    args = parser.parse_args()

    pack = Path(args.pack)
    if not pack.is_file():
        raise SystemExit(f"pack not found: {pack}")

    with tarfile.open(pack, "r:gz") as archive:
        members = [m for m in archive.getmembers() if m.isfile()]

    manifest = {
        "schema": 1,
        "name": "millforge-pack",
        "version": args.version,
        "commit": args.commit,
        "files": len(members),
        "tarball": {
            "name": pack.name,
            "bytes": pack.stat().st_size,
            "sha256": sha256_file(pack),
        },
        "schemas": schema_digests(),
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    dist = pack.parent
    manifest_path = dist / "pack-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (dist / "sha256sums.txt").write_text(
        f"{manifest['tarball']['sha256']}  {pack.name}\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "manifest": str(manifest_path),
                      "sha256": manifest["tarball"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
