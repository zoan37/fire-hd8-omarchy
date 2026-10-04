#!/usr/bin/env python3
"""Package the native giza configuration without changing upstream Omarchy."""
import io
import pathlib
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent
WORK = ROOT / "working/desktop"


def main():
    payload = ROOT / "port/giza/root"
    files = {}
    for path in payload.rglob("*"):
        if path.is_file():
            files[str(path.relative_to(payload))] = path.read_bytes()
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
        "hl.config({ animations = { enabled = false }, debug = { enable_stdout_logs = true } })\n"
    ).encode()
    files["etc/giza-native-release"] = b"GIZA_NATIVE_EXPERIMENT=1\nTARGET=giza-KFGIWI\n"
    files["etc/hostname"] = b"fire-giza\n"
    files["etc/pacman.d/mirrorlist"] = b"Server = https://ca.us.mirror.archlinuxarm.org/$arch/$repo\n"
    output = WORK / "giza-desktop-overlay.tar"
    with tarfile.open(output, "w") as archive:
        for name, data in sorted(files.items()):
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o755 if data.startswith(b"#!") else 0o644
            item.uid = item.gid = 1000 if name.startswith("home/omarchy/") else 0
            archive.addfile(item, io.BytesIO(data))
    print(f"Built native configuration overlay: {len(files)} files, {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
