# Native Omarchy on Fire HD 8 (2016)

Hardware bring-up and desktop port work for the sixth-generation Amazon
Fire HD 8: **giza / KFGIWI, 1.5 GB RAM, 16 GB storage**.

This repository records an actual hardware experiment. It is **not a finished
Omarchy installer** and does not support newer Fire HD 8 models.

## Verified on hardware

- Temporary root and the amonet bootloader exploit succeeded.
- TWRP 3.3.1-0 boots and exposes root ADB.
- Sixteen original partition backups were saved and verified locally.
- A temporary boot image booted native aarch64 Linux 3.18.19 from the
  postmarketOS giza kernel release.
- The tablet displayed the postmarketOS splash. A USB network connection and
  root shell worked, and charging was reported.
- The framebuffer is 800 × 1280, 32 bpp. The Goodix touchscreen driver is
  detected; interactive touch behavior has not yet been verified.
- The test returned automatically to TWRP. The full original boot partition
  was restored and verified against its original SHA256.

**Full Omarchy has not yet run.** The kernel lacks DRM display support.
The next experiment uses Xorg's framebuffer driver, Weston, and patched ARM64
Hyprland userspace. That route remains unverified on this device.

## Latest checkpoint

The ARM64 desktop bundle and seven additional display packages were downloaded
and verified. A minimal Arch ARM Bash/glibc environment ran successfully under
the recovery kernel. The full root filesystem transfer passed its SHA256 check,
but extraction encountered an ext4 block-bitmap/free-block accounting error.
The journal aborted and the data partition became read-only. Recovery's unmount
and restart paths subsequently stalled; a physical restart into TWRP is needed
before an offline filesystem check can proceed.

The desktop boot image has **not** been flashed or tested. The original boot_x
image remains restored. No disk I/O failures were identified in the inspected
kernel log; the filesystem error alone does not establish a hardware fault.

## Files

- `inspect_tablet.py`: read-only checks for the original Fire OS environment.
- `backup_tablet.py`: original partition backup helper.
- `prepare_files.py`, `verify_files.py`: host artifact preparation and checks.
- `build_linux_probe.py`: diagnostic boot image builder. `--installed-test`
  builds the variant actually booted; its init only writes the audited
  next-boot recovery flag and returns to recovery after 120 seconds.
- `setup-bootrom-access.sh`: temporary host USB permissions helper.
- `prepare_desktop_packages.py`: dependency selection, package hash checks,
  and verification against the official Arch Linux ARM signing key.
- `build_desktop_overlay.py`, `stage_desktop.py`: native startup configuration
  and guarded offline package staging; neither flashes a boot partition.
- `port/giza/README.md`: experimental desktop architecture and prerequisites.
- `patches/`: reviewed changes to the original unlock distribution.
- `sources.lock.json`: upstream repositories and exact inspected revisions.
- `prepared/manifest.json`, `prepared/SHA256SUMS`: downloaded artifact inventory.
- `records/`: sanitized diagnostic evidence and status snapshots.
- `research-notes.txt`, `README.txt`: chronological research and preparation notes.

The notes contain historical checkpoints; the current status is summarized
above and in `records/execution-status.json`. Preparation-time statements do
not describe later device execution.

## Recovery findings

Power + Volume Down enters the installed TWRP. Hold the tablet with its screen
facing you and its ports at the top; Volume Down is the left volume button.
The TWRP system-partition prompt can remain on screen while ADB works.

`adb reboot bootloader` reaches a restricted fastboot implementation even
when `getvar unlocked` says yes. The audited `boot-amonet` MISC flag followed
by a normal reboot enters the writable hacked fastboot path. `fastboot boot`
is unsupported, and `fastboot reboot recovery` did not enter recovery here.

## Local artifacts

Downloaded firmware, release bundles, upstream checkouts, build output, raw
logs, and device-specific backups are ignored by Git. They remain in the
original workspace. The artifact inventory records URLs and checksums;
source revisions are pinned separately. The original unlock tools and mtk-su
must be obtained from their authors under their distribution terms.

Run `python sanitize_records.py` to refresh the committed diagnostic records
from local raw reports. It does not access or modify the tablet.
