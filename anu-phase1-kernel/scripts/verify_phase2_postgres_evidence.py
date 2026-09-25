from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = {
    "live_postgresql_aru01_reality_pilot",
    "live_postgresql_backup",
    "live_postgresql_restore",
    "restored_data_history_present",
    "restored_university_memory_present",
    "restored_historical_projection_replays_v1",
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
    qualified = payload.get("status") == "PASS" and not missing and not failed
    result = {
        "work_id": "P2-T01-REALITY-DATA-MEMORY",
        "qualification": "PASS" if qualified else "FAIL",
        "missing_checks": missing,
        "failed_checks": failed,
        "source_evidence": args.input,
    }
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if qualified else 1


if __name__ == "__main__":
    raise SystemExit(main())
