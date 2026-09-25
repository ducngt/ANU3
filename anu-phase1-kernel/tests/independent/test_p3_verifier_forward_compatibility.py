from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_p3_runtime_postgres_evidence import BASELINE_REVISION, REQUIRED

ROOT = Path(__file__).resolve().parents[2]


def test_p3_local_verifier_does_not_pin_schema_count_or_current_head():
    source = (ROOT / 'scripts' / 'verify_p3_runtime.py').read_text(encoding='utf-8')
    assert 'exported 67 schemas' not in source
    assert 'revision 0005"' not in source


def test_p3_postgres_qualifier_allows_additive_0006_head_when_0005_preserved(tmp_path):
    payload = {
        'status': 'PASS',
        'baseline_revision': BASELINE_REVISION,
        'database_revision': '0006',
        'synthetic_data_only': True,
        'checks': {name: True for name in REQUIRED},
    }
    p = tmp_path / 'evidence.json'
    p.write_text(json.dumps(payload), encoding='utf-8')
    assert payload['database_revision'] != BASELINE_REVISION
    assert payload['checks']['baseline_revision_0005_in_history'] is True
