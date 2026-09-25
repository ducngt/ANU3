from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from anu_kernel.backup import backup_database, restore_database
from anu_kernel.capability_contracts import CapabilityDiscoveryQuery
from anu_kernel.capability_models import CapabilityVersion, SmartBoxManifestVersion
from anu_kernel.capability_services import discover_capabilities
from anu_kernel.db import make_engine
from anu_kernel.ingestion_contracts import RetrievalMode, RetrievalQuery
from anu_kernel.ingestion_models import ArtifactObjectVersion, RetrievalProjection
from anu_kernel.ingestion_services import retrieve, verify_artifact_integrity
from anu_kernel.object_store import FileSystemObjectStore
from anu_kernel.reality_models import KnowledgeObjectVersion, UniversityMemoryRecord
from aru01_multimodal_capability_pilot import run_pilot

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
        return True, "upgrade -> downgrade -> upgrade PASS at revision 0004"
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
        "CREATE TABLE artifact_object_version",
        "CREATE TABLE retrieval_projection",
        "CREATE TABLE capability_version",
        "CREATE TABLE smart_box_manifest_version",
    ]
    ok = proc.returncode == 0 and all(fragment in sql for fragment in required)
    return ok, (sql[-8000:] + proc.stderr[-2000:]).strip()


def recovery_reference(source_url: str, object_root: Path, tmp: Path) -> tuple[bool, dict]:
    backup_path = tmp / "p2t02.db.backup"
    restored_path = tmp / "p2t02-restored.db"
    restored_url = f"sqlite+pysqlite:///{restored_path}"
    object_backup = tmp / "object-store-backup"
    restored_objects = tmp / "object-store-restored"
    try:
        backup = backup_database(source_url, backup_path)
        shutil.copytree(object_root, object_backup)
        restore = restore_database(backup_path, restored_url)
        shutil.copytree(object_backup, restored_objects)
        engine = make_engine(restored_url)
        Session = sessionmaker(bind=engine, future=True)
        with Session() as session:
            counts = {
                "artifacts": int(session.scalar(select(func.count()).select_from(ArtifactObjectVersion)) or 0),
                "knowledge": int(session.scalar(select(func.count()).select_from(KnowledgeObjectVersion)) or 0),
                "memory": int(session.scalar(select(func.count()).select_from(UniversityMemoryRecord)) or 0),
                "retrieval": int(session.scalar(select(func.count()).select_from(RetrievalProjection)) or 0),
                "capabilities": int(session.scalar(select(func.count()).select_from(CapabilityVersion)) or 0),
                "boxes": int(session.scalar(select(func.count()).select_from(SmartBoxManifestVersion)) or 0),
            }
            integrity = verify_artifact_integrity(
                session,
                "urn:anu:artifact-version:aru-p2t02:1:v1",
                store=FileSystemObjectStore(restored_objects),
            )
            retrieval = retrieve(session, RetrievalQuery(query="responsible AI systems", mode=RetrievalMode.HYBRID))
            discovery = discover_capabilities(session, CapabilityDiscoveryQuery(operation_id="knowledge.retrieve"))
        ok = (
            counts["artifacts"] >= 5
            and counts["knowledge"] >= 1
            and counts["memory"] >= 6
            and counts["capabilities"] >= 1
            and counts["boxes"] >= 2
            and integrity.integrity_state == "PASS"
            and bool(retrieval.hits and retrieval.hits[0].provenance_ref)
            and bool(discovery.hits and len(discovery.hits[0].box_refs) >= 2)
        )
        return ok, {
            "database_backup": backup,
            "database_restore": restore,
            "object_store_backup": str(object_backup),
            "object_store_restore": str(restored_objects),
            "counts_after_restore": counts,
            "artifact_integrity_after_restore": integrity.model_dump(mode="json"),
            "retrieval_after_restore": retrieval.model_dump(mode="json"),
            "capability_discovery_after_restore": discovery.model_dump(mode="json"),
        }
    except Exception as exc:
        return False, {"error": repr(exc)}


