"""健康检查测试。"""

from fastapi.testclient import TestClient

from backend.main import app


def test_health_includes_checks():
    client = TestClient(app)
    res = client.get('/api/health')

    assert res.status_code == 200
    body = res.json()
    assert body['version'] == '4.0'
    assert body['checks']['api'] == 'ok'
    assert body['checks']['database'] == 'ok'
    assert body['status'] == 'ok'
