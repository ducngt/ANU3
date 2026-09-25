from __future__ import annotations

import secrets
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate an RFC 9562-compatible UUIDv7 using Unix epoch milliseconds."""
    ms = int(time.time() * 1000)
    if ms >= 1 << 48:
        raise OverflowError("timestamp does not fit UUIDv7")
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)


def urn(kind: str, identifier: str | uuid.UUID) -> str:
    return f"urn:anu:{kind}:{identifier}"
