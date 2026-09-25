from scripts.verify_postgres_evidence import qualify


def passing_payload():
    return {
        "status": "PASS",
        "checks": {
            "live_postgresql_aru01_trust_pilot": True,
            "live_postgresql_backup": True,
            "live_postgresql_restore": True,
            "restored_institutional_history_present": True,
        },
        "restored_decision_count": 1,
    }


def test_qualifies_complete_live_postgres_evidence():
    result = qualify(passing_payload())
    assert result["status"] == "PASS"


def test_rejects_missing_or_false_live_postgres_evidence():
    payload = passing_payload()
    payload["checks"]["live_postgresql_restore"] = False
    result = qualify(payload)
    assert result["status"] == "FAIL"


def test_rejects_zero_restored_history():
    payload = passing_payload()
    payload["restored_decision_count"] = 0
    result = qualify(payload)
    assert result["status"] == "FAIL"
