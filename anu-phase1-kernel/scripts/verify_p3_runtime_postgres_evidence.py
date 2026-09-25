from __future__ import annotations

import argparse
import json
from pathlib import Path

BASELINE_REVISION = "0005"
REQUIRED = {
    "baseline_revision_0005_in_history",
    "live_postgresql_sbbs_runtime_pilot",
    "live_postgresql_write_box_audit_promotion",
    "live_postgresql_provider_replacement",
    "live_postgresql_transform_registry",
    "live_postgresql_adapter_registry",
    "live_postgresql_backup",
    "live_postgresql_restore",
    "restored_transform_registry",
    "restored_adapter_registry",
    "restored_compatibility_evidence",
    "restored_connection_plans",
    "restored_assemblies",
    "restored_write_box_candidate",
    "restored_assembly_replay",
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
    qualified = (payload.get("status") == "PASS" and payload.get("baseline_revision") == BASELINE_REVISION and isinstance(payload.get("database_revision"), str) and bool(payload.get("database_revision")) and payload.get("synthetic_data_only") is True and not missing and not failed)
    result = {
        "work_id": "P3-02-P3-07-SBBS-CAPABILITY-RUNTIME",
        "qualification": "PASS" if qualified else "FAIL",
        "missing_checks": missing,
        "failed_checks": failed,
        "baseline_revision": payload.get("baseline_revision"),
        "qualified_database_revision": payload.get("database_revision"),
        "compatibility_rule": "later additive database heads are allowed when baseline 0005 remains in migration history and baseline behavior passes",
        "source_evidence": args.input,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
