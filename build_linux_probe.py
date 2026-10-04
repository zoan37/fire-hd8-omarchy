#!/usr/bin/env python3
"""Build a RAM-only Linux diagnostic boot image from the reviewed giza release."""
import gzip
import argparse
import hashlib
import io
import json
import pathlib
import stat
import struct
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "working/linux-probe"

INIT = b'''#!/bin/sh
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
/bin/busybox --install -s
/bin/busybox-extras --install -s
mkdir -p /dev /proc /sys /tmp /run
mount -t devtmpfs devtmpfs /dev
. /etc/deviceinfo
. /init_functions.sh
mount_proc_sys_dev
create_device_nodes
setup_mdev
exec >/probe.log 2>&1
echo "Giza RAM-only native Linux diagnostic probe"
uname -a
echo "No storage partitions are mounted or written by this init script."
echo 128 >/sys/class/leds/lcd-backlight/brightness
echo "Native Linux kernel test: USB diagnostics; automatic reboot in 120 seconds." >/dev/tty0
setup_framebuffer
show_splash /splash-debug-shell.ppm.gz
setup_usb_network
start_unudhcpd
sleep 2
telnetd -b 172.16.42.1:23 -l /bin/sh
echo "USB diagnostic shell listening on 172.16.42.1:23"
ip addr
# A recovery flag is set separately before fastboot boot. Reboot returns to TWRP.
(sleep 120; echo "Probe timeout; rebooting"; reboot -f) &
while true; do sleep 1; done
'''


def read_newc(data):
    entries = []
    offset = 0
    while offset + 110 <= len(data):
        header = data[offset:offset + 110]
        if header[:6] != b"070701":
            raise RuntimeError("Unexpected CPIO format")
        fields = [int(header[6 + n * 8:14 + n * 8], 16) for n in range(13)]
        start = offset + 110
        name = data[start:start + fields[11] - 1].decode()
        offset = (start + fields[11] + 3) & ~3
        content = data[offset:offset + fields[6]]
        offset = (offset + fields[6] + 3) & ~3
        if name == "TRAILER!!!":
            return entries
        relative = pathlib.PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Unsafe CPIO filename")
        entries.append((name, fields, content))
    raise RuntimeError("Missing CPIO trailer")


