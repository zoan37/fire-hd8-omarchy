#!/bin/sh
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
/bin/busybox --install -s
/bin/busybox-extras --install -s
mkdir -p /dev /proc /sys /tmp /run /newroot /data-root
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /run
. /etc/deviceinfo
. /init_functions.sh
mount_proc_sys_dev
create_device_nodes
setup_mdev
exec >/probe.log 2>&1
echo "Native Arch/Omarchy desktop bring-up on giza"
uname -a

# Match the audited device layout before any partition write or mount.
if [ "$(cat /sys/block/mmcblk0/mmcblk0p21/start)" != 4457024 ] ||
   [ "$(cat /sys/block/mmcblk0/mmcblk0p21/size)" != 1024 ] ||
   [ "$(cat /sys/block/mmcblk0/mmcblk0p24/start)" != 4499456 ] ||
   [ "$(cat /sys/block/mmcblk0/mmcblk0p24/size)" != 25826304 ]; then
    echo "Unexpected partition layout; stopping without writes."
    while true; do sleep 1; done
fi
printf 'boot-recovery\000\000\000' >/tmp/recovery-flag
dd if=/tmp/recovery-flag of=/dev/mmcblk0p21 bs=16 count=1 conv=notrunc || exit 1
sync
echo 128 >/sys/class/leds/lcd-backlight/brightness
setup_framebuffer
show_splash /splash-debug-shell.ppm.gz
setup_usb_network_android
start_unudhcpd

if ! mount -t ext4 -o rw,noatime /dev/mmcblk0p24 /data-root ||
   ! mount --bind /data-root/omarchy-rootfs /newroot ||
   [ ! -x /newroot/sbin/giza-init ]; then
    echo "Arch root filesystem unavailable; USB diagnostic shell remains available."
    telnetd -b 172.16.42.1:23 -l /bin/sh
    (sleep 120; reboot -f) &
    while true; do sleep 1; done
fi

# Keep the tested musl helpers alongside Arch's glibc. There is no Android
# userspace, PRoot, or CPU emulation after switch_root.
mkdir -p /newroot/usr/local/libexec /newroot/usr/lib /newroot/var/log
cp /bin/busybox /newroot/usr/local/libexec/giza-busybox
cp /bin/busybox-extras /newroot/usr/local/libexec/giza-busybox-extras
cp -L /lib/ld-musl-aarch64.so.1 /newroot/usr/lib/ld-musl-aarch64.so.1
ln -sf ld-musl-aarch64.so.1 /newroot/usr/lib/libc.musl-aarch64.so.1
cp /probe.log /newroot/var/log/giza-initramfs.log
mkdir -p /newroot/dev /newroot/proc /newroot/sys /newroot/run
mount --move /dev /newroot/dev
mount --move /proc /newroot/proc
mount --move /sys /newroot/sys
mount --move /run /newroot/run
exec /bin/busybox switch_root /newroot /sbin/giza-init
