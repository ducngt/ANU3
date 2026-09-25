from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from anu_kernel.db import Base, make_engine
import anu_kernel.reality_models  # register Phase 2 tables with shared metadata


@pytest.fixture()
def session():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        yield s