def write_newc(entries):
    result = bytearray()
    for name, fields, data in entries + [("TRAILER!!!", [0] * 13, b"")]:
        fields = fields.copy()
        encoded = name.encode() + b"\0"
        fields[6] = len(data)
        fields[11] = len(encoded)
        result += b"070701" + b"".join(f"{field:08x}".encode() for field in fields) + encoded
        result += b"\0" * (-len(result) % 4)
        result += data
        result += b"\0" * (-len(result) % 4)
    result += b"\0" * (-len(result) % 512)
    return bytes(result)


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-test", action="store_true",
                        help="Temporary boot_x test that arms recovery from Linux init")
    args = parser.parse_args()
    init = INIT
    if args.installed_test:
        OUT = ROOT / "working/linux-installed-probe"
        init = INIT.replace(b'echo "Giza RAM-only native Linux diagnostic probe"',
                            b'echo "Giza temporary boot-partition Linux diagnostic probe"')
        init = init.replace(
            b'echo "No storage partitions are mounted or written by this init script."',
            b'''# Only write the next-boot recovery flag, after matching the audited GPT.
if [ "$(cat /sys/block/mmcblk0/mmcblk0p21/start)" = "4457024" ] && \\
   [ "$(cat /sys/block/mmcblk0/mmcblk0p21/size)" = "1024" ]; then
    printf 'boot-recovery\\000\\000\\000' >/tmp/recovery-flag
    if dd if=/tmp/recovery-flag of=/dev/mmcblk0p21 bs=16 count=1 conv=notrunc; then
        sync
        echo "Recovery flag armed; no filesystems mounted."
        (sleep 120; echo "Probe timeout; rebooting to recovery"; reboot -f) &
    else
        echo "Recovery flag write failed; leave running for physical recovery."
    fi
else
    echo "Unexpected MISC partition layout; refusing recovery flag write."
fi''')
        init = init.replace(
            b'# A recovery flag is set separately before fastboot boot. Reboot returns to TWRP.\n(sleep 120; echo "Probe timeout; rebooting"; reboot -f) &\n', b'')
    OUT.mkdir(parents=True, exist_ok=True)
    data = gzip.decompress((ROOT / "prepared/linux/initramfs.gz").read_bytes())
    # The release assets wrap an already-gzipped ramdisk in a second gzip layer.
    data = gzip.decompress(data)
    entries = read_newc(data)
    rewritten = []
    for name, fields, content in entries:
        if name == "init":
            fields = fields.copy()
            fields[1] = stat.S_IFREG | 0o755
            content = init
        rewritten.append((name, fields, content))
    ramdisk = gzip.compress(write_newc(rewritten), mtime=0)
    (OUT / "init").write_bytes(init)
    (OUT / "initramfs.gz").write_bytes(ramdisk)
    original = (ROOT / "prepared/linux/boot.img").read_bytes()
    if original[:8] != b"ANDROID!":
        raise RuntimeError("Unexpected Android boot image")
    sizes = struct.unpack_from("<10I", original, 8)
    kernel_size, page = sizes[0], sizes[7]
    if page != 2048 or sizes[4] or sizes[8]:
        raise RuntimeError("Unexpected secondary kernel or DT section")
    kernel = original[page:page + kernel_size]
    header = bytearray(original[:page])
    struct.pack_into("<I", header, 16, len(ramdisk))
    cmdline = b"bootopt=64S3,32N2,64N2 loglevel=6 console=tty0 rdinit=/init net.ifnames=0 ipv6.disable=1"
    header[64:576] = cmdline.ljust(512, b"\0")
    digest = hashlib.sha1(kernel + struct.pack("<I", len(kernel)) + ramdisk + struct.pack("<I", len(ramdisk)) + struct.pack("<I", 0)).digest()
    header[576:608] = digest.ljust(32, b"\0")
    image = bytes(header) + kernel + b"\0" * (-len(kernel) % page) + ramdisk + b"\0" * (-len(ramdisk) % page)
    (OUT / "boot.img").write_bytes(image)
    metadata = {"source": "linux-amazon-giza-3.18.19-r4", "purpose": "RAM-only native Linux diagnostic boot; not Omarchy", "kernel_unchanged": True,
                "kernel_sha256": hashlib.sha256(kernel).hexdigest(), "image_sha256": hashlib.sha256(image).hexdigest(),
                "image_bytes": len(image), "ramdisk_bytes": len(ramdisk), "storage_mounts_in_init": False,
                "requires_recovery_flag_before_boot": True, "automatic_reboot_seconds": 120, "hardware_tested": False}
    if args.installed_test:
        metadata.update(purpose="Temporary boot_x Linux diagnostic; not Omarchy",
                        requires_recovery_flag_before_boot=False,
                        init_writes="16-byte next-boot recovery flag in audited MISC partition",
                        automatic_reboot_condition="Linux init reaches verified recovery-flag write")
    (OUT / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    # Minimal musl userspace archive for a compatibility check under recovery.
    selected = {"bin/busybox", "lib/ld-musl-aarch64.so.1", "lib/libc.musl-aarch64.so.1"}
    with tarfile.open(OUT / "userspace-check.tar", "w") as archive:
        for name, fields, content in entries:
            if name not in selected:
                continue
            item = tarfile.TarInfo(name)
            item.mode = fields[1] & 0o777
            if stat.S_ISLNK(fields[1]):
                item.type = tarfile.SYMTYPE
                item.linkname = content.decode()
                archive.addfile(item)
            elif stat.S_ISREG(fields[1]):
                item.size = len(content)
                archive.addfile(item, io.BytesIO(content))
            else:
                raise RuntimeError("Unexpected userspace entry type")
    print(f"Built Linux diagnostic image: {len(image):,} bytes; original kernel preserved.")


if __name__ == "__main__":
    main()
