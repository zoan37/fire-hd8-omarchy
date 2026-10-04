#!/bin/bash
# Temporary, device-specific host permissions. No tablet commands.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Administrator access required.' >&2; exit 1; }
rule=/run/udev/rules.d/99-fire-hd8-codex-1000.rules
if [[ ${1:-} == --remove ]]; then
  rm -f -- "$rule"
  udevadm control --reload-rules
  echo 'Removed the temporary Fire bootrom access rule.'
  exit 0
fi
[[ $# == 0 ]] || exit 2
[[ $(id -u zoan) == 1000 ]] || { echo 'Unexpected laptop user ID.' >&2; exit 1; }
install -d -m 0755 /run/udev/rules.d
cat > "$rule" <<'RULE'
# Fire HD 8 preparation: MediaTek bootrom/preloader only; disappears on reboot.
SUBSYSTEM=="usb", ATTR{idVendor}=="0e8d", ATTR{idProduct}=="0003|2000", OWNER="1000", MODE="0600"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0e8d", ATTRS{idProduct}=="0003|2000", OWNER="1000", MODE="0600"
RULE
chmod 0644 "$rule"
udevadm control --reload-rules
udevadm trigger --subsystem-match=usb --attr-match=idVendor=0e8d
udevadm trigger --subsystem-match=tty
udevadm settle --timeout=10
echo 'Temporary MediaTek bootrom/preloader permissions ready for laptop user zoan.'
