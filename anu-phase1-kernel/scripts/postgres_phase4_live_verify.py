from __future__ import annotations

import argparse
import json
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.db import make_engine
from anu_kernel.work_models import WorkContractVersion, WorkGraphVersion, WorkExecutionPlanRecord, WorkInstanceRecord, WorkTaskRecord, WorkTransitionRecord, HandoverRecord
from anu_kernel.work_services import replay_work
from aru01_governed_work_pilot import run_pilot

ROOT = Path(__file__).resolve().parents[1]
BASELINE_REVISION = "0006"


def current_database_revision(database_url: str) -> str | None:
    engine = make_engine(database_url)
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def baseline_revision_is_ancestor(current_revision: str | None) -> bool:
    if not current_revision:
        return False
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    try:
        return any(r.revision == BASELINE_REVISION for r in script.iterate_revisions(current_revision, "base"))
    except Exception:
        return False


def restored_evidence(database_url: str, pilot: dict) -> dict:
    Session = sessionmaker(bind=make_engine(database_url), future=True)
    with Session() as session:
        counts = {
            "work_contracts": int(session.scalar(select(func.count()).select_from(WorkContractVersion)) or 0),
            "work_graphs": int(session.scalar(select(func.count()).select_from(WorkGraphVersion)) or 0),
            "plans": int(session.scalar(select(func.count()).select_from(WorkExecutionPlanRecord)) or 0),
            "work_instances": int(session.scalar(select(func.count()).select_from(WorkInstanceRecord)) or 0),
            "tasks": int(session.scalar(select(func.count()).select_from(WorkTaskRecord)) or 0),
            "transitions": int(session.scalar(select(func.count()).select_from(WorkTransitionRecord)) or 0),
            "handovers": int(session.scalar(select(func.count()).select_from(HandoverRecord)) or 0),
        }
        replays = {name: replay_work(session, pilot[name]["work_id"]).model_dump(mode="json") for name in ["e1", "e2", "e3"]}
    return {"counts": counts, "replays": replays}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", required=True)
    ap.add_argument("--restore-url", required=True)
    ap.add_argument("--backup", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    database_revision = current_database_revision(args.database_url)
    baseline_preserved = baseline_revision_is_ancestor(database_revision)
    pilot = run_pilot(args.database_url)
    backup = backup_database(args.database_url, args.backup)
    restore = restore_database(args.backup, args.restore_url)
    restored = restored_evidence(args.restore_url, pilot)
    c = restored["counts"]
    checks = {
        "baseline_revision_0006_in_history": baseline_preserved,
        "live_postgresql_e1_e2_e3_pilot": pilot["pass"],
        "live_postgresql_responsibility_replay": pilot["responsibility_replay_complete"],
        "live_postgresql_handover_fail_closed": pilot["e2"]["forbidden_agent_action"] == "HANDOVER_REQUIRED" and pilot["e3"]["agent_approval_attempt"] == "HANDOVER_REQUIRED",
        "live_postgresql_human_signature_e3": bool(pilot["e3"].get("human_signature_ref")),
        "live_postgresql_backup": backup["status"] == "PASS",
        "live_postgresql_restore": restore["status"] == "PASS",
        "restored_work_contracts": c["work_contracts"] >= 3,
        "restored_work_graphs": c["work_graphs"] >= 3,
        "restored_work_instances": c["work_instances"] >= 5,
        "restored_tasks": c["tasks"] >= 4,
        "restored_transitions": c["transitions"] >= 20,
        "restored_handovers": c["handovers"] >= 2,
        "restored_e1_e2_e3_replay": all(v["current_state"] == "CLOSED" and v["replay_complete"] for v in restored["replays"].values()),
    }
    result = {
        "work_id": "P4-GOVERNED-HUMAN-AI-WORK-RUNTIME",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "pilot": pilot,
        "restored": restored,
        "synthetic_data_only": True,
        "baseline_revision": BASELINE_REVISION,
        "database_revision": database_revision,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
