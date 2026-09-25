from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)
INDEX_VERSION = "anu-hash-vector-v1"
VECTOR_DIMS = 128


def tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def lexical_score(query: str, document: str) -> float:
    q = Counter(tokens(query))
    d = Counter(tokens(document))
    if not q or not d:
        return 0.0
    overlap = sum(min(count, d[token]) for token, count in q.items())
    return overlap / max(1, sum(q.values()))


def vectorize(text: str) -> list[float]:
    vec = [0.0] * VECTOR_DIMS
    toks = tokens(text)
    if not toks:
        return vec
    for token in toks:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        raw = int.from_bytes(digest, "big")
        index = raw % VECTOR_DIMS
        sign = -1.0 if ((raw >> 8) & 1) else 1.0
        vec[index] += sign
    norm = math.sqrt(sum(value * value for value in vec))
    if norm:
        vec = [value / norm for value in vec]
    return vec


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    score = sum(x * y for x, y in zip(a, b))
    return max(0.0, min(1.0, score))
