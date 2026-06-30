from __future__ import annotations

import socket
from typing import Any

from config.settings import RedisSettings


class RedisClientProvider:
    def __init__(self, settings: RedisSettings) -> None:
        self.settings = settings
        self._client: Any | None = None

    def client(self) -> Any:
        if self._client is None:
            try:
                import redis
            except ImportError as exc:
                raise RuntimeError("redis is not installed") from exc
            self._client = redis.Redis.from_url(self.settings.url, decode_responses=True)
        return self._client

    def set_value(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        try:
            result = self.client().set(key, value, ex=ex, nx=nx)
            return bool(result)
        except RuntimeError:
            command = ["SET", key, value]
            if ex is not None:
                command.extend(["EX", str(ex)])
            if nx:
                command.append("NX")
            result = self._raw_command(command)
            return result == "OK"

    def get_value(self, key: str) -> str | None:
        try:
            return self.client().get(key)
        except RuntimeError:
            result = self._raw_command(["GET", key])
            return None if result is None else str(result)

    def delete(self, key: str) -> int:
        try:
            return int(self.client().delete(key))
        except RuntimeError:
            result = self._raw_command(["DEL", key])
            return int(result or 0)

    def lpush(self, key: str, value: str) -> int:
        try:
            return int(self.client().lpush(key, value))
        except RuntimeError:
            result = self._raw_command(["LPUSH", key, value])
            return int(result or 0)

    def rpop(self, key: str) -> str | None:
        try:
            return self.client().rpop(key)
        except RuntimeError:
            result = self._raw_command(["RPOP", key])
            return None if result is None else str(result)

    def llen(self, key: str) -> int:
        try:
            return int(self.client().llen(key))
        except RuntimeError:
            result = self._raw_command(["LLEN", key])
            return int(result or 0)

    def status(self) -> dict[str, Any]:
        if not self.settings.enabled:
            return {"enabled": False, "status": "disabled"}
        try:
            self.get_value(f"{self.settings.key_prefix}:system:initialized")
            return {"enabled": True, "status": "configured", "url": self.settings.url}
        except RuntimeError as exc:
            return {"enabled": True, "status": "missing_dependency", "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"enabled": True, "status": "unavailable", "error": str(exc)}

    def _raw_command(self, command: list[str]) -> Any:
        host, port = self._parse_host_port()
        payload = self._encode_resp(command)
        with socket.create_connection((host, port), timeout=3) as sock:
            sock.sendall(payload)
            return self._read_resp(sock)

    def _parse_host_port(self) -> tuple[str, int]:
        # Supports the project's default redis://host:port/db form.
        raw = self.settings.url
        without_scheme = raw.split("://", 1)[-1]
        host_port = without_scheme.split("/", 1)[0]
        if "@" in host_port:
            host_port = host_port.split("@", 1)[1]
        host, port = host_port.split(":", 1)
        return host, int(port)

    def _encode_resp(self, values: list[str]) -> bytes:
        parts = [f"*{len(values)}\r\n".encode()]
        for value in values:
            encoded = str(value).encode()
            parts.append(f"${len(encoded)}\r\n".encode())
            parts.append(encoded + b"\r\n")
        return b"".join(parts)

    def _read_resp(self, sock: socket.socket) -> Any:
        prefix = sock.recv(1)
        if prefix == b"+":
            return self._read_line(sock)
        if prefix == b"-":
            raise RuntimeError(self._read_line(sock))
        if prefix == b":":
            return int(self._read_line(sock))
        if prefix == b"$":
            length = int(self._read_line(sock))
            if length == -1:
                return None
            data = self._read_exact(sock, length)
            self._read_exact(sock, 2)
            return data.decode()
        if prefix == b"*":
            count = int(self._read_line(sock))
            return [self._read_resp(sock) for _ in range(count)]
        raise RuntimeError("invalid redis response")

    def _read_line(self, sock: socket.socket) -> str:
        data = bytearray()
        while True:
            chunk = sock.recv(1)
            if not chunk:
                break
            data.extend(chunk)
            if data.endswith(b"\r\n"):
                break
        return bytes(data[:-2]).decode()

    def _read_exact(self, sock: socket.socket, length: int) -> bytes:
        data = bytearray()
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                raise RuntimeError("redis connection closed")
            data.extend(chunk)
        return bytes(data)
