#!/usr/bin/env python3
"""Package the native giza configuration without changing upstream Omarchy."""
import io
import gzip
import json
import pathlib
import tarfile
from build_linux_probe import read_newc

ROOT = pathlib.Path(__file__).resolve().parent
WORK = ROOT / "working/desktop"


def main():
    payload = ROOT / "port/giza/root"
    files = {}
    for path in payload.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(payload))] = path.read_bytes()
    # Stage the diagnostic helpers ahead of boot so their actual applet
    # dispatch can be checked under the recovery kernel.
    ramdisk = gzip.decompress(gzip.decompress((ROOT / "prepared/linux/initramfs.gz").read_bytes()))
    helper_paths = {
        "bin/busybox": "usr/local/libexec/giza/busybox",
        "bin/busybox-extras": "usr/local/libexec/giza/busybox-extras",
        "lib/ld-musl-aarch64.so.1": "usr/lib/ld-musl-aarch64.so.1",
    }
    for name, _, data in read_newc(ramdisk):
        if name in helper_paths:
            files[helper_paths[name]] = data
    if not all(destination in files for destination in helper_paths.values()):
        raise RuntimeError("Missing native diagnostic helper in source ramdisk")
    home = "home/omarchy"
    original = WORK / "rootfs" / home / ".config/hypr/hyprland.lua"
    config = original.read_text()
    config = config.replace("omarchy-shell-launch.lock omarchy-launch-shell",
                            "omarchy-shell-launch.lock giza-launch-shell")
    files[f"{home}/.config/hypr/hyprland.lua.giza-original"] = original.read_bytes()
    files[f"{home}/.config/hypr/hyprland.lua"] = config.encode()
    original_look = WORK / "rootfs" / home / ".config/hypr/looknfeel.lua"
    files[f"{home}/.config/hypr/looknfeel.lua.giza-original"] = original_look.read_bytes()
    files[f"{home}/.config/hypr/looknfeel.lua"] = (
        original_look.read_text() + "\n-- Keep the software-rendered giza desktop responsive.\n"
        "hl.config({ animations = { enabled = false }, debug = { enable_stdout_logs = true, vfr = false }, "
        "xwayland = { enabled = false } })\n"
    ).encode()
    shell_config = json.loads((WORK / "rootfs" / home / ".config/omarchy/shell.json").read_text())
    shell_config["bar"]["layout"]["left"].insert(0, {"id": "giza.keyboard"})
    files[f"{home}/.config/omarchy/shell.json.giza-original"] = (
        WORK / "rootfs" / home / ".config/omarchy/shell.json").read_bytes()
    files[f"{home}/.config/omarchy/shell.json"] = (json.dumps(shell_config, indent=2) + "\n").encode()
    autostart = (WORK / "rootfs" / home / ".config/hypr/autostart.lua").read_text()
    files[f"{home}/.config/hypr/autostart.lua"] = (autostart +
        '\nhl.on("hyprland.start", function()\n'
        '  hl.exec_cmd("flock -n $XDG_RUNTIME_DIR/giza-keyboard.lock wvkbd-mobintl -H 300")\n'
        '  hl.exec_cmd("flock -n $XDG_RUNTIME_DIR/giza-terminal.lock foot")\n'
        'end)\n').encode()
    files["etc/giza-native-release"] = b"GIZA_NATIVE_EXPERIMENT=1\nTARGET=giza-KFGIWI\n"
    files["etc/hostname"] = b"fire-giza\n"
    files["etc/pacman.d/mirrorlist"] = b"Server = https://ca.us.mirror.archlinuxarm.org/$arch/$repo\n"
    output = WORK / "giza-desktop-overlay.tar"
    with tarfile.open(output, "w") as archive:
        for name, data in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o755 if data.startswith((b"#!", b"\x7fELF")) else 0o644
            item.uid = item.gid = 1000 if name.startswith("home/omarchy/") else 0
            archive.addfile(item, io.BytesIO(data))
        alias = tarfile.TarInfo("usr/lib/libc.musl-aarch64.so.1")
        alias.type = tarfile.SYMTYPE
        alias.linkname = "ld-musl-aarch64.so.1"
        alias.mode = 0o777
        archive.addfile(alias)
    print(f"Built native configuration overlay: {len(files)} files, {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
