#!/usr/bin/env python3
"""Check the prepared inventory locally, without contacting any device."""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent / "prepared"


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    expected = {}
    for item in manifest["artifacts"]:
        relative = pathlib.PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or item["path"] in expected:
            raise RuntimeError("Invalid or duplicate inventory path")
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or path.stat().st_size != item["bytes"]:
            raise RuntimeError(f"Missing or changed file: {relative}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != item["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {relative}")
        expected[item["path"]] = item["sha256"]
    sums = {}
    for line in (ROOT / "SHA256SUMS").read_text().splitlines():
        sha256, relative = line.split("  ", 1)
        if relative in sums:
            raise RuntimeError("Duplicate checksum path")
        sums[relative] = sha256
    if sums != expected:
        raise RuntimeError("Manifest and SHA256SUMS disagree")
    print(f"Verified {len(expected)} prepared files. No tablet access or writes.")
    print("Hardware validation and a working native Omarchy image remain pending.")


if __name__ == "__main__":
    main()
