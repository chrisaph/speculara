from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app import access, main


@pytest.fixture
def secured(monkeypatch):
    settings = SimpleNamespace(require_access_code=True, demo_access_token='test-demo', operator_access_token='test-operator')
    monkeypatch.setattr(access, 'get_settings', lambda: settings)
    return TestClient(main.app)


def test_access_code_required(secured):
    assert secured.get('/api/access').status_code == 401
    assert secured.get('/api/access', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    assert secured.get('/api/access', headers={'Authorization': 'Bearer test-demo'}).status_code == 200
    assert secured.get('/api/access', headers={'X-Speculara-Operator-Key': 'test-operator'}).status_code == 200


@pytest.mark.parametrize('path', ['/api/collector/login', '/api/collector/login/finish', '/api/collector/cancel'])
def test_guests_cannot_control_sessions(secured, path):
    assert secured.post(path, headers={'Authorization': 'Bearer test-demo', 'X-Forwarded-For': '127.0.0.1'}).status_code == 403
    assert secured.post(path).status_code == 403


def test_cors_and_health_remain_available(secured):
    assert secured.get('/api/health').status_code == 200
    response = secured.options('/api/access', headers={'Origin': 'http://localhost:8443', 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization'})
    assert response.status_code == 200
    denied = secured.get('/api/access', headers={'Origin': 'http://localhost:8443'})
    assert denied.headers['access-control-allow-origin'] == 'http://localhost:8443'


def test_missing_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(access, 'get_settings', lambda: SimpleNamespace(require_access_code=True, demo_access_token='', operator_access_token=''))
    assert TestClient(main.app).get('/api/access').status_code == 503


def test_local_access_unchanged(monkeypatch):
    monkeypatch.setattr(access, 'get_settings', lambda: SimpleNamespace(require_access_code=False, demo_access_token='', operator_access_token=''))
    assert TestClient(main.app).get('/api/access').status_code == 200


def test_operator_can_finish_remote_login(secured, monkeypatch):
    monkeypatch.setattr(main, 'get_settings', access.get_settings)
    async def finish():
        return {'ok': True}
    monkeypatch.setattr(main.collector, 'finish_login', finish)
    client = TestClient(main.app, client=('203.0.113.1', 12345))
    assert client.post('/api/collector/login/finish', headers={'X-Speculara-Operator-Key': 'test-operator'}).json() == {'ok': True}
