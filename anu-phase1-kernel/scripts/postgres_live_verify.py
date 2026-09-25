from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.db import DecisionRecord, make_engine
from aru01_trust_pilot import run_trust_pilot


def count_decisions(database_url: str) -> int:
    engine = make_engine(database_url)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        return int(session.scalar(select(func.count()).select_from(DecisionRecord)) or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--restore-url", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    pilot = run_trust_pilot(args.database_url)
    backup = backup_database(args.database_url, args.backup)
    restore = restore_database(args.backup, args.restore_url)
    restored_decisions = count_decisions(args.restore_url)
    checks = {
        "live_postgresql_aru01_trust_pilot": pilot["pass"],
        "live_postgresql_backup": backup["status"] == "PASS",
        "live_postgresql_restore": restore["status"] == "PASS",
        "restored_institutional_history_present": restored_decisions >= 1,
    }
    result = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "restored_decision_count": restored_decisions,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
