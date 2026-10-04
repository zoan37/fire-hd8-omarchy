Fire HD 8 (2016 / sixth generation / giza / KFGIWI) preparation
============================================================

CURRENT EXECUTION STATUS (October 3, 2026)

Temporary root and the bootrom exploit succeeded. The amonet bootloader
exploit is installed. Initial hacked fastboot reported unlocked=yes and
successfully flashed TWRP 3.3.1-0. TWRP booted with root ADB; its data/cache
format completed and /data mounted. User data was erased as authorized.
Sixteen original partition backups are verified in backups/20261003T233552Z.

Important: adb reboot bootloader from recovery enters a restricted fastboot
mode on this device, despite getvar unlocked reporting yes. It refused a MISC
write. fastboot reboot recovery reported success but booted into fresh Fire OS.
Power + Volume Down successfully returned to TWRP. Writing the temporary
boot-amonet MISC flag from TWRP, then using normal reboot, enters writable
hacked fastboot. That bootloader does not implement fastboot boot.

A temporary boot_x test in working/linux-installed-probe/ successfully booted
native aarch64 Linux 3.18.19 #5-postmarketOS. Its splash appeared on the tablet,
USB networking and a root diagnostic shell worked, and charging was reported.
The display is fb0, 800x1280, 32bpp; Goodix touch input is detected, but touch
interaction was not tested. CONFIG_DRM is disabled and no /dev/dri exists.
The test armed recovery and automatically returned to TWRP. The original full
boot_x partition was restored and readback verified against its original SHA256.
The tablet is left in TWRP, with the next boot directed to recovery.
Omarchy is not installed; its graphical desktop remains unresolved.
Actual device execution status is in reports/execution-status.json.

The working unlock copy is working/amonet-giza-reviewed/. It adds the source's
five-second reboot delay, fixes image size checks (including header size units),
matches USB vendor and product IDs, and uses a bounded root-mount script because
mtk-su r23's -c accepts an executable path, rather than a command with arguments.
The downloaded original archives and scripts in prepared/ are retained.

Preparation completed locally on October 3, 2026. No rooting, rebooting,
unlocking, partition writes or tablet erasure were performed during preparation.
The tablet was disconnected and charging from the wall.

FILES

prepared/unlock/amonet-giza-v1.3.zip
  Original author's unlock distribution, including its bootrom payload,
  preloader, LK, TZ, stock recovery and TWRP. ZIP CRCs checked.
  Source: https://xdaforums.com/attachments/amonet-giza-v1-3-zip.5551753/

prepared/unlock/amonet-giza-v1.3/
  Extracted distribution. Its scripts are unchanged. The separately downloaded
  ARM mtk-su binary has been added as bin/mtk-su, as the author requires.
  Executable permissions restored for scripts and binaries. Nothing executed.
  This is the prepared unlock directory; it is not a ready Omarchy installer.

prepared/unlock/mtk-su_r23.zip and mtk-su-r23/
  Original release 23 and both ARM / ARM64 binaries, obtained for this user's
  personal use. ARM is staged because its author supports both 32-bit and
  64-bit userspaces. Verify the tablet's actual ABI before using it.
  Source: https://xdaforums.com/attachments/mtk-su_r23-zip.5085853/
  Instructions: https://xdaforums.com/t/rapid-temporary-root-for-hd-8-hd-10.3904595/
  Respect the author's restrictions on bundling or auto-downloading mtk-su
  inside distributed software. It is not fetched by prepare_files.py.

prepared/stock/update-kindle-49.6.2.6_user_626533320.bin
  Fire OS 5.3.6.4 stock update matching the last recorded build. Fetched from
  Amazon S3; SHA256 matches the community firmware index. The Amazon vendor
  signature has not been independently verified. ZIP CRCs and giza metadata
  checked. This is a stock reference, not an unlock downgrade or a guaranteed
  recovery procedure. Selected original components are in reference-parts/.

prepared/linux/
  All seven assets from the giza 3.18.19-r4 release, plus decompressed boot.img
  and parsed boot-header.json. Gzip integrity and Android boot headers checked.
  The author explicitly calls this release "still untested". Its kernel has now
  booted here using our diagnostic initramfs; the original full OS is untested.
  Source: https://github.com/hexdump0815/pmaports-amazon/releases/tag/linux-amazon-giza-3.18.19-r4

prepared/sources/
  Pinned snapshots of amonet-giza and pmaports-amazon. Revisions in manifest.json.

prepared/host-tools/bin/dos2unix and .venv/
  Local dos2unix and Python with pyserial 3.5. The Arch dos2unix package's
  detached signature verified successfully against the installed Arch keyring.
  Host adb and fastboot are present. No system package or service was changed.

VERIFY

From this directory, run:
  python verify_files.py

prepared/manifest.json lists file sizes, SHA256 hashes, provenance and checks.
prepared/SHA256SUMS contains the same artifact inventory. These local hashes
detect later changes; they do not authenticate XDA or GitHub publications.
prepare_files.py refreshes the stock/Linux downloads and pinned snapshots;
it preserves and verifies previously inventoried supplemental files.
browser_download.py records the one-off original amonet browser download;
its page ID is session-specific and it is not a general-purpose installer.

NEXT DEVICE CHECKS

Reconnect over USB while charged. Start with inspect_tablet.py (read-only).
Confirm giza/KFGIWI, Fire OS build, bootloader versions, actual userspace ABI,
battery and storage; do not assume the old recorded values are still current.
Then assess temporary-root compatibility and bootrom recovery before invoking
any unlock script. ModemManager interference must be assessed at that stage.

Last recorded firmware: Fire OS 5.3.6.4 / build 626533320, kernel 3.18.19.
Last recorded versions: tee=258, lk=1, preloader=6. The unlock script permits
preloader <=2 in its direct path. With preloader 6 it proposes damaging the
preloader, flashing LK/TZ, rebooting into bootrom, and completing recovery with
bootrom-step-minimal.sh. These are actual bootloader writes, not a harmless
root test. No such action has been taken.

The official ZIP and pinned source differ in modules/main.py: the newer source
adds a five-second wait before reboot. Preserve this difference for review.
Both versions also discard the max_size argument in flash_binary; image sizes
and the live partition layout need checking before any writes.
The XDA recovery post calls an old downgrade 5.3.1.0, while its linked filename
is indexed elsewhere as 5.3.1.1. That downgrade has not been downloaded or used.

FULL OMARCHY STATUS

No working native Omarchy image has been built for this tablet. The available
giza Linux kernel uses the framebuffer and disables DRM; modern Hyprland needs
a usable DRM display path. Software rendering alone does not bridge this gap.
Booting Linux, solving display/kernel support, and adapting ARM userspace are
separate work still required. An unlock or TWRP install would not complete them.
These files support that investigation; full Omarchy is not promised to work.
