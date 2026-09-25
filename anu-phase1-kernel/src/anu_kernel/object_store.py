from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse


class ObjectStoreError(RuntimeError):
    pass


class FileSystemObjectStore:
    """Content-addressed immutable object-store adapter for pilot/reference use.

    Provider-specific filesystem logic is deliberately kept behind this adapter.
    Institutional references are sha256-addressed and stable regardless of the
    concrete filesystem root.
    """

    provider_ref = "urn:anu:adapter:object-store:filesystem"
    provider_version = "1.0.0"

    def __init__(self, root: str | Path | None = None):
        configured = root or os.getenv("ANU_OBJECT_STORE_ROOT", "./var/object-store")
        self.root = Path(configured).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def put(self, data: bytes) -> tuple[str, str, Path]:
        digest = self.sha256(data)
        target = self.root / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing = target.read_bytes()
            if self.sha256(existing) != digest:
                raise ObjectStoreError("content-address collision or tampered stored object")
        else:
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, target)
        return f"urn:anu:object:sha256:{digest}", digest, target

    def path_for_ref(self, storage_ref: str) -> Path:
        prefix = "urn:anu:object:sha256:"
        if not storage_ref.startswith(prefix):
            raise ObjectStoreError("unsupported storage_ref")
        digest = storage_ref[len(prefix):]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ObjectStoreError("invalid sha256 storage_ref")
        return self.root / digest[:2] / digest

    def read(self, storage_ref: str) -> bytes:
        path = self.path_for_ref(storage_ref)
        if not path.exists():
            raise FileNotFoundError(storage_ref)
        return path.read_bytes()

    def verify(self, storage_ref: str, expected_hash: str) -> tuple[str, str | None]:
        path = self.path_for_ref(storage_ref)
        if not path.exists():
            return "MISSING", None
        observed = self.sha256(path.read_bytes())
        return ("PASS" if observed == expected_hash else "FAIL"), observed
