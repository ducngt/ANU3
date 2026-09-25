from __future__ import annotations

import argparse
import json
from pathlib import Path

BASELINE_REVISION = "0006"
REQUIRED = {
    "baseline_revision_0006_in_history",
    "live_postgresql_e1_e2_e3_pilot",
    "live_postgresql_responsibility_replay",
    "live_postgresql_handover_fail_closed",
    "live_postgresql_human_signature_e3",
    "live_postgresql_backup",
    "live_postgresql_restore",
    "restored_work_contracts",
    "restored_work_graphs",
    "restored_work_instances",
    "restored_tasks",
    "restored_transitions",
    "restored_handovers",
    "restored_e1_e2_e3_replay",
}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--input", required=True); ap.add_argument("--output", required=True); args = ap.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    checks = payload.get("checks", {})
    missing = sorted(REQUIRED - set(checks))
    failed = sorted(k for k in REQUIRED if checks.get(k) is not True)
    qualified = payload.get("status") == "PASS" and payload.get("baseline_revision") == BASELINE_REVISION and payload.get("synthetic_data_only") is True and isinstance(payload.get("database_revision"), str) and bool(payload.get("database_revision")) and not missing and not failed
    result = {
        "work_id": "P4-GOVERNED-HUMAN-AI-WORK-RUNTIME",
        "qualification": "PASS" if qualified else "FAIL",
        "missing_checks": missing,
        "failed_checks": failed,
        "baseline_revision": payload.get("baseline_revision"),
        "qualified_database_revision": payload.get("database_revision"),
        "source_evidence": args.input,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
