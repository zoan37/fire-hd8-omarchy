#!/usr/bin/env python3
"""Collect selected read-only diagnostics from a Fire HD 8 (2016).

No root, pushes, reboots, partition reads/writes, or unlock operations.
ADB serial numbers are used for targeting but omitted from the report.
"""

import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return result.stdout.strip()


def shell(prefix, command):
    # Legacy Android ADB can return success even when the remote command fails.
    marker = "__FIRE_INSPECT_EXIT__:"
    output = run(prefix + [command + '; result=$?; echo ' + marker + '$result'])
    body, separator, status = output.rpartition(marker)
    if not separator or status.strip() != "0":
        raise RuntimeError(body.strip() or "Remote command failed")
    return body.strip()


def main():
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("ADB is missing on this computer.")
    entries = []
    for line in run([adb, "devices"]).splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2:
            entries.append((fields[0], fields[1]))
    ready = [serial for serial, state in entries if state == "device"]
    if not ready:
        states = ", ".join(state for _, state in entries) or "none connected"
        raise RuntimeError(
            f"No authorized tablet available ({states}). Connect a data cable, "
            "enable USB debugging, unlock the screen, and accept its debugging prompt."
        )
    if len(ready) != 1:
        raise RuntimeError("Multiple authorized ADB devices found. Disconnect the others first.")
    prefix = [adb, "-s", ready[0], "shell"]
    model = shell(prefix, "getprop ro.product.model")
    device = shell(prefix, "getprop ro.product.device")
    if model != "KFGIWI" or device != "giza":
        raise RuntimeError(f"Expected KFGIWI/giza; found {model!r}/{device!r}. Stop and identify this tablet.")

    properties = {}
    for name in (
        "ro.product.model", "ro.product.device", "ro.product.board",
        "ro.product.cpu.abi", "ro.product.cpu.abilist", "ro.product.cpu.abilist32",
        "ro.product.cpu.abilist64", "ro.build.version.release",
        "ro.build.version.sdk", "ro.build.version.security_patch",
        "ro.build.display.id", "ro.build.version.incremental",
        "ro.build.version.fireos", "ro.build.version.name",
        "ro.boot.tee_version", "ro.boot.lk_version", "ro.boot.pl_version",
        "ro.boot.flash.locked", "ro.boot.verifiedbootstate",
    ):
        properties[name] = shell(prefix, f"getprop {name}")
    diagnostics = {}
    for label, command in (
        ("kernel", "cat /proc/version"),
        ("userspace_elf_header", "od -An -tx1 -N5 /system/bin/sh"),
        ("android_linkers", "ls -l /system/bin/linker /system/bin/linker64"),
        ("data_storage", "df /data"),
        ("memory", "cat /proc/meminfo"),
        ("input_devices", "cat /proc/bus/input/devices"),
        ("block_partitions", "cat /proc/partitions"),
        ("partition_links", "ls -l /dev/block/platform/soc/by-name"),
        ("display_nodes", "ls -l /dev/graphics /dev/dri /dev/mali"),
        ("battery", "dumpsys battery"),
    ):
        try:
            diagnostics[label] = {"output": shell(prefix, command)}
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            diagnostics[label] = {"unavailable": str(error)}
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    report = {"collected_at": timestamp.isoformat(), "properties": properties, "diagnostics": diagnostics}
    directory = Path(__file__).resolve().parent / "reports"
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / (timestamp.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    with path.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    path.chmod(0o600)
    print(f"Identified Fire HD 8 (2016): {model}/{device}")
    print(f"Read-only report saved to {path}")
    print("No unlock or flash operations performed.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
