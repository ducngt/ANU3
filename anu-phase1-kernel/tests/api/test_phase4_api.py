from __future__ import annotations

from fastapi.testclient import TestClient

from anu_kernel.api import app


def test_health_reports_phase4_runtime():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    body = r.json()
    assert body['current_phase'] == 4
    assert body['phase_4_work_runtime'] is True
    assert tuple(int(x) for x in body['kernel_version'].split('.')) >= (0, 7, 0)


def test_phase4_routes_are_exposed():
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    required = {
        '/v4/work/contracts', '/v4/work/graphs', '/v4/work/plans', '/v4/work/instances',
        '/v4/work/tasks/execute', '/v4/work/transitions', '/v4/work/handover', '/v4/work/{work_id}/trace'
    }
    assert required.issubset(paths)
