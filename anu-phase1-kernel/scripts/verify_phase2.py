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
from anu_kernel.reality_models import DataObjectVersion, UniversityMemoryRecord
from anu_kernel.reality_services import project_data
from anu_kernel.reality_contracts import DataProjectionRequest
from aru01_reality_pilot import dt, run_pilot

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "verification"
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT) + os.pathsep + merged.get("PYTHONPATH", "")
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
        return True, "upgrade -> downgrade -> upgrade PASS at revision 0003"
    except Exception as exc:
        return False, repr(exc)
    finally:
        if old is None:
            os.environ.pop("ANU_DATABASE_URL", None)
        else:
            os.environ["ANU_DATABASE_URL"] = old


def postgres_offline_sql() -> tuple[bool, str]:
    proc = run(
        ["alembic", "upgrade", "head", "--sql"],
        {"ANU_DATABASE_URL": "postgresql://anu:anu@localhost/anu"},
    )
    sql = proc.stdout
    required = [
        "CREATE TABLE source_registry",
        "CREATE TABLE source_authority_mapping",
        "CREATE TABLE data_contract_version",
        "CREATE TABLE data_object_version",
        "CREATE TABLE knowledge_object_version",
        "CREATE TABLE university_memory_record",
    ]
    ok = proc.returncode == 0 and all(fragment in sql for fragment in required)
    return ok, (sql[-6000:] + proc.stderr[-2000:]).strip()


def backup_restore_reference(source_url: str, tmp: Path) -> tuple[bool, dict]:
    backup_path = tmp / "p2-backup.db"
    restored_path = tmp / "p2-restored.db"
    restored_url = f"sqlite+pysqlite:///{restored_path}"
    try:
        backup = backup_database(source_url, backup_path)
        restore = restore_database(backup_path, restored_url)
        engine = make_engine(restored_url)
        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            data_count = int(session.scalar(select(func.count()).select_from(DataObjectVersion)) or 0)
            memory_count = int(session.scalar(select(func.count()).select_from(UniversityMemoryRecord)) or 0)
            projection = project_data(
                session,
                DataProjectionRequest(
                    data_id="urn:anu:data:programme:software-engineering",
                    effective_at=dt("2026-06-01T00:00:00Z"),
                ),
            )
        ok = data_count >= 4 and memory_count >= 1 and projection.payload.get("version") == "1.0"
        return ok, {
            "backup": backup,
            "restore": restore,
            "data_versions_after_restore": data_count,
            "memory_records_after_restore": memory_count,
            "historical_projection_after_restore": projection.model_dump(mode="json"),
        }
    except Exception as exc:
        return False, {"error": repr(exc)}


def main() -> int:
    checks: dict[str, str] = {}
    details: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="anu-p2-t01-") as tmp_name:
        tmp = Path(tmp_name)
        db_path = tmp / "verification.db"
        db_url = f"sqlite+pysqlite:///{db_path}"

        ok, detail = migration_cycle(db_url)
        checks["clean_migration_cycle"] = "PASS" if ok else "FAIL"
        details["clean_migration_cycle"] = detail

        tests = run([sys.executable, "-m", "pytest", "-q"])
        checks["automated_tests"] = "PASS" if tests.returncode == 0 else "FAIL"
        details["automated_tests"] = (tests.stdout + tests.stderr).strip()

        pilot = run_pilot(db_url)
        checks["aru01_reality_data_memory_pilot"] = "PASS" if pilot["pass"] else "FAIL"
        details["aru01_reality_data_memory_pilot"] = pilot

        schemas = run([sys.executable, "scripts/export_schemas.py"])
        checks["contract_schema_export"] = "PASS" if schemas.returncode == 0 else "FAIL"
        details["contract_schema_export"] = (schemas.stdout + schemas.stderr).strip()

        pg_ok, pg_detail = postgres_offline_sql()
        checks["postgresql_offline_migration_compile"] = "PASS" if pg_ok else "FAIL"
        details["postgresql_offline_migration_compile"] = pg_detail

        br_ok, br_detail = backup_restore_reference(db_url, tmp)
        checks["backup_restore_reference"] = "PASS" if br_ok else "FAIL"
        details["backup_restore_reference"] = br_detail

    local_ok = all(v == "PASS" for v in checks.values())
    status = {
        "work_id": "P2-T01-REALITY-DATA-MEMORY",
        "status": "LOCAL_VERIFIED_AWAITING_LIVE_POSTGRES" if local_ok else "BLOCKED_TECHNICAL_VERIFICATION",
        "human_gate": "G3_NOT_READY",
        "phase": 2,
        "baseline": "P1-T03-G3-ACCEPTED-G4-PILOT",
        "summary": (
            "Phase 2 Tranche 01 is implemented and locally verified with ARU-01 synthetic institutional data. Live PostgreSQL evidence is the remaining technical gate before Human G3."
            if local_ok else
            "Phase 2 Tranche 01 has technical verification failures. Human action is not required until AI clears them."
        ),
        "checks": checks,
        "external_checks": {
            "live_postgresql_phase2_migration": "PENDING_EXTERNAL_CI",
            "live_postgresql_aru01_reality_pilot": "PENDING_EXTERNAL_CI",
            "live_postgresql_phase2_backup_restore": "PENDING_EXTERNAL_CI",
        },
        "known_limitations": [
            "ARU-01 data is synthetic by Human-approved G0/G1; no real learner PII is used.",
            "Search/retrieval is a baseline lexical in-process implementation, not a production search/vector provider.",
            "Object/document ingestion registers institutional metadata and integrity references; binary object storage/provider adapters remain outside this tranche.",
            "Source authority is scoped through registered mappings; connecting a real SIS/LMS/HR source requires a new G2 privacy/retention/access decision.",
        ],
        "human_action": "None until live PostgreSQL CI evidence is attached. AI/CI owns the remaining technical verification.",
    }
    (OUT / "P2-LATEST.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "TECHNICAL-DETAILS-P2-T01.json").write_text(
        json.dumps({"checks": checks, "details": details}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
