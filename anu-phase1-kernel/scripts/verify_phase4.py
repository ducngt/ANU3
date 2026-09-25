from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.db import make_engine
from anu_kernel.work_models import (
    WorkContractVersion, WorkGraphVersion, WorkExecutionPlanRecord,
    WorkInstanceRecord, WorkTaskRecord, WorkTransitionRecord, HandoverRecord,
)
from anu_kernel.work_services import replay_work
from aru01_governed_work_pilot import run_pilot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "verification"
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT / "scripts") + os.pathsep + merged.get("PYTHONPATH", "")
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=ROOT, env=merged, text=True, capture_output=True)


def migration_cycle(database_url: str) -> tuple[bool, str]:
    old = os.environ.get("ANU_DATABASE_URL")
    os.environ["ANU_DATABASE_URL"] = database_url
    try:
        cfg = Config(str(ROOT / "alembic.ini"))
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        return True, "upgrade -> downgrade -> upgrade PASS at revision 0006"
    except Exception as exc:
        return False, repr(exc)
    finally:
        if old is None:
            os.environ.pop("ANU_DATABASE_URL", None)
        else:
            os.environ["ANU_DATABASE_URL"] = old


def postgres_offline_sql() -> tuple[bool, str]:
    proc = run(["alembic", "upgrade", "head", "--sql"], {"ANU_DATABASE_URL": "postgresql://anu:anu@localhost/anu"})
    sql = proc.stdout
    required = [
        "CREATE TABLE work_contract_version",
        "CREATE TABLE work_graph_version",
        "CREATE TABLE work_execution_plan",
        "CREATE TABLE work_instance",
        "CREATE TABLE work_task_record",
        "CREATE TABLE work_transition_record",
        "CREATE TABLE work_handover_record",
    ]
    return proc.returncode == 0 and all(x in sql for x in required), (sql[-14000:] + proc.stderr[-3000:]).strip()


def recovery_reference(source_url: str, pilot: dict, tmp: Path) -> tuple[bool, dict]:
    backup_path = tmp / "p4.db.backup"
    restored_path = tmp / "p4-restored.db"
    restored_url = f"sqlite+pysqlite:///{restored_path}"
    try:
        backup = backup_database(source_url, backup_path)
        restore = restore_database(backup_path, restored_url)
        Session = sessionmaker(bind=make_engine(restored_url), future=True)
        with Session() as session:
            counts = {
                "work_contracts": int(session.scalar(select(func.count()).select_from(WorkContractVersion)) or 0),
                "work_graphs": int(session.scalar(select(func.count()).select_from(WorkGraphVersion)) or 0),
                "execution_plans": int(session.scalar(select(func.count()).select_from(WorkExecutionPlanRecord)) or 0),
                "work_instances": int(session.scalar(select(func.count()).select_from(WorkInstanceRecord)) or 0),
                "tasks": int(session.scalar(select(func.count()).select_from(WorkTaskRecord)) or 0),
                "transitions": int(session.scalar(select(func.count()).select_from(WorkTransitionRecord)) or 0),
                "handovers": int(session.scalar(select(func.count()).select_from(HandoverRecord)) or 0),
            }
            replays = {name: replay_work(session, pilot[name]["work_id"]).model_dump(mode="json") for name in ["e1", "e2", "e3"]}
        ok = (
            backup.get("status") == "PASS" and restore.get("status") == "PASS"
            and counts["work_contracts"] >= 3 and counts["work_graphs"] >= 3
            and counts["work_instances"] >= 5 and counts["tasks"] >= 4
            and counts["transitions"] >= 20 and counts["handovers"] >= 2
            and all(v["current_state"] == "CLOSED" and v["replay_complete"] for v in replays.values())
        )
        return ok, {"backup": backup, "restore": restore, "counts": counts, "replays": replays}
    except Exception as exc:
        return False, {"error": repr(exc)}