def main() -> int:
    checks: dict[str, str] = {}
    details: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="anu-p2t02-p3-") as tmp_name:
        tmp = Path(tmp_name)
        db_path = tmp / "verification.db"
        db_url = f"sqlite+pysqlite:///{db_path}"
        object_root = tmp / "objects"

        ok, detail = migration_cycle(db_url)
        checks["clean_migration_cycle"] = "PASS" if ok else "FAIL"
        details["clean_migration_cycle"] = detail

        tests = run([sys.executable, "-m", "pytest", "-q"])
        checks["automated_tests"] = "PASS" if tests.returncode == 0 else "FAIL"
        details["automated_tests"] = (tests.stdout + tests.stderr).strip()

        pilot = run_pilot(db_url, object_root)
        checks["aru01_multimodal_capability_pilot"] = "PASS" if pilot["pass"] else "FAIL"
        details["aru01_multimodal_capability_pilot"] = pilot

        schemas = run([sys.executable, "scripts/export_schemas.py"])
        checks["contract_schema_export"] = "PASS" if schemas.returncode == 0 and "exported 50 schemas" in schemas.stdout else "FAIL"
        details["contract_schema_export"] = (schemas.stdout + schemas.stderr).strip()

        independent = run([sys.executable, "-m", "pytest", "tests/independent/test_p2t02_p3_boundaries.py", "-q"])
        checks["independent_boundary_verifier"] = "PASS" if independent.returncode == 0 else "FAIL"
        details["independent_boundary_verifier"] = (independent.stdout + independent.stderr).strip()

        pg_ok, pg_detail = postgres_offline_sql()
        checks["postgresql_offline_migration_compile"] = "PASS" if pg_ok else "FAIL"
        details["postgresql_offline_migration_compile"] = pg_detail

        rec_ok, rec_detail = recovery_reference(db_url, object_root, tmp)
        checks["database_object_store_recovery_reference"] = "PASS" if rec_ok else "FAIL"
        details["database_object_store_recovery_reference"] = rec_detail

    local_ok = all(v == "PASS" for v in checks.values())
    status = {
        "work_id": "P2-T02-P3-01-MULTIMODAL-CAPABILITY-FOUNDATION",
        "status": "LOCAL_VERIFIED_AWAITING_LIVE_POSTGRES" if local_ok else "BLOCKED_TECHNICAL_VERIFICATION",
        "human_gate": "G3_NOT_READY",
        "phase": "P2-T02 + P3-00/P3-01 contract foundation",
        "baseline": "P2-T01-G3-ACCEPTED",
        "summary": (
            "P2-T02 multimodal ingestion/University Memory/retrieval and P3 capability contract/registry/discovery are implemented and locally verified. Live PostgreSQL recovery evidence remains the external CI gate before G3."
            if local_ok else
            "Technical verification has failures; Human action is not required until AI clears them."
        ),
        "checks": checks,
        "external_checks": {
            "live_postgresql_revision_0004": "PENDING_EXTERNAL_CI",
            "live_postgresql_multimodal_pilot": "PENDING_EXTERNAL_CI",
            "live_postgresql_db_object_store_recovery": "PENDING_EXTERNAL_CI",
            "independent_live_evidence_qualification": "PENDING_EXTERNAL_CI",
        },
        "known_limitations": [
            "ARU-01 remains synthetic; no real learner PII is used.",
            "PDF and DOCX have deterministic text extraction; image/audio/video are ingested as immutable governed artifacts with media metadata. OCR, speech transcription and video semantic analysis remain provider adapters for later versioned upgrades.",
            "Vector retrieval is a provider-neutral deterministic hashing baseline, not a production embedding model; provider implementation is replaceable behind the retrieval boundary.",
            "P3 scope is contract/registry/Smart Box manifest/discovery only. Connection Planner, Assembly runtime and Write Box Studio are intentionally not opened in this tranche.",
            "Connecting real SIS/LMS/HR or personal data requires a separate Human G2 privacy/retention/access decision.",
        ],
        "human_action": "None for verification. Publish the prepared CI activation package only because this session has no GitHub write connector; GitHub Actions then owns live PostgreSQL verification.",
    }
    (OUT / "P2T02-P3-LATEST.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "TECHNICAL-DETAILS-P2T02-P3.json").write_text(
        json.dumps({"checks": checks, "details": details}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if local_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
