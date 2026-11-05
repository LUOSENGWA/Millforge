#!/usr/bin/env python3
"""Sync beta module artifacts from the fork's GitHub releases into `releases/`.

Reads only the public releases API (no token), copies the release assets into
`releases/<module>/<version>/`, computes sha256 and updates `releases/beta/channels.json`.
Never pushes. See `releases/README.md` for the layout and contract.

Usage:
    tools/sync-beta.sh                    # the five most recent beta releases
    tools/sync-beta.sh teamharness-v0.3.0-beta.2 ...
    tools/sync-beta.sh --dry-run          # list only, no writes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FORK_DEFAULT = "LUOSENGWA/HiClaw"
TAG_RE = re.compile(r"^(teamharness|agentteams-matrix|qwen-code-bridge|looprunner)-v(\d+\.\d+\.\d+-beta\.\d+)$")
MODULE_KINDS = {
    "teamharness": "plugin",
    "agentteams-matrix": "bundle",
    "qwen-code-bridge": "plugin",
    "looprunner": "runner",
}
# QwenPaw plugin ids that differ from the module id (adapter packages).
MODULE_PLUGIN_IDS = {
    "agentteams-matrix": "agentteams-matrix-channel",
}
META_FILES = {"sha256sums.txt", "release-manifest.json"}
KEEP_BETAS = 5
USER_AGENT = "millforge-sync/1"


def http_json(url: str) -> dict:
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url: str, dest: Path) -> str:
    digest = hashlib.sha256()
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=120
    ) as response, tmp.open("wb") as handle:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            digest.update(chunk)
            handle.write(chunk)
    tmp.replace(dest)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version_key(version: str) -> tuple:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)-beta\.(\d+)$", version)
    if not match:
        return (0, 0, 0, 0)
    return tuple(int(part) for part in match.groups())


def list_beta_releases(fork: str, limit: int = 5) -> list[dict]:
    releases = http_json(f"https://api.github.com/repos/{fork}/releases?per_page=100")
    selected = [
        release
        for release in releases
        if release.get("prerelease") and TAG_RE.match(release.get("tag_name", ""))
    ]
    selected.sort(key=lambda release: release.get("published_at") or "", reverse=True)
    return selected[:limit]


def process_release(repo_root: Path, fork: str, release: dict, dry_run: bool) -> tuple[str, str, bool]:
    module, version = TAG_RE.match(release["tag_name"]).groups()
    target = repo_root / "releases" / module / version
    if dry_run:
        return module, version, False

    target.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict] = []
    downloaded = False
    for asset in release.get("assets", []):
        name = asset["name"]
        dest = target / name
        tmp = dest.with_suffix(dest.suffix + ".part")
        try:
            download(asset["browser_download_url"], tmp)
        except Exception as error:  # noqa: BLE001 - a single bad asset must not abort the sync
            print(f"  warn: cannot download {name}: {error}")
            tmp.unlink(missing_ok=True)
            if dest.exists() and name not in META_FILES:
                artifacts.append({"name": name, "sha256": sha256_file(dest)})
            continue
        fresh = sha256_file(tmp)
        if dest.exists() and sha256_file(dest) == fresh:
            tmp.unlink(missing_ok=True)
        else:
            tmp.replace(dest)
            downloaded = True
        if name not in META_FILES:
            artifacts.append({"name": name, "sha256": fresh})

    requires: dict = {}
    commit = ""
    manifest_path = target / "release-manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            requires = manifest.get("requires") or {}
            commit = manifest.get("commit") or ""
        except json.JSONDecodeError:
            print(f"  warn: invalid release-manifest.json for {release['tag_name']}")

    channel_path = repo_root / "releases" / "beta" / "channels.json"
    before = channel_path.read_text(encoding="utf-8")
    channel = json.loads(before)
    module_entry = channel["modules"].setdefault(module, {"latest": version, "versions": {}})
    if "kind" not in module_entry:
        module_entry["kind"] = MODULE_KINDS[module]
    if "pluginId" not in module_entry and module in MODULE_PLUGIN_IDS:
        module_entry["pluginId"] = MODULE_PLUGIN_IDS[module]
    module_entry["versions"][version] = {
        "artifacts": sorted(artifacts, key=lambda item: item["name"]),
        "requires": requires,
        "commit": commit,
        "published_at": release.get("published_at"),
        "deprecated": False,
    }
    versions = sorted(module_entry["versions"], key=version_key, reverse=True)
    module_entry["latest"] = versions[0]
    for stale in versions[KEEP_BETAS:]:
        module_entry["versions"][stale]["deprecated"] = True
    channel["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    channel_path.write_text(
        json.dumps(channel, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return module, version, downloaded or channel_path.read_text(encoding="utf-8") != before


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--fork", default=FORK_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("tags", nargs="*")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    if args.tags:
        releases = []
        for tag in args.tags:
            if not TAG_RE.match(tag):
                raise SystemExit(f"not a beta module tag: {tag}")
            releases.append(http_json(f"https://api.github.com/repos/{args.fork}/releases/tags/{tag}"))
    else:
        releases = list_beta_releases(args.fork)

    if not releases:
        print("no beta releases to sync (exit 0)")
        return 0

    print(f"syncing {len(releases)} release(s) from {args.fork}")
    for release in releases:
        module, version, changed = process_release(repo_root, args.fork, release, args.dry_run)
        state = "dry-run" if args.dry_run else ("updated" if changed else "unchanged")
        print(f"  {module} {version}: {state}")

    if not args.dry_run:
        print("\nnext: git add releases && git commit -m 'chore(releases): sync beta artifacts'  (then push to both remotes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
