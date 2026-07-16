"""Rescue a stuck bot: teleport it to open ground near its current position.

Operator tool (ADR-0006 spirit: out-of-band control that never touches the
bot process). Uses the Paper server's RCON; reads credentials from
server.properties. Run on the Studio:

    python3 rescue.py Sable
    python3 rescue.py Sable Jolt --radius 8
"""

from __future__ import annotations

import argparse
import re
import socket
import struct
from pathlib import Path

SERVER_PROPERTIES = Path.home() / "Desktop" / "mc-bot-server" / "server.properties"


class Rcon:
    def __init__(self, host: str, port: int, password: str) -> None:
        self._sock = socket.create_connection((host, port), timeout=5)
        self._req_id = 0
        if self._send(3, password)[0] == -1:
            raise SystemExit("RCON auth failed")

    def command(self, cmd: str) -> str:
        return self._send(2, cmd)[1]

    def _send(self, ptype: int, payload: str) -> tuple[int, str]:
        self._req_id += 1
        data = struct.pack("<ii", self._req_id, ptype) + payload.encode() + b"\x00\x00"
        self._sock.send(struct.pack("<i", len(data)) + data)
        length = struct.unpack("<i", self._sock.recv(4))[0]
        resp = b""
        while len(resp) < length:
            resp += self._sock.recv(length - len(resp))
        rid = struct.unpack("<i", resp[:4])[0]
        return rid, resp[8:-2].decode(errors="replace")


def read_rcon_config() -> tuple[int, str]:
    text = SERVER_PROPERTIES.read_text(encoding="utf-8")
    port = int(re.search(r"^rcon\.port=(\d+)", text, re.M).group(1))
    password = re.search(r"^rcon\.password=(.+)$", text, re.M).group(1).strip()
    return port, password


def main() -> None:
    parser = argparse.ArgumentParser(description="Teleport stuck bots to open ground")
    parser.add_argument("bots", nargs="+", help="bot player names, e.g. Sable Jolt")
    parser.add_argument("--radius", type=int, default=6, help="max spread distance")
    args = parser.parse_args()

    port, password = read_rcon_config()
    rcon = Rcon("127.0.0.1", port, password)
    for bot in args.bots:
        pos = rcon.command(f"data get entity {bot} Pos")
        # spreadplayers relocates to the highest solid block near the bot's x/z
        out = rcon.command(
            f"execute as {bot} at @s run spreadplayers ~ ~ 0 {args.radius} false @s"
        )
        print(f"{bot}: was {pos.split(':', 1)[-1].strip()} -> {out}")


if __name__ == "__main__":
    main()
