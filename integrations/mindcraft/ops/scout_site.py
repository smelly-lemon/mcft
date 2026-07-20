"""Scout a build site near world spawn via RCON terrain probes.

Bisects ground height per column with `execute if block ... air`, scores a
ring of candidate centers on flatness (3x3 columns, 12-block pitch), rejects
water, and prints candidates sorted best-first. Used at era resets; the
winner goes to soft_reset.py --site and make_profiles.py --site.
"""

from __future__ import annotations

import socket
import struct
from pathlib import Path

SERVER = Path.home() / "Desktop" / "mc-bot-server"


class Rcon:
    def __init__(self) -> None:
        props = {}
        for line in (SERVER / "server.properties").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                props[k] = v
        self.sock = socket.create_connection(("localhost", int(props["rcon.port"])), timeout=8)
        self._send(3, props["rcon.password"])

    def _send(self, kind: int, body: str) -> str:
        payload = struct.pack("<ii", 0, kind) + body.encode() + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(payload)) + payload)
        length = struct.unpack("<i", self.sock.recv(4))[0]
        data = b""
        while len(data) < length:
            data += self.sock.recv(length - len(data))
        return data[8:-2].decode(errors="replace")

    def cmd(self, body: str) -> str:
        return self._send(2, body)


def main() -> None:
    rcon = Rcon()

    def is_block(x: int, y: int, z: int, block: str) -> bool:
        return "passed" in rcon.cmd(f"execute if block {x} {y} {z} minecraft:{block}")

    def ground(x: int, z: int) -> int:
        lo, hi = 40, 160
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if is_block(x, mid, z, "air"):
                hi = mid
            else:
                lo = mid
        return lo

    centers = [
        (0, 0), (64, 0), (96, 32), (64, 64), (0, 64), (-64, 64), (-64, 0),
        (-64, -64), (0, -96), (64, -64), (128, 0), (96, 96), (0, 128), (-128, 0),
    ]
    results = []
    for cx, cz in centers:
        # ungenerated chunks answer every if-block with a failure, which reads
        # as solid-to-the-sky; forceload generates + loads them for the probe.
        rcon.cmd(f"forceload add {cx - 16} {cz - 16} {cx + 16} {cz + 16}")
        ys = [ground(cx + dx, cz + dz) for dx in (-12, 0, 12) for dz in (-12, 0, 12)]
        lo, hi = min(ys), max(ys)
        center_y = ys[4]
        water = is_block(cx, center_y, cz, "water") or is_block(cx, lo, cz, "water")
        results.append((hi - lo, water, cx, center_y, cz))
        tag = " WATER" if water else ""
        print(f"({cx:5d},{cz:5d}) Y {lo}-{hi} spread={hi - lo}{tag}")
    rcon.cmd("forceload remove all")

    results.sort(key=lambda r: (r[1], r[0]))
    best = results[0]
    print(f"\nBEST: site {best[2]},{best[3] + 1},{best[4]} (spread {best[0]}, water={best[1]})")


if __name__ == "__main__":
    main()
