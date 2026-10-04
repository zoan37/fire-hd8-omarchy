#!/usr/bin/env python3
"""Back up boot/recovery/calibration blocks through temporary root; no block writes."""
import datetime
import hashlib
import json
import pathlib
import subprocess

from inspect_tablet import run, shell

ROOT = pathlib.Path(__file__).resolve().parent


def main():
    ready = [line.split()[0] for line in run(["adb", "devices"]).splitlines()[1:]
             if len(line.split()) == 2 and line.split()[1] == "device"]
    if len(ready) != 1:
        raise RuntimeError("Exactly one authorized tablet required")
    adb = ["adb", "-s", ready[0]]
    prefix = adb + ["shell"]
    if shell(prefix, "getprop ro.product.device") != "giza" or shell(prefix, "getprop ro.product.model") != "KFGIWI":
        raise RuntimeError("Incorrect tablet")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = ROOT / "backups" / stamp
    destination.mkdir(parents=True, mode=0o700)
    destination.parent.chmod(0o700)
    remote = "/data/local/tmp/fire-backup-" + stamp
    commands = ["#!/system/bin/sh", "set -e", "umask 077", f"mkdir {remote}", "b=/data/local/tmp/busybox",
                "blocks=$(cat /sys/block/mmcblk0/size)",
                f"$b dd if=/dev/block/mmcblk0 of={remote}/gpt-primary.bin bs=512 count=34",
                f"$b dd if=/dev/block/mmcblk0 of={remote}/gpt-backup.bin bs=512 skip=$((blocks-33)) count=33"]
    parts = {"boot0": "/dev/block/mmcblk0boot0", "boot1": "/dev/block/mmcblk0boot1"}
    for name in ("lk", "tee1", "tee2", "boot", "recovery", "MISC", "nvram", "proinfo", "protect1", "protect2", "seccfg", "frp"):
        parts[name] = "/dev/block/platform/soc/by-name/" + name
    for name, device in parts.items():
        commands.append(f"$b dd if={device} of={remote}/{name}.bin bs=4096")
    commands.extend([f"cd {remote}", "$b sha256sum *.bin > SHA256SUMS", "chmod 0755 .", "chmod 0644 *.bin SHA256SUMS"])
    script = destination / "read-partitions.sh"
    script.write_text("\n".join(commands) + "\n")
    script.chmod(0o600)
    for local, target in ((ROOT / "prepared/unlock/amonet-giza-v1.3/bin/busybox", "/data/local/tmp/busybox"),
                          (script, "/data/local/tmp/fire-read-partitions.sh")):
        subprocess.run(adb + ["push", str(local), target], capture_output=True, check=True, timeout=20)
    shell(prefix, "chmod 755 /data/local/tmp/busybox")
    shell(prefix, "chmod 755 /data/local/tmp/fire-read-partitions.sh")
    command = "/data/local/tmp/mtk-su -c /data/local/tmp/fire-read-partitions.sh"
    result = subprocess.run(prefix + [command + "; result=$?; echo __BACKUP_EXIT__:$result"],
                            capture_output=True, text=True, timeout=120)
    (destination / "backup-log.txt").write_text(result.stdout + result.stderr)
    if "__BACKUP_EXIT__:0" not in result.stdout:
        raise RuntimeError("Partition backup failed; inspect private backup-log.txt")
    subprocess.run(adb + ["pull", remote + "/.", str(destination)], capture_output=True, check=True, timeout=120)
    inventory = []
    for line in (destination / "SHA256SUMS").read_text().splitlines():
        expected, filename = line.split(maxsplit=1)
        if pathlib.PurePosixPath(filename).name != filename or not filename.endswith(".bin"):
            raise RuntimeError("Unexpected backup filename")
        path = destination / filename
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Backup checksum mismatch: {filename}")
        inventory.append({"path": filename, "bytes": path.stat().st_size, "sha256": actual})
    if len(inventory) != len(parts) + 2:
        raise RuntimeError("Incomplete backup inventory")
    for path in destination.iterdir():
        if path.is_file():
            path.chmod(0o600)
    (destination / "manifest.json").write_text(json.dumps({"target": "KFGIWI/giza", "artifacts": inventory}, indent=2) + "\n")
    (destination / "manifest.json").chmod(0o600)
    print(f"Verified {len(inventory)} original partition backups in {destination}")
    print("Original block devices were only read. Temporary backup files remain on the tablet.")


if __name__ == "__main__":
    main()
