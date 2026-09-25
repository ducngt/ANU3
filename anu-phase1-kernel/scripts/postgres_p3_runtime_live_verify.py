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
BASELINE_REVISION = "0005"

def current_database_revision(database_url: str) -> str | None:
    engine = make_engine(database_url)
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()

def baseline_revision_is_ancestor(current_revision: str | None) -> bool:
    if not current_revision:
        return False
    cfg = Config(str(ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    try:
        return any(r.revision == BASELINE_REVISION for r in script.iterate_revisions(current_revision, "base"))
    except Exception:
        return False


def restored_evidence(database_url: str, pilot: dict) -> dict:
    Session = sessionmaker(bind=make_engine(database_url), future=True)
    with Session() as session:
        counts = {
            "transforms": int(session.scalar(select(func.count()).select_from(TransformVersion)) or 0),
            "adapters": int(session.scalar(select(func.count()).select_from(AdapterVersion)) or 0),
            "compatibility_evidence": int(session.scalar(select(func.count()).select_from(CompatibilityEvidence)) or 0),
            "connection_plans": int(session.scalar(select(func.count()).select_from(ConnectionPlanVersion)) or 0),
            "assemblies": int(session.scalar(select(func.count()).select_from(AssemblyVersion)) or 0),
            "wire_executions": int(session.scalar(select(func.count()).select_from(WireExecutionRecord)) or 0),
            "write_box_candidates": int(session.scalar(select(func.count()).select_from(WriteBoxCandidate)) or 0),
        }
        replay = execute_assembly(session, AssemblyExecutionRequest(
            assembly_ref=pilot["assembly_refs"][0],
            input_payload={"programme_code": "BSC-CS", "title": "Computer Science"},
            trace_id="postgres-restored-replay",
        ))
    return {"counts": counts, "restored_assembly_replay": replay.model_dump(mode="json")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--restore-url", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database_revision = current_database_revision(args.database_url)
    baseline_preserved = baseline_revision_is_ancestor(database_revision)
    pilot = run_pilot(args.database_url)
    backup = backup_database(args.database_url, args.backup)
    restore = restore_database(args.backup, args.restore_url)
    restored = restored_evidence(args.restore_url, pilot)
    c = restored["counts"]
    checks = {
        "baseline_revision_0005_in_history": baseline_preserved,
        "live_postgresql_sbbs_runtime_pilot": pilot["pass"],
        "live_postgresql_write_box_audit_promotion": pilot["architecture_audit_pass"] and bool(pilot["promoted_capability_ref"]),
        "live_postgresql_provider_replacement": pilot["provider_replacement_preserved_contract"],
        "live_postgresql_transform_registry": bool(pilot["legacy_transform_refs"]),
        "live_postgresql_adapter_registry": bool(pilot["legacy_adapter_refs"]),
        "live_postgresql_backup": backup["status"] == "PASS",
        "live_postgresql_restore": restore["status"] == "PASS",
        "restored_transform_registry": c["transforms"] >= 1,
        "restored_adapter_registry": c["adapters"] >= 1,
        "restored_compatibility_evidence": c["compatibility_evidence"] >= 3,
        "restored_connection_plans": c["connection_plans"] >= 3,
        "restored_assemblies": c["assemblies"] >= 2,
        "restored_write_box_candidate": c["write_box_candidates"] >= 1,
        "restored_assembly_replay": restored["restored_assembly_replay"]["status"] == "SUCCEEDED" and restored["restored_assembly_replay"]["final_payload"] == {"programme_id":"BSC-CS","summary":"Computer Science"},
    }
    result = {
        "work_id": "P3-02-P3-07-SBBS-CAPABILITY-RUNTIME",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "pilot": pilot,
        "restored": restored,
        "synthetic_data_only": True,
        "baseline_revision": BASELINE_REVISION,
        "database_revision": database_revision,
        "compatibility_rule": "accepted P3 baseline remains valid under additive later Alembic heads",
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
