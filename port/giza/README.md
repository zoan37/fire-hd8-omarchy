# Experimental native desktop port

This is an unfinished hardware experiment for giza, the 2016 Fire HD 8. The
postmarketOS Linux 3.18.19 kernel has booted on the tablet. Hyprland, Omarchy's real Quickshell shell, a terminal, and wvkbd have rendered
on the tablet. Physical tapping and typing have been confirmed.

The kernel exposes `/dev/fb0` and vendor Mali interfaces, but no DRM device.
The tested display stack is Xorg with fbdev and evdev, Weston with its X11
backend and pixman renderer, then a patched ARM64 Hyprland with software Mesa
rendering. Omarchy's Quickshell and applications run in that native Arch ARM
root filesystem. GPU acceleration is unavailable; graphics use llvmpipe. Broader application
compatibility and audio remain unverified. Native wireless networking now works.

Current systemd requires a newer kernel. `root/sbin/giza-init` is a temporary
native PID 1 supervisor that starts diagnostics, D-Bus, Xorg, and the desktop.
The initramfs mounts the data partition, binds its `omarchy-rootfs` directory as
the new root, and uses `switch_root`. It audits partition offsets before writing
the recovery boot flag. A desktop test returns to TWRP after ten minutes unless
an operator deliberately creates `/run/giza-keep-running`.

The ARM64 userspace and patched graphics binaries come from the pinned
`BlackFireAlex/omarchy-android` release recorded in `sources.lock.json` and
`records/desktop-package-manifest.json`. Its Android installer is not used.
`OMARCHY_PROOT=1` selects service-free application launching; this native boot
does not start PRoot or Android. The special Adreno/KGSL Mesa build is not used
on this Mali tablet.

Seven additional Arch Linux ARM packages provide Xorg, framebuffer/input
drivers, Weston, and missing dependencies. `prepare_desktop_packages.py` checks
their repository hashes and signatures using an isolated verification keyring.
`stage_desktop.py` verifies hashes again after ADB transfer. Its temporary
offline pacman config skips a second signature check because the bundle's
keyring differs; the normal signature-required pacman configuration is unchanged.
Package hooks and install scripts are skipped during recovery staging.

Configuration changes are confined to the user's Hyprland files and new giza
startup helpers. Original user configuration copies are preserved. Omarchy's
packaged `/usr/share/omarchy` tree is not edited.

## Local preparation helpers

The extracted, verified bundle must be available at `working/desktop/rootfs`.
These commands prepare local artifacts; they do not boot the tablet:

```sh
python prepare_desktop_packages.py
python build_desktop_overlay.py
python build_linux_probe.py --desktop-test
```

Before running `python stage_desktop.py`, the complete root filesystem must be
extracted to `/data/omarchy-rootfs` in giza TWRP. Staging checks the device model,
package transfers, pacman dependencies, and key executable versions.

Do not flash the desktop image until the filesystem is healthy and staging
succeeds. The earlier data filesystem error was repaired and a final offline
check passed. Native USB diagnostics and the corrected BusyBox helpers now work. Xwayland
is disabled because its initialization blocked Hyprland's main thread. The
framebuffer helper sets XRGB8888 channel masks without changing the 32-bit
pixel depth. Switching Xorg to 16-bit depth caused early resets and is avoided.
Preserve original partition backups and the tested recovery route. There is
no finished unattended installer.

## Tablet input

`giza-touch-pointer` reads the Goodix MT slots and exposes the first contact as
an absolute pointer with click events through `/dev/uinput`. Xorg reads the
stable `/dev/input/giza-touch-pointer` alias. This provides single-finger
pointer interaction; it does not implement multitouch gestures or rotation.

The keyboard source revision is pinned in `sources.lock.json`. The official
ARM compiler packages were verified before installation; their manifest is in
`records/keyboard-build-package-manifest.json`. To prepare that package set:

```sh
python prepare_desktop_packages.py --packages gcc make pkgconf --manifest reports/keyboard-build-package-manifest.json
```

