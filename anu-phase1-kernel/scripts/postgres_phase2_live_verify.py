from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.db import make_engine
from anu_kernel.reality_models import DataObjectVersion, UniversityMemoryRecord
from anu_kernel.reality_contracts import DataProjectionRequest
from anu_kernel.reality_services import project_data
from aru01_reality_pilot import dt, run_pilot


def restored_evidence(database_url: str) -> dict:
    Session = sessionmaker(bind=make_engine(database_url), future=True)
    with Session() as session:
        data_count = int(session.scalar(select(func.count()).select_from(DataObjectVersion)) or 0)
        memory_count = int(session.scalar(select(func.count()).select_from(UniversityMemoryRecord)) or 0)
        old = project_data(
            session,
            DataProjectionRequest(
                data_id="urn:anu:data:programme:software-engineering",
                effective_at=dt("2026-06-01T00:00:00Z"),
            ),
        )
    return {
        "data_versions": data_count,
        "memory_records": memory_count,
        "historical_programme_version": old.payload.get("version"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--restore-url", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pilot = run_pilot(args.database_url)
    backup = backup_database(args.database_url, args.backup)
    restore = restore_database(args.backup, args.restore_url)
    restored = restored_evidence(args.restore_url)
    checks = {
        "live_postgresql_aru01_reality_pilot": pilot["pass"],
        "live_postgresql_backup": backup["status"] == "PASS",
        "live_postgresql_restore": restore["status"] == "PASS",
        "restored_data_history_present": restored["data_versions"] >= 4,
        "restored_university_memory_present": restored["memory_records"] >= 1,
        "restored_historical_projection_replays_v1": restored["historical_programme_version"] == "1.0",
    }
    result = {
        "work_id": "P2-T01-REALITY-DATA-MEMORY",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "restored": restored,
        "synthetic_data_only": True,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
