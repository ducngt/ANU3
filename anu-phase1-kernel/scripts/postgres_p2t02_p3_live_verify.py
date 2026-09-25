from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
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
BASELINE_REVISION = "0004"


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
        revisions = script.iterate_revisions(current_revision, "base")
        return any(revision.revision == BASELINE_REVISION for revision in revisions)
    except Exception:
        return False


def restored_evidence(database_url: str, object_store_root: Path) -> dict:
    Session = sessionmaker(bind=make_engine(database_url), future=True)
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
            store=FileSystemObjectStore(object_store_root),
        )
        retrieval = retrieve(session, RetrievalQuery(query="responsible AI systems", mode=RetrievalMode.HYBRID))
        discovery = discover_capabilities(session, CapabilityDiscoveryQuery(operation_id="knowledge.retrieve"))
    return {
        "counts": counts,
        "artifact_integrity": integrity.model_dump(mode="json"),
        "retrieval_hit_count": len(retrieval.hits),
        "retrieval_first_hit_has_provenance": bool(retrieval.hits and retrieval.hits[0].provenance_ref),
        "discovered_capability_count": len(discovery.hits),
        "discovered_box_count": len(discovery.hits[0].box_refs) if discovery.hits else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--restore-url", required=True)
    parser.add_argument("--backup", required=True)
    parser.add_argument("--object-store", required=True)
    parser.add_argument("--restored-object-store", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    database_revision = current_database_revision(args.database_url)
    baseline_preserved = baseline_revision_is_ancestor(database_revision)
    object_store = Path(args.object_store).resolve()
    restored_store = Path(args.restored_object_store).resolve()
    pilot = run_pilot(args.database_url, object_store)
    backup = backup_database(args.database_url, args.backup)
    restore = restore_database(args.backup, args.restore_url)
    if restored_store.exists():
        shutil.rmtree(restored_store)
    shutil.copytree(object_store, restored_store)
    restored = restored_evidence(args.restore_url, restored_store)
    checks = {
        "baseline_revision_0004_in_history": baseline_preserved,
        "live_postgresql_multimodal_capability_pilot": pilot["pass"],
        "live_postgresql_backup": backup["status"] == "PASS",
        "live_postgresql_restore": restore["status"] == "PASS",
        "restored_artifact_history_present": restored["counts"]["artifacts"] >= 5,
        "restored_knowledge_present": restored["counts"]["knowledge"] >= 1,
        "restored_university_memory_present": restored["counts"]["memory"] >= 6,
        "restored_retrieval_projection_present": restored["counts"]["retrieval"] >= 6,
        "restored_artifact_integrity_pass": restored["artifact_integrity"]["integrity_state"] == "PASS",
        "restored_retrieval_has_provenance": restored["retrieval_first_hit_has_provenance"],
        "restored_capability_registry_present": restored["counts"]["capabilities"] >= 1,
        "restored_replaceable_boxes_present": restored["discovered_box_count"] >= 2,
    }
    result = {
        "work_id": "P2-T02-P3-01-MULTIMODAL-CAPABILITY-FOUNDATION",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "pilot": pilot,
        "restored": restored,
        "synthetic_data_only": True,
        "baseline_revision": BASELINE_REVISION,
        "database_revision": database_revision,
        "compatibility_rule": "accepted P2-T02/P3-01 baseline must remain valid under additive later Alembic heads",
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
