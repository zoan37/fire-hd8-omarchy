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
  detected; a native input adapter now exposes an absolute click pointer; physical tapping and typing have been confirmed.
- The test returned automatically to TWRP. The full original boot partition
  was restored and verified against its original SHA256.

**Native Hyprland, the Omarchy shell, a terminal, and an on-screen keyboard
have now rendered on the tablet.** This remains an experimental ARM port with
software graphics and a temporary boot supervisor, rather than a supported
Omarchy installation.

## Latest checkpoint

The native display stack is Xorg/fbdev → Weston/pixman → patched ARM64
Hyprland/llvmpipe. A framebuffer channel-order correction makes Weston work.
Xwayland is disabled because its startup blocked the compositor. Hyprland's
configuration reload and error checks pass; its output is 800 × 1280 at 30 Hz
and scale 1.25. Omarchy's real Quickshell bar and wallpaper are visible.

A small native adapter converts the Goodix driver's multitouch positions into
an absolute click pointer for Xorg. Physical touch and typing were confirmed by the user. The wvkbd on-screen keyboard was compiled on the tablet from a
pinned source revision. Simulated pointer clicks also verified typing into the terminal and the show/hide
button. A user plugin adds a
**Keys** button to Omarchy's bar. A terminal and keyboard start with the desktop.

The user reports typing feels a bit faster after tuning, and pressed-key
highlights work again. The software renderer now uses four workers and a
reversible vendor four-core request. A four-second animation probe improved
from 32–33 frames to 59 frames; direct rendering through Weston reached 236.
A keyboard patch submits feedback without waiting for an extra frame. Synthetic
80-ms taps changed the framebuffer highlight after about 249–272 ms. These are
framebuffer-memory measurements, not physical panel timing.

VFR was reverted because it could leave the final keyboard update waiting.
Continuous frame pacing and the core request can increase battery use. The
normal frequency governor and thermal limits remain in place. Physical touch
reaches the keyboard handler in about 1–4 ms; software presentation remains
the main limitation.

USB diagnostics and native Wi-Fi work. NetworkManager connects to the laptop’s
saved Wi-Fi network, and HTTPS over `wlan0` returned 200 as the desktop user.
Omarchy’s user-owned network panel shows the connected network, scan results,
and live latency. Service restart/autoconnect passed; Wi-Fi after a full native
reboot has not yet been tested. Audio, suspend, rotation, and broader application
compatibility remain unverified. Current
systemd cannot run on this 3.18 kernel, so a Bash PID 1 starts the experiment.

The temporary desktop image remains installed in boot_x. Original partition
backups and TWRP are preserved. The next boot is armed for recovery, and the
10-minute test timer can be suppressed with `/run/giza-keep-running`.
`test_desktop_boot.py --restore` restores the verified original boot image
from TWRP. There is no finished unattended installer.

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
- `test_desktop_boot.py`: guarded temporary boot_x write, full readback, and
  restoration of the original verified image.
- `usb_shell.py`: local USB diagnostic shell client for native Linux boots.
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
