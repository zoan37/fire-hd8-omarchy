#!/usr/bin/env python3
"""Run a command through the native probe's local USB Telnet diagnostic shell."""
import argparse
import re
import socket
import time
import uuid


class TelnetStream:
    def __init__(self, connection):
        self.connection = connection
        self.state = "data"
        self.option_command = None

    def decode(self, chunk):
        output = bytearray()
        for value in chunk:
            if self.state == "data":
                if value == 255:
                    self.state = "iac"
                else:
                    output.append(value)
            elif self.state == "iac":
                if value == 255:
                    output.append(value)
                    self.state = "data"
                elif value in (251, 252, 253, 254):
                    self.option_command = value
                    self.state = "option"
                elif value == 250:
                    self.state = "sub"
                else:
                    self.state = "data"
            elif self.state == "option":
                if self.option_command in (251, 253):
                    refusal = 254 if self.option_command == 251 else 252
                    self.connection.sendall(bytes((255, refusal, value)))
                self.state = "data"
            elif self.state == "sub":
                if value == 255:
                    self.state = "sub_iac"
            elif self.state == "sub_iac":
                self.state = "data" if value == 240 else "sub"
        return bytes(output)


def run(command, timeout=45):
    marker = "GIZA_COMMAND_" + uuid.uuid4().hex
    output = bytearray()
    deadline = time.monotonic() + timeout
    with socket.create_connection(("172.16.42.1", 23), timeout=5) as connection:
        connection.settimeout(0.5)
        stream = TelnetStream(connection)
        # The shell is started directly by telnetd; no login prompt is involved.
        connection.sendall((command + "; giza_rc=$?; printf '\\n" + marker + "=%s\\n' \"$giza_rc\"\r\n").encode())
        while time.monotonic() < deadline:
            try:
                chunk = connection.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                break
            output.extend(stream.decode(chunk))
            clean = bytes(output).replace(b"\r", b"")
            match = re.search(rb"(?:^|\n)" + marker.encode() + rb"=(\d+)\n", clean)
            if match:
                return clean[:match.start()].decode(errors="replace"), int(match.group(1))
    raise TimeoutError(bytes(output).decode(errors="replace"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command")
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    output, status = run(args.command, args.timeout)
    print(output)
    raise SystemExit(status)


if __name__ == "__main__":
    main()
