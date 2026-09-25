from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CHECKS = (
    "live_postgresql_aru01_trust_pilot",
    "live_postgresql_backup",
    "live_postgresql_restore",
    "restored_institutional_history_present",
)


def qualify(payload: dict) -> dict:
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        checks = {}
    qualified = {
        name: checks.get(name) is True
        for name in REQUIRED_CHECKS
    }
    source_pass = payload.get("status") == "PASS"
    decision_count = payload.get("restored_decision_count")
    history_count_valid = isinstance(decision_count, int) and not isinstance(decision_count, bool) and decision_count >= 1
    qualified["source_status_pass"] = source_pass
    qualified["restored_decision_count_valid"] = history_count_valid
    result = {
        "status": "PASS" if all(qualified.values()) else "FAIL",
        "evidence_class": "LIVE_POSTGRESQL_PHASE1",
        "qualified_checks": qualified,
        "source_restored_decision_count": decision_count,
        "note": "This qualifies technical CI evidence only; it does not grant Human G3 acceptance.",
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently qualify ANU Phase-1 PostgreSQL CI evidence")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = qualify(payload)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
