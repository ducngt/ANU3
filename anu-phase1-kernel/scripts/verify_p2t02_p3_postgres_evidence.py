from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = {
    "live_postgresql_multimodal_capability_pilot",
    "live_postgresql_backup",
    "live_postgresql_restore",
    "restored_artifact_history_present",
    "restored_knowledge_present",
    "restored_university_memory_present",
    "restored_retrieval_projection_present",
    "restored_artifact_integrity_pass",
    "restored_retrieval_has_provenance",
    "restored_capability_registry_present",
    "restored_replaceable_boxes_present",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    checks = payload.get("checks", {})
    missing = sorted(REQUIRED - set(checks))
    failed = sorted(name for name in REQUIRED if checks.get(name) is not True)
    qualified = (
        payload.get("status") == "PASS"
        and payload.get("database_revision") == "0004"
        and payload.get("synthetic_data_only") is True
        and not missing
        and not failed
    )
    result = {
        "work_id": "P2-T02-P3-01-MULTIMODAL-CAPABILITY-FOUNDATION",
        "qualification": "PASS" if qualified else "FAIL",
        "missing_checks": missing,
        "failed_checks": failed,
        "source_evidence": args.input,
        "qualified_database_revision": payload.get("database_revision"),
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
