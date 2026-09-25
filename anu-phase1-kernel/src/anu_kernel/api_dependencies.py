from __future__ import annotations

from .db import get_session_factory


def get_session():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
