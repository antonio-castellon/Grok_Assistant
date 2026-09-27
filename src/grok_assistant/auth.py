"""Administrator password. Only a salted hash is stored. There is no default."""

from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path


class AdminAuth:
    def __init__(self, path: Path):
        self.path = path
        self._salt: bytes | None = None
        self._hash: bytes | None = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._salt = bytes.fromhex(data["salt"])
            self._hash = bytes.fromhex(data["hash"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            self._salt = None
            self._hash = None

    @property
    def is_set(self) -> bool:
        return self._hash is not None and self._salt is not None

    def set_password(self, password: str) -> None:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"salt": salt.hex(), "hash": digest.hex()}),
            encoding="utf-8",
        )
        self._salt = salt
        self._hash = digest

    def verify(self, password: str) -> bool:
        if not self.is_set or self._salt is None or self._hash is None:
            return False
        digest = hashlib.scrypt(password.encode("utf-8"), salt=self._salt, n=2**14, r=8, p=1)
        return secrets.compare_digest(digest, self._hash)
