"""Minimal RCON client (Source protocol as spoken by Minecraft servers).

The fourth reimplementation of this snippet finally promoted to a module -
rescue.py, scout_site.py, and the ops one-liners can migrate at leisure.
"""

from __future__ import annotations

import socket
import struct
from pathlib import Path


class Rcon:
    def __init__(self, host: str, port: int, password: str, timeout: float = 8.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self._req_id = 0
        resp_id = self._send(3, password)
        if resp_id == -1:
            raise PermissionError("RCON auth failed")

    @classmethod
    def from_server_dir(cls, server_dir: str | Path, host: str = "localhost") -> Rcon:
        props: dict[str, str] = {}
        for line in (Path(server_dir) / "server.properties").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                props[key] = value
        return cls(host, int(props["rcon.port"]), props["rcon.password"])

    def _send(self, kind: int, body: str) -> int:
        self._req_id += 1
        payload = struct.pack("<ii", self._req_id, kind) + body.encode() + b"\x00\x00"
        self.sock.sendall(struct.pack("<i", len(payload)) + payload)
        length = struct.unpack("<i", self._recv_exact(4))[0]
        data = self._recv_exact(length)
        resp_id = struct.unpack("<i", data[:4])[0]
        self._last_body = data[8:-2].decode(errors="replace")
        return resp_id

    def _recv_exact(self, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("RCON connection closed")
            data += chunk
        return data

    def cmd(self, command: str) -> str:
        self._send(2, command)
        return self._last_body

    def close(self) -> None:
        self.sock.close()
