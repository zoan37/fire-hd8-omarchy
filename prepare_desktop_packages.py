#!/usr/bin/env python3
"""Download and verify the ARM packages for the native framebuffer experiment."""
import base64
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import re
import subprocess
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
WORK = ROOT / "working/desktop"
DOWNLOADS = WORK / "downloads"
MIRROR = "https://ca.us.mirror.archlinuxarm.org/aarch64"
SIGNER = "68B3537F39A313B3E574D06777193F152BDBE6A6"
REQUESTED = ["xorg-server", "xf86-video-fbdev", "xf86-input-evdev", "weston"]


def fields(text):
    result = {}
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        if lines and lines[0].startswith("%"):
            result[lines[0].strip("%")] = lines[1:]
    return result


def one(package, key):
    return package[key][0]


def dependency(spec):
    return re.split(r"[<>=]", spec, maxsplit=1)[0]


def download(url, path):
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".partial")
        with urllib.request.urlopen(url, timeout=30) as source, temporary.open("wb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        temporary.replace(path)
    return path


def main(requested=None, output=None):
    requested = requested or REQUESTED
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    available = {}
    for repo in ("core", "extra"):
        path = download(f"{MIRROR}/{repo}/{repo}.db", DOWNLOADS / f"{repo}.db")
        grouped = {}
        with tarfile.open(path) as archive:
            for member in archive:
                if member.name.endswith(("/desc", "/depends")):
                    group = grouped.setdefault(member.name.split("/")[0], {})
                    group.update(fields(archive.extractfile(member).read().decode()))
        for package in grouped.values():
            # A mirror can retain an orphan dependency entry during a sync.
            if "NAME" not in package or "FILENAME" not in package:
                continue
            package["repo"] = [repo]
            available[one(package, "NAME")] = package

    installed = {}
    for path in (WORK / "rootfs/var/lib/pacman/local").glob("*/desc"):
        package = fields(path.read_text())
        installed[one(package, "NAME")] = package
    installed_names = set(installed)
    for package in installed.values():
        installed_names.update(dependency(x) for x in package.get("PROVIDES", []))

    providers = {}
    for package in available.values():
        for spec in package.get("PROVIDES", []):
            providers.setdefault(dependency(spec), one(package, "NAME"))

    selected = {}

    def resolve(name, force=False):
        if name in selected or (not force and name in installed_names):
            return
        name = name if name in available else providers.get(name, name)
        if name not in available:
            raise RuntimeError(f"Missing dependency: {name}")
        package = available[name]
        selected[name] = package
        for spec in package.get("DEPENDS", []):
            dep = dependency(spec)
            # These packages primarily depend on libraries already in the
            # checksum-verified bundle. Retain its accepted package closure.
            if dep in installed and dep != spec:
                required = re.match(r"^([^<>=]+)(>=|<=|=|>|<)(.+)$", spec)
                if required:
                    comparison = int(subprocess.check_output(
                        ["vercmp", one(installed[dep], "VERSION"), required[3]], text=True))
                    matches = {">=": comparison >= 0, "<=": comparison <= 0,
                               "=": comparison == 0, ">": comparison > 0,
                               "<": comparison < 0}[required[2]]
                    if not matches:
                        resolve(dep, force=True)
                        continue
            resolve(dep)

    for name in requested:
        resolve(name, force=True)

    keyring = download(
        "https://raw.githubusercontent.com/archlinuxarm/archlinuxarm-keyring/master/archlinuxarm.gpg",
        DOWNLOADS / "archlinuxarm.gpg")
    key_output = subprocess.check_output(
        ["gpg", "--show-keys", "--with-colons", str(keyring)], stderr=subprocess.DEVNULL, text=True)
    if SIGNER not in key_output:
        raise RuntimeError("Official ARM build-system signing key is missing")
    verification_home = WORK / "gpg-verification"
    verification_home.mkdir(mode=0o700, exist_ok=True)
    binary_keyring = verification_home / "archlinuxarm-keyring.gpg"
    subprocess.run(["gpg", "--batch", "--yes", "--dearmor", "--output",
                    str(binary_keyring), str(keyring)], check=True)

    def fetch(package):
        filename = one(package, "FILENAME")
        path = DOWNLOADS / filename
        url = f"{MIRROR}/{one(package, 'repo')}/{filename}"
        download(url, path)
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != one(package, "SHA256SUM"):
            raise RuntimeError(f"Package hash mismatch: {filename}")
        signature = path.with_suffix(path.suffix + ".sig")
        signature.write_bytes(base64.b64decode(one(package, "PGPSIG")))
        checked = subprocess.run(
            ["gpgv", "--homedir", str(verification_home), "--keyring", str(binary_keyring),
             "--status-fd", "1", str(signature), str(path)], capture_output=True, text=True)
        if checked.returncode or f"VALIDSIG {SIGNER}" not in checked.stdout:
            raise RuntimeError(f"Signature check failed: {filename}: {checked.stderr}")
        print(f"Verified {filename}", flush=True)
        return {"name": one(package, "NAME"), "version": one(package, "VERSION"),
                "url": url, "filename": filename, "sha256": actual,
                "signer_fingerprint": SIGNER, "signature_verified": True}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch, selected.values()))
    manifest = {"purpose": "Native Linux framebuffer desktop experiment",
                "requested": requested, "packages": results,
                "bundle": {"version": "0.1.1", "url":
                    "https://github.com/BlackFireAlex/omarchy-android/releases/download/v0.1.1/omarchy-android-aarch64-0.1.1.bundle.tar",
                    "sha256": "7e9f1cd67533bc0d3988b5cb3831aef52f1527dd90391d9d868ed9345021cdb2"}}
    (output or ROOT / "reports/desktop-package-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified {len(results)} packages. No device changes performed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", nargs="+", default=REQUESTED)
    parser.add_argument("--manifest", type=pathlib.Path)
    args = parser.parse_args()
    main(args.packages, args.manifest)
