from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.contracts import EffectivePeriod, IdentityContract, SubjectType
from anu_kernel.db import Base, IdentityRecord, make_engine
from anu_kernel.repository import add_identity


def dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_sqlite_backup_restore_preserves_institutional_identity(tmp_path: Path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    source_url = f"sqlite+pysqlite:///{source}"
    restored_url = f"sqlite+pysqlite:///{restored}"
    engine = make_engine(source_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        add_identity(session, IdentityContract(
            identity_id="urn:anu:identity:human:backup-test",
            subject_id="urn:anu:human:backup-test",
            subject_type=SubjectType.HUMAN,
            effective_period=EffectivePeriod(valid_from=dt("2026-01-01T00:00:00Z")),
        ))
    backup_database(source_url, backup)
    restore_database(backup, restored_url)
    restored_engine = make_engine(restored_url)
    RestoredSession = sessionmaker(bind=restored_engine, future=True)
    with RestoredSession() as session:
        row = session.scalar(select(IdentityRecord).where(IdentityRecord.identity_id == "urn:anu:identity:human:backup-test"))
        assert row is not None
        assert row.subject_id == "urn:anu:human:backup-test"
