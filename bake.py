#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

OWNER = "katabame"
BASE_DIR = Path(__file__).resolve().parent
PLUGINS_FILE = BASE_DIR / "materials.txt"
OUTPUT = BASE_DIR / "pancakes.json"


def load_plugins():
    if not PLUGINS_FILE.exists():
        sys.exit(f"{PLUGINS_FILE.name} が見つかりません")

    plugins = []
    for line in PLUGINS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line and line not in plugins:
            plugins.append(line)

    if not plugins:
        sys.exit(f"{PLUGINS_FILE.name} にプラグインが1件もありません")
    return plugins


def http_get(url):
    headers = {"User-Agent": "https://github.com/katabame/Popoto/bake.py"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def fetch_releases(name):
    releases, page = [], 1
    while True:
        url = (f"https://api.github.com/repos/{OWNER}/{name}/releases"
               f"?per_page=100&page={page}")
        data = http_get(url)
        if not data:
            return releases
        releases.extend(data)
        page += 1


def to_unix(iso):
    return str(int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()))


def build_entry(name):
    base = f"https://github.com/{OWNER}/{name}/releases/latest/download"
    entry = http_get(f"{base}/{name}.json")

    entry["DownloadLinkInstall"] = f"{base}/install.zip"
    entry["DownloadLinkUpdate"] = f"{base}/update.zip"

    releases = fetch_releases(name)
    stable = [r for r in releases if not r["draft"] and not r["prerelease"]]
    if not stable:
        raise RuntimeError(f"{name}: 公開済みのReleaseがありません")

    entry["LastUpdate"] = to_unix(stable[0]["published_at"])

    entry["DownloadCount"] = sum(
        asset["download_count"]
        for r in releases
        for asset in r["assets"]
        if asset["name"] == "install.zip"
    )
    return entry


def main():
    master = []
    for name in load_plugins():
        try:
            master.append(build_entry(name))
            print(f"OK: {name}")
        except Exception as e:
            print(f"NG: {name}: {e}", file=sys.stderr)
            sys.exit(1)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
