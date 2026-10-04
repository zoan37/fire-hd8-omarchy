#!/usr/bin/env python3
"""Export diagnostic evidence without device serials or host network addresses."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent


def sanitize(text):
    text = re.sub(r"\bG000[A-Z0-9]+\b", "REDACTED_DEVICE_SERIAL", text)
    text = re.sub(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b", "REDACTED_MAC", text)
    text = re.sub(r"\bwlx[0-9a-fA-F]{12}\b", "REDACTED_MAC_INTERFACE", text)
    text = re.sub(r"\b192\.168\.(?:\d{1,3}\.)\d{1,3}\b", "REDACTED_HOST_IP", text)
    # Host Wi-Fi interface lines contain globally routable IPv6 addresses.
    text = re.sub(r"^wlp[^\n]*", "[host Wi-Fi addresses omitted]", text, flags=re.M)
    text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    text = re.sub(r"\x1b\][\s\S]*?(?:\x07|\x1b\\)", "", text)
    text = re.sub(r"\x00+", "\n[zero-filled log gap]\n", text)
    text = re.sub(r"^(?:Set-Cookie|Cookie|Authorization|Proxy-Authorization):[^\n]*",
                  "[HTTP credential header omitted]", text, flags=re.M | re.I)
    return text


def main():
    output = ROOT / "records"
    output.mkdir(exist_ok=True)
    count = 0
    for source in sorted((ROOT / "reports").glob("*")):
        if not source.is_file() or source.suffix not in {".txt", ".json"}:
            continue
        text = source.read_text(errors="replace")
        (output / source.name).write_text(sanitize(text))
        count += 1
    print(f"Exported {count} sanitized diagnostic records.")


if __name__ == "__main__":
    main()
