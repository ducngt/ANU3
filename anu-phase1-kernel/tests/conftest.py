from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from anu_kernel.db import Base, make_engine
import anu_kernel.reality_models  # register Phase 2 tables with shared metadata
import anu_kernel.ingestion_models  # register P2-T02 tables
import anu_kernel.capability_models  # register P3 contract/registry tables
import anu_kernel.sbbs_runtime_models  # register P3 runtime tables
import anu_kernel.work_models  # register P4 governed work tables


@pytest.fixture()
def session():
    engine = make_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        yield s
