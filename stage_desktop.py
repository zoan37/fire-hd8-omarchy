#!/usr/bin/env python3
"""Stage verified native desktop packages/configuration through giza TWRP ADB.

Requires the verified rootfs archive to have been extracted already. This
helper never flashes a boot image, repartitions, or erases the tablet.
"""
import hashlib
import json
import pathlib
import shlex
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
WORK = ROOT / "working/desktop"
DEVICE_ROOT = "/data/omarchy-rootfs"


def main():
    listing = subprocess.check_output(["adb", "devices"], text=True)
    devices = [line.split() for line in listing.splitlines()[1:] if line.strip()]
    if len(devices) != 1 or devices[0][1] != "recovery":
        raise RuntimeError("Exactly one TWRP device must be connected")
    prefix = ["adb", "-s", devices[0][0]]

    def adb(*args, timeout=120):
        result = subprocess.run(prefix + list(args), capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace") + result.stdout.decode(errors="replace"))
        return result.stdout

    def shell(command, timeout=120):
        # adb shell on this old recovery does not propagate remote exit codes.
        output = adb("shell", command + "; giza_status=$?; echo GIZA_REMOTE_EXIT=$giza_status", timeout=timeout)
        text = output.decode(errors="replace").replace("\r", "")
        if not text.rstrip().endswith("GIZA_REMOTE_EXIT=0"):
            raise RuntimeError(text)
        return text

    if adb("shell", "getprop ro.product.device").strip() != b"giza" or \
       adb("shell", "getprop ro.product.model").strip() != b"omni_giza":
        raise RuntimeError("This helper only supports giza TWRP")
    shell(f"test -x {DEVICE_ROOT}/usr/bin/bash && test -x {DEVICE_ROOT}/opt/omarchy-android/hyprland/bin/Hyprland")
    manifest = json.loads((ROOT / "reports/desktop-package-manifest.json").read_text())
    shell(f"mkdir -p {DEVICE_ROOT}/var/tmp/giza-packages")
    package_paths = []
    for package in manifest["packages"]:
        if not package["signature_verified"]:
            raise RuntimeError("Unverified package in manifest")
        path = WORK / "downloads" / package["filename"]
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != package["sha256"]:
                raise RuntimeError(f"Changed local package: {path.name}")
        device_path = f"{DEVICE_ROOT}/var/tmp/giza-packages/{path.name}"
        adb("push", str(path), device_path)
        actual = shell(f"sha256sum {shlex.quote(device_path)}").split()[0]
        if actual != package["sha256"]:
            raise RuntimeError(f"Device transfer mismatch: {path.name}")
        package_paths.append("/var/tmp/giza-packages/" + path.name)

    # Every package was signature-verified against the official ARM build key
    # on the host, then hash-verified after transfer. Use a temporary offline
    # config so the base bundle's different keyring does not block installation.
    # The tablet's normal signature-required pacman.conf remains unchanged.
    config = WORK / "offline-pacman.conf"
    config.write_text("[options]\nArchitecture = aarch64\nSigLevel = Never\n"
                      "LocalFileSigLevel = Never\nDisableSandboxSyscalls\nDisableSandboxFilesystem\n")
    adb("push", str(config), f"{DEVICE_ROOT}/var/tmp/giza-offline-pacman.conf")
    mounts = []
    hooks = f"{DEVICE_ROOT}/usr/share/libalpm/hooks"
    saved_hooks = f"{DEVICE_ROOT}/var/tmp/giza-saved-hooks"
    try:
        for source, target in [("/dev", "dev"), ("/proc", "proc"), ("/sys", "sys")]:
            destination = f"{DEVICE_ROOT}/{target}"
            shell(f"mkdir -p {destination} && mount --bind {source} {destination}")
            mounts.append(destination)
        shell(f"test ! -e {saved_hooks} && mv {hooks} {saved_hooks} && mkdir {hooks}")
        command = f"chroot {DEVICE_ROOT} /usr/bin/pacman --config /var/tmp/giza-offline-pacman.conf --noconfirm --noscriptlet --needed -U "
        command += " ".join(shlex.quote(path) for path in package_paths)
        output = shell(command, timeout=300)
        (ROOT / "reports/desktop-package-install.txt").write_text(output)
        print(output, flush=True)
    finally:
        # Restore only our own temporary hook move; do not erase hook contents.
        shell(f"if test -d {saved_hooks}; then rmdir {hooks} && mv {saved_hooks} {hooks}; fi")
        for destination in reversed(mounts):
            shell(f"umount {destination}")
    shell(f"rm -f {DEVICE_ROOT}/var/tmp/giza-offline-pacman.conf")

    overlay = WORK / "giza-desktop-overlay.tar"
    adb("push", str(overlay), "/data/omarchy-stage/giza-overlay.tar")
    shell(f"tar -xpf /data/omarchy-stage/giza-overlay.tar -C {DEVICE_ROOT} && sync")
    output = shell(f"chroot {DEVICE_ROOT} /usr/bin/bash --noprofile --norc -c " + shlex.quote(
        "set -e; echo NATIVE_DESKTOP_BINARIES; "
        "LD_LIBRARY_PATH=/opt/omarchy-android/aquamarine/lib /opt/omarchy-android/hyprland/bin/Hyprland --version; "
        "weston --version; /usr/lib/Xorg -version; "
        "test -x /sbin/giza-init && test -x /usr/local/bin/giza-desktop"))
    (ROOT / "reports/desktop-binary-check.txt").write_text(output)
    print(output, flush=True)


if __name__ == "__main__":
    main()