The source was transferred to the native tablet, compiled with
`make -j2 wvkbd-mobintl`, then installed as `/usr/local/bin/wvkbd-mobintl`.
The rootfs must contain that binary before automatic desktop startup. Its
`-H 300` option gives a 300-logical-pixel keyboard. The user plugin adds a
**Keys** button; `giza-toggle-keyboard` sends SIGRTMIN to show/hide the keyboard.
Startup uses locks to prevent duplicate keyboards and terminals. An XTest
pointer test clicked the Keys button, typed a letter through wvkbd into foot,
and removed it with the keyboard's Backspace key. This verifies the desktop
input path but does not replace a physical finger test.

`giza-launch-shell` creates the bundle's required plugin index and then invokes
its packaged launcher. Omitting that index previously produced an empty bar.
User plugin/config changes preserve the packaged Omarchy tree.

## Performance checkpoint

Physical typing and restored pressed-key highlights are confirmed by the user,
who says typing feels a bit faster. Paired raw-touch/keyboard timing logs put
event delivery around 1–4 ms. The timing-only keyboard instrumentation has been
removed from the installed build.

A four-second `weston-simple-damage --verbose --width=160 --height=160` probe
produced 32–33 frames through Hyprland with two software-rendering workers,
compared with 236 through Weston directly. Both llvmpipe workers saturated
while Xorg/Weston used little CPU. Four workers produced 46 frames with VFR;
the final continuous-pacing setup produced 59. Short probes include startup
and are not general application benchmarks.

`giza-desktop` sets `LP_NUM_THREADS=4`. The root supervisor uses
`giza-render-boost on` to hold the vendor dynamic-boost request `-1 16`
(PRIO_MAX_CORES); `off` releases it with `-2 16`. A lock and marker prevent
repeated `on` calls from adding reference-counted requests. This retains the
interactive frequency governor and existing thermal/battery limits. Desktop
exit releases the request. The helper can also release it manually. Keeping
cores available can increase battery use; battery runtime has not been measured.

VFR reduced idle CPU work but left keyboard presentation stale in a probe:
the final unpressed state did not reach framebuffer memory within one second.
It is therefore disabled again, as the bundle's original compatibility config
recommends. Continuous pacing has a battery cost.

`patches/wvkbd-immediate-feedback.patch` applies to the pinned wvkbd revision.
Apply it before building and installing the keyboard described above. With
`WVKBD_IMMEDIATE_DRAW=1`, it submits completed drawing after event dispatch,
instead of waiting for a callback on an otherwise undamaged surface. The normal
callback path remains available when the environment switch is absent. The
launcher exports the switch for autostart and keyboard toggling.

Synthetic 220-ms taps reached a changed highlight pixel after about 242–265 ms
with immediate submission, compared with 370–375 ms without it. Final 80-ms
taps showed feedback after 249–272 ms and returned to the normal color. The test
used an isolated terminal running `read`, avoiding command execution or edits
to the user's terminal. These measurements observe `/dev/fb0` memory, not the
physical panel. Quick physical taps show highlights again according to the user.

