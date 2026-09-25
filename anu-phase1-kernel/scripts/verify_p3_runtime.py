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
from anu_kernel.sbbs_runtime_contracts import AssemblyExecutionRequest
from anu_kernel.sbbs_runtime_models import (
    AdapterVersion,
    AssemblyVersion,
    CompatibilityEvidence,
    ConnectionPlanVersion,
    TransformVersion,
    WireExecutionRecord,
    WriteBoxCandidate,
)
from anu_kernel.sbbs_runtime_services import execute_assembly
from aru01_sbbs_runtime_pilot import run_pilot

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
        return True, "upgrade -> downgrade -> upgrade PASS at current repository head with P3 baseline preserved"
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
        "CREATE TABLE transform_version",
        "CREATE TABLE adapter_version",
        "CREATE TABLE compatibility_evidence",
        "CREATE TABLE connection_plan_version",
        "CREATE TABLE assembly_version",
        "CREATE TABLE write_box_candidate",
    ]
    ok = proc.returncode == 0 and all(fragment in sql for fragment in required)
    return ok, (sql[-10000:] + proc.stderr[-2000:]).strip()


def recovery_reference(source_url: str, pilot: dict, tmp: Path) -> tuple[bool, dict]:
    backup_path = tmp / "p3-runtime.db.backup"
    restored_path = tmp / "p3-runtime-restored.db"
    restored_url = f"sqlite+pysqlite:///{restored_path}"
    try:
        backup = backup_database(source_url, backup_path)
        restore = restore_database(backup_path, restored_url)
        Session = sessionmaker(bind=make_engine(restored_url), future=True)
        with Session() as session:
            counts = {
                "compatibility_evidence": int(session.scalar(select(func.count()).select_from(CompatibilityEvidence)) or 0),
                "connection_plans": int(session.scalar(select(func.count()).select_from(ConnectionPlanVersion)) or 0),
                "assemblies": int(session.scalar(select(func.count()).select_from(AssemblyVersion)) or 0),
                "wire_executions": int(session.scalar(select(func.count()).select_from(WireExecutionRecord)) or 0),
                "write_box_candidates": int(session.scalar(select(func.count()).select_from(WriteBoxCandidate)) or 0),
                "transforms": int(session.scalar(select(func.count()).select_from(TransformVersion)) or 0),
                "adapters": int(session.scalar(select(func.count()).select_from(AdapterVersion)) or 0),
            }
            replay = execute_assembly(session, AssemblyExecutionRequest(
                assembly_ref=pilot["assembly_refs"][0],
                input_payload={"programme_code": "BSC-CS", "title": "Computer Science"},
                trace_id="restored-replay",
            ))
        ok = (
            backup.get("status") == "PASS"
            and restore.get("status") == "PASS"
            and counts["compatibility_evidence"] >= 2
            and counts["connection_plans"] >= 2
            and counts["assemblies"] >= 2
            and counts["wire_executions"] >= 2
            and counts["write_box_candidates"] >= 1
            and counts["transforms"] >= 1
            and counts["adapters"] >= 1
            and replay.status == "SUCCEEDED"
            and replay.final_payload == {"programme_id": "BSC-CS", "summary": "Computer Science"}
        )
        return ok, {"backup": backup, "restore": restore, "counts": counts, "restored_assembly_replay": replay.model_dump(mode="json")}
    except Exception as exc:
        return False, {"error": repr(exc)}


def main() -> int:
    checks: dict[str, str] = {}
    details: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="anu-p3-runtime-") as tmp_name:
        tmp = Path(tmp_name)
        db_url = f"sqlite+pysqlite:///{tmp / 'verification.db'}"

        ok, detail = migration_cycle(db_url)
        checks["clean_migration_cycle"] = "PASS" if ok else "FAIL"
        details["clean_migration_cycle"] = detail

        tests = run([sys.executable, "-m", "pytest", "-q"])
        checks["automated_tests"] = "PASS" if tests.returncode == 0 else "FAIL"
        details["automated_tests"] = (tests.stdout + tests.stderr).strip()

        pilot = run_pilot(db_url)
        checks["aru01_sbbs_runtime_pilot"] = "PASS" if pilot["pass"] else "FAIL"
        details["aru01_sbbs_runtime_pilot"] = pilot

        schemas = run([sys.executable, "scripts/export_schemas.py"])
        p3_schema_names = ["anu.compatibility-result.v1.json","anu.connection-plan.v1.json","anu.smart-wire-execution-result.v1.json","anu.assembly-definition.v1.json","anu.write-box-proposal-result.v1.json"]
        checks["contract_schema_export"] = "PASS" if schemas.returncode == 0 and all((ROOT / "contracts" / "schemas" / n).exists() for n in p3_schema_names) else "FAIL"
        details["contract_schema_export"] = (schemas.stdout + schemas.stderr).strip()

        independent = run([sys.executable, "-m", "pytest", "tests/independent/test_p3_runtime_boundaries.py", "-q"])
        checks["independent_boundary_verifier"] = "PASS" if independent.returncode == 0 else "FAIL"
        details["independent_boundary_verifier"] = (independent.stdout + independent.stderr).strip()

        pg_ok, pg_detail = postgres_offline_sql()
        checks["postgresql_offline_migration_compile"] = "PASS" if pg_ok else "FAIL"
        details["postgresql_offline_migration_compile"] = pg_detail

        rec_ok, rec_detail = recovery_reference(db_url, pilot, tmp)
        checks["runtime_recovery_and_replay"] = "PASS" if rec_ok else "FAIL"
        details["runtime_recovery_and_replay"] = rec_detail

    local_ok = all(v == "PASS" for v in checks.values())
    status = {
        "work_id": "P3-02-P3-07-SBBS-CAPABILITY-RUNTIME",
        "status": "LOCAL_VERIFIED_AWAITING_LIVE_POSTGRES" if local_ok else "BLOCKED_TECHNICAL_VERIFICATION",
        "human_gate": "G3_NOT_READY",
        "phase": "P3-02 Compatibility through P3-07 Write Box Studio MVP",
        "baseline": "P2-T02-P3-01-G3-ACCEPTED",
        "summary": "SBBS Capability Runtime is locally implemented and verified: compatibility, adapter/transform registry, declarative connection planning, thin Smart Wire, Assembly runtime, Write Box Studio MVP and architecture audit.",
        "checks": checks,
        "external_checks": {
            "live_postgresql_baseline_0005_preserved": "PENDING_EXTERNAL_CI",
            "live_postgresql_sbbs_runtime_pilot": "PENDING_EXTERNAL_CI",
            "live_postgresql_backup_restore_replay": "PENDING_EXTERNAL_CI",
            "independent_live_evidence_qualification": "PENDING_EXTERNAL_CI",
        },
        "known_limitations": [
            "ARU-01 remains synthetic and no real learner PII is used.",
            "Smart Wire MVP supports registered declarative transforms/adapters and approved handler boundaries; distributed transport providers remain adapter extensions.",
            "Write Box Studio MVP governs candidate packaging/audit/promotion; it does not autonomously grant authority or modify Constitutional Core.",
            "Phase 4 Governed Human-AI Work Runtime is not included in this tranche.",
        ],
        "human_action": "None for technical verification. Publish the CI activation package because this session has no GitHub write connector; GitHub Actions owns live PostgreSQL verification.",
    }
    (OUT / "P3-RUNTIME-LATEST.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "TECHNICAL-DETAILS-P3-RUNTIME.json").write_text(json.dumps({"checks": checks, "details": details}, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
