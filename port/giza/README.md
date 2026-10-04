# Experimental native desktop port

This is an unfinished hardware experiment for giza, the 2016 Fire HD 8. The
postmarketOS Linux 3.18.19 kernel has booted on the tablet. The desktop path
below has not yet been tested on hardware.

The kernel exposes `/dev/fb0` and vendor Mali interfaces, but no DRM device.
The proposed display stack is Xorg with fbdev and evdev, Weston with its X11
backend and pixman renderer, then a patched ARM64 Hyprland with software Mesa
rendering. Omarchy's Quickshell and applications run in that native Arch ARM
root filesystem. Performance and touch behavior remain unknown.

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
succeeds. The present checkpoint requires a physical recovery restart followed
by an offline data filesystem repair. Preserve original partition backups and
the tested recovery route. There is no finished unattended installer.
