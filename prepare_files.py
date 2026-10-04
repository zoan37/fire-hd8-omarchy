#!/usr/bin/env python3
"""Prepare host-side giza research artifacts. Never connects to the tablet."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "prepared"
TAG = "linux-amazon-giza-3.18.19-r4"
STOCK_URL = (
    "https://fireos-tablet-src.s3.amazonaws.com/93olgKwMW8ecGINzUwwqQmLz43/"
    "update-kindle-49.6.2.6_user_626533320.bin"
)
# This expected digest is from the community firmware index, not an Amazon
# signature. The bytes are fetched directly from Amazon's published S3 host.
STOCK_SHA256 = "0ea9dcb2474a8a068cca98dc92a438fc233ff778d0ed1b4cd345f4fccef872ae"
INDEX_URL = "https://github.com/fireos-archive/fireos-archive"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(item):
    path = OUT / item["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_name(path.name + ".partial")
        for attempt in range(3):
            url = item["url"] + ("?download=" + str(attempt) if attempt else "")
            req = urllib.request.Request(url, headers={"User-Agent": "giza-file-preparation"})
            try:
                with urllib.request.urlopen(req, timeout=25) as response, temporary.open("wb") as stream:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        stream.write(chunk)
                break
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
                time.sleep(1)
        if temporary.stat().st_size != item["expected_bytes"]:
            raise RuntimeError(f"Unexpected download length for {path.name}")
        actual = digest(temporary)
        if item.get("expected_sha256") and actual != item["expected_sha256"]:
            raise RuntimeError(f"Digest mismatch for {path.name}; leaving .partial for review")
        temporary.replace(path)
    actual = digest(path)
    if path.stat().st_size != item["expected_bytes"]:
        raise RuntimeError(f"Unexpected existing file length for {path.name}")
    if item.get("expected_sha256") and actual != item["expected_sha256"]:
        raise RuntimeError(f"Digest mismatch for existing {path.name}")
    print(f"Prepared {item['path']} ({path.stat().st_size:,} bytes)", flush=True)
    return {**item, "bytes": path.stat().st_size, "sha256": actual}


def snapshot(repo, revision, filename):
    actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if actual != revision:
        raise RuntimeError(f"Unexpected revision for {repo.name}: {actual}")
    path = OUT / "sources" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar.gz", "--output=" + str(path), revision],
        check=True,
    )
    return {"path": str(path.relative_to(OUT)), "source_revision": revision,
            "bytes": path.stat().st_size, "sha256": digest(path),
            "purpose": "Pinned source snapshot; not an install package"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    url = "https://api.github.com/repos/hexdump0815/pmaports-amazon/releases/tags/" + TAG
    with urllib.request.urlopen(url, timeout=30) as stream:
        release = json.load(stream)
    if release["tag_name"] != TAG:
        raise RuntimeError("Unexpected release")
    (OUT / "linux-release.json").write_text(json.dumps(release, indent=2) + "\n")
    expected_names = {
        "boot.img.gz", "config-amazon-giza.aarch64.gz", "initramfs-extra.gz",
        "initramfs.gz", "lib-modules.tar.gz", "linux-amazon-giza-3.18.19-r4.apk", "vmlinuz.gz",
    }
    if {asset["name"] for asset in release["assets"]} != expected_names:
        raise RuntimeError("Release assets differ from the reviewed giza release")
    items = [{"path": "linux/" + asset["name"], "url": asset["browser_download_url"],
              "expected_bytes": asset["size"], "upstream_digest": asset.get("digest"),
              "purpose": "Experimental giza Linux; upstream explicitly says still untested"}
             for asset in release["assets"]]
    items.append({"path": "stock/update-kindle-49.6.2.6_user_626533320.bin", "url": STOCK_URL,
                  "expected_bytes": 737907632, "expected_sha256": STOCK_SHA256,
                  "digest_source": INDEX_URL,
                  "purpose": "Stock Fire OS 5.3.6.4 recovery reference; not an unlock downgrade"})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(download, items))
    results.append(snapshot(ROOT / "research/amonet-giza",
                            "dfe7f719bae9227cf8379ce3e7054aef2825962d", "amonet-giza-source.tar.gz"))
    results.append(snapshot(ROOT / "research/pmaports-amazon",
                            "ddd2b2f63d6135239f866460345342ae5a1d8002", "pmaports-amazon-source.tar.gz"))
    metadata = OUT / "linux-release.json"
    results.append({"path": "linux-release.json", "url": url,
                    "purpose": "GitHub release metadata refreshed during preparation",
                    "bytes": metadata.stat().st_size, "sha256": digest(metadata)})
    # Keep separately obtained originals and inspected derivatives in the inventory.
    previous_path = OUT / "manifest.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    generated_paths = {item["path"] for item in results}
    for item in previous.get("artifacts", []):
        if item["path"] not in generated_paths:
            path = OUT / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
                raise RuntimeError(f"Previously inventoried artifact changed: {item['path']}")
            results.append(item)
    manifest = {"target": "Amazon Fire HD 8 (2016, 6th gen), KFGIWI, giza",
                "prepared_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "flash_ready": False, "artifacts": results,
                "reason": "Live firmware/root and bootrom recovery checks pending; full native Omarchy image not available",
                "checks": previous.get("checks", {})}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "SHA256SUMS").write_text("".join(f"{x['sha256']}  {x['path']}\n" for x in results))
    print("Host-side artifacts prepared. No device actions performed; not flash-ready.")


if __name__ == "__main__":
    main()