Sources: [Mesa environment variables](https://docs.mesa3d.org/envvars.html),
[vendor boost interface](https://github.com/hexdump0815/linux-amazon-mediatek-mt8163-kernel-source/blob/Fire_HD8_6th_Gen-5.3.6.4-20201006/drivers/misc/mediatek/dynamic_boost/dynamic_boost.c),
[vendor mode definitions](https://github.com/hexdump0815/linux-amazon-mediatek-mt8163-kernel-source/blob/Fire_HD8_6th_Gen-5.3.6.4-20201006/drivers/misc/mediatek/dynamic_boost/dynamic_boost.h).

## Native Wi-Fi checkpoint

The tablet connects directly to the same Wi-Fi as the laptop, using its own
radio and NetworkManager. This is not USB internet sharing. Both root and the
desktop user reached the internet; an HTTPS request bound explicitly to
`wlan0` returned 200. A NetworkManager restart reconnected without intervention.
The actual Omarchy network panel shows Connected, nearby networks, and live
ping latency. This checkpoint does not include a full cold-boot Wi-Fi test.

`giza-wifi-radio` checks the model marker and original system partition's
geometry before mounting partition 19 at `/system` with `ro,noload`. It uses
preserved stock firmware and the small MediaTek `6620_launcher` hardware helper
with its stock ARM64 dynamic loader/libraries; Android itself does not run.
These vendor files are not redistributed. Their checksums are recorded in
`records/wifi-stock-files.json`. The driver is already built into this kernel.
Correct wmtdetect ioctl values are `0x80047703`, `0x40047701`, and `0x80047704`.
The aggregate initialization can report EPERM for an unsupported optional
function; the helper accepts this only when the Wi-Fi/WMT devices actually
appear. It does not initialize an already initialized driver again.

The driver loads `/etc/firmware/WIFI_RAM_CODE` directly, so an alias to the
stock `WIFI_RAM_CODE_8163` is required. Targeted character-device creation avoids
another broad mdev scan, which previously reset basic device permissions.
The radio helper starts the vendor launcher and powers the Wi-Fi function on.

Modern systemd/libudev needs statx mount-ID support absent in Linux 3.18.
Without compatible device support, NetworkManager rejected wlan0 as unmanaged,
reason 71. Eudev 3.2.14 fixes this without replacing packaged systemd libraries.
`/usr/local/libexec/giza/build-eudev` downloads the official pinned release,
checks its SHA-256, compiles natively, and installs under `/opt/giza-eudev`.
Its install command also redirects udev configuration into that prefix.

For a fresh experimental rootfs, first install the host-verified package sets
listed in `records/wifi-package-manifest.json` and
`records/eudev-build-package-manifest.json` (the latter adds gperf to the compiler
already used for wvkbd), then run the eudev build helper as root. The build uses
GCC, make, and pkgconf. No changes to the normal signature-required pacman
configuration are needed. The separate prefix is selected only for eudev and
NetworkManager processes with `LD_LIBRARY_PATH=/opt/giza-eudev/lib`.

`giza-init` starts `giza-wifi-start` in the background after system D-Bus. It
initializes the radio, starts eudev, announces only wlan0, and starts
NetworkManager. USB rndis0 remains explicitly unmanaged. An idempotent startup
check and service restart passed. Saved credentials exist only in mode-0600
files on the tablet and are excluded from Git. Future networks can be selected
from the Omarchy network panel; connecting to a different network has not been
physically tested. A direct wpa_supplicant/BusyBox DHCP fallback was tested
before NetworkManager; its optional DHCP hook remains available but is not
started in the normal setup.

A narrow local polkit rule lets user `omarchy` scan, connect, enable Wi-Fi, and
manage connection profiles without a logind session. Other administrative
NetworkManager actions keep their normal authorization requirements. The
startup helper allows only group 1000 to use ICMP datagram sockets, restoring
the network panel's latency display without making ping setuid.

The bundled service-free switch is still needed by other desktop components.
The stock network panel interprets it as Android-owned networking, so the
panel was cloned using `omarchy plugin clone` with a distinct `giza.network`
ID and adapted only under the user's configuration. The overlay reproduces
that clone and selects it in `shell.json`; packaged Omarchy files stay intact.
`giza-launch-shell --index-only` can refresh the prepared plugin catalog.
After restarting NetworkManager, Quickshell held stale device references;
restarting only its shell supervisor restored the connected panel without
restarting Hyprland, the user's terminal, or keyboard. Full native boot
integration remains to be exercised, and the next-boot recovery flag is still
armed.

Sources: [eudev 3.2.14 release](https://github.com/eudev-project/eudev/releases/tag/v3.2.14),
[giza kernel driver source](https://github.com/hexdump0815/linux-amazon-mediatek-mt8163-kernel-source/tree/Fire_HD8_6th_Gen-5.3.6.4-20201006/drivers/misc/mediatek/connectivity).