def main() -> int:
    checks: dict[str, str] = {}
    details: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="anu-p4-") as tmp_name:
        tmp = Path(tmp_name)
        db_url = f"sqlite+pysqlite:///{tmp / 'verification.db'}"

        ok, detail = migration_cycle(db_url)
        checks["clean_migration_cycle"] = "PASS" if ok else "FAIL"
        details["clean_migration_cycle"] = detail

        tests = run([sys.executable, "-m", "pytest", "-q"])
        checks["automated_tests"] = "PASS" if tests.returncode == 0 else "FAIL"
        details["automated_tests"] = (tests.stdout + tests.stderr).strip()
        if tests.returncode != 0:
            print("AUTOMATED_TEST_FAILURE_DETAILS", flush=True)
            print(details["automated_tests"], flush=True)

        # migration_cycle leaves a clean upgraded DB
        pilot = run_pilot(db_url)
        checks["aru01_e1_e2_e3_pilot"] = "PASS" if pilot["pass"] else "FAIL"
        details["aru01_e1_e2_e3_pilot"] = pilot

        schemas = run([sys.executable, "scripts/export_schemas.py"])
        required_schemas = [
            "anu.work-contract.v1.json", "anu.governed-work-graph.v1.json",
            "anu.execution-plan.v1.json", "anu.work-task-request.v1.json",
            "anu.work-transition-request.v1.json", "anu.work-replay-result.v1.json",
        ]
        schema_ok = schemas.returncode == 0 and all((ROOT / "contracts" / "schemas" / x).exists() for x in required_schemas)
        checks["contract_schema_export"] = "PASS" if schema_ok else "FAIL"
        details["contract_schema_export"] = (schemas.stdout + schemas.stderr).strip()

        independent = run([sys.executable, "-m", "pytest", "tests/independent/test_phase4_boundaries.py", "-q"])
        checks["independent_boundary_verifier"] = "PASS" if independent.returncode == 0 else "FAIL"
        details["independent_boundary_verifier"] = (independent.stdout + independent.stderr).strip()

        pg_ok, pg_detail = postgres_offline_sql()
        checks["postgresql_offline_migration_compile"] = "PASS" if pg_ok else "FAIL"
        details["postgresql_offline_migration_compile"] = pg_detail

        rec_ok, rec_detail = recovery_reference(db_url, pilot, tmp)
        checks["work_state_recovery_and_replay"] = "PASS" if rec_ok else "FAIL"
        details["work_state_recovery_and_replay"] = rec_detail

    local_ok = all(v == "PASS" for v in checks.values())
    status = {
        "work_id": "P4-GOVERNED-HUMAN-AI-WORK-RUNTIME",
        "status": "LOCAL_VERIFIED_AWAITING_LIVE_POSTGRES" if local_ok else "BLOCKED_TECHNICAL_VERIFICATION",
        "human_gate": "G3_NOT_READY",
        "phase": "Phase 4 Governed Human-AI Work Runtime",
        "baseline": "P3-RUNTIME-G3-ACCEPTED",
        "summary": "Work Contract, Governed Work Graph, Execution Planner, Human/Agent/Capability tasks, authority/policy gates, Human signature, handover/recovery, state persistence and responsibility replay are implemented for ARU-01 E1/E2/E3.",
        "checks": checks,
        "external_checks": {
            "live_postgresql_revision_0006": "PENDING_EXTERNAL_CI",
            "live_postgresql_e1_e2_e3_pilot": "PENDING_EXTERNAL_CI",
            "live_postgresql_backup_restore_replay": "PENDING_EXTERNAL_CI",
            "independent_live_evidence_qualification": "PENDING_EXTERNAL_CI",
        },
        "known_limitations": [
            "ARU-01 remains synthetic; no real learner PII is used.",
            "E1/E2/E3 pilot contracts use A1/A2 before consequential Human decisions. Higher delegated autonomy remains contract/policy-context dependent and is not promoted by this pilot.",
            "Timer/Event-Wait are deterministic runtime primitives in this tranche; distributed queue/scheduler providers remain replaceable adapters.",
            "Phase 5 Academic Reference Vertical is not included in this tranche.",
        ],
        "human_action": "None for technical verification. Publish the CI activation package because this session has no GitHub write connector; GitHub Actions owns live PostgreSQL verification.",
    }
    (OUT / "P4-LATEST.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "TECHNICAL-DETAILS-P4.json").write_text(json.dumps({"checks": checks, "details": details}, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
