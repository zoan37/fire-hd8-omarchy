#!/usr/bin/env python3
"""Write and verify a temporary giza boot_x test, or restore its original image.

Requires this experiment's verified original local backup. Does not change GPT,
bootloader, or recovery. The desktop init arms recovery and a timed return.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
BACKUP = ROOT / "backups/20261003T233552Z/boot_x-before-linux.bin"
ORIGINAL_HASH = "c9b526d2f3ac5f99142d36a738b8cd9b7e20189b36fe02141366e6b8647c0a40"
BOOT_BYTES = 32536 * 512


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    devices = [line.split() for line in subprocess.check_output(["adb", "devices"], text=True).splitlines()[1:] if line.strip()]
    if len(devices) != 1 or devices[0][1] != "recovery":
        raise RuntimeError("Exactly one TWRP device is required")
    prefix = ["adb", "-s", devices[0][0]]

    def adb(*arguments):
        return subprocess.check_output(prefix + list(arguments), timeout=60)

    def shell(command):
        output = adb("shell", command + "; giza_status=$?; echo GIZA_REMOTE_EXIT=$giza_status")
        if not output.replace(b"\r", b"").rstrip().endswith(b"GIZA_REMOTE_EXIT=0"):
            raise RuntimeError(output.decode(errors="replace"))
        return output

    if adb("shell", "getprop ro.product.device").strip() != b"giza" or adb("shell", "getprop ro.product.model").strip() != b"omni_giza":
        raise RuntimeError("Only giza TWRP is supported")
    for partition, start, sectors in [(7, 59880, 32536), (21, 4457024, 1024), (24, 4499456, 25826304)]:
        shell(f'test "$(cat /sys/block/mmcblk0/mmcblk0p{partition}/start)" = {start} && test "$(cat /sys/block/mmcblk0/mmcblk0p{partition}/size)" = {sectors}')
    shell('test "$(readlink -f /dev/block/platform/mtk-msdc.0/by-name/boot_x)" = /dev/block/mmcblk0p7')
    original = BACKUP.read_bytes()
    if len(original) != BOOT_BYTES or digest(original) != ORIGINAL_HASH:
        raise RuntimeError("Original backup validation failed")
    current = adb("exec-out", "dd if=/dev/block/mmcblk0p7 bs=512 count=32536 2>/dev/null")
    previous = ROOT / "working/desktop/last-boot-test.bin"
    allowed = {ORIGINAL_HASH}
    if previous.exists():
        allowed.add(digest(previous.read_bytes()))
    if len(current) != BOOT_BYTES or digest(current) not in allowed:
        raise RuntimeError("Unexpected current boot_x contents; no write performed")
    if args.restore:
        payload = original
        flag = b"boot-recovery\0\0\0"
    else:
        if not (ROOT / "reports/desktop-binary-check.txt").exists():
            raise RuntimeError("Successful desktop staging evidence is required")
        shell("test -x /data/omarchy-rootfs/sbin/giza-init && test -x /data/omarchy-rootfs/usr/local/bin/giza-desktop")
        image = (ROOT / "working/linux-desktop-probe/boot.img").read_bytes()
        metadata = json.loads((ROOT / "working/linux-desktop-probe/manifest.json").read_text())
        if digest(image) != metadata["image_sha256"] or not metadata["kernel_unchanged"] or image[:8] != b"ANDROID!" or len(image) >= BOOT_BYTES:
            raise RuntimeError("Desktop test image validation failed")
        payload = image + original[len(image):]
        flag = bytes(16)
    temporary = ROOT / "working/desktop/boot-transfer.bin"
    temporary.write_bytes(payload)
    flag_path = ROOT / "working/desktop/boot-flag.bin"
    flag_path.write_bytes(flag)
    adb("push", str(temporary), "/tmp/giza-boot-transfer.bin")
    adb("push", str(flag_path), "/tmp/giza-boot-flag.bin")
    actual = shell("sha256sum /tmp/giza-boot-transfer.bin").split()[0].decode()
    if actual != digest(payload):
        raise RuntimeError("Boot transfer validation failed")
    shell("dd if=/tmp/giza-boot-transfer.bin of=/dev/block/mmcblk0p7 bs=4096 conv=notrunc && sync")
    readback = adb("exec-out", "dd if=/dev/block/mmcblk0p7 bs=512 count=32536 2>/dev/null")
    if readback != payload:
        raise RuntimeError("Boot readback mismatch; recovery remains installed")
    if not args.restore:
        previous.write_bytes(payload)
    shell("dd if=/tmp/giza-boot-flag.bin of=/dev/block/mmcblk0p21 bs=16 count=1 conv=notrunc && sync")
    if adb("exec-out", "dd if=/dev/block/mmcblk0p21 bs=16 count=1 2>/dev/null") != flag:
        raise RuntimeError("Boot flag readback mismatch")
    record = {"action": "restore" if args.restore else "desktop test", "partition": "boot_x / mmcblk0p7", "bytes": len(payload), "sha256": digest(payload), "full_readback_verified": True}
    (ROOT / "reports/desktop-boot-write.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)
    adb("reboot")


if __name__ == "__main__":
    main()
