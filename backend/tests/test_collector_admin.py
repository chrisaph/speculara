import importlib.util
import sys
from pathlib import Path
import httpx
import pytest


@pytest.fixture
def admin(monkeypatch):
    path=Path(__file__).resolve().parents[2]/'deploy/collector-admin.py'
    spec=importlib.util.spec_from_file_location('collector_admin_check',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(sys,'argv',['collector-admin.py','status','--url','https://speculara-api.onrender.com'])
    return module


def test_missing_remote_key_is_actionable(admin,monkeypatch,capsys):
    monkeypatch.delenv('OPERATOR_ACCESS_TOKEN',raising=False)
    assert admin.main()==1
    assert 'missing in this terminal' in capsys.readouterr().err


@pytest.mark.parametrize('status,message',[(401,'Operator key rejected'),(403,'Operator key rejected'),(409,'collector is busy'),(503,'Render is starting')])
def test_http_failures_identify_cause_without_exposing_key(admin,monkeypatch,capsys,status,message):
    token='private-test-operator-key'
    monkeypatch.setenv('OPERATOR_ACCESS_TOKEN',token)
    original=httpx.Client
    def handle(request):
        assert request.headers['X-Speculara-Operator-Key']==token
        return httpx.Response(status,json={'detail':'test'})
    monkeypatch.setattr(admin.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    assert admin.main()==1
    output=capsys.readouterr().err
    assert message in output and token not in output


def test_success_uses_system_tls_context_and_returns_status(admin,monkeypatch,capsys):
    monkeypatch.setenv('OPERATOR_ACCESS_TOKEN','test-operator')
    original=httpx.Client
    context=admin.ssl.create_default_context()
    monkeypatch.setattr(admin.ssl,'create_default_context',lambda:context)
    def client(**kw):
        assert kw['verify'] is context and kw['timeout']==120
        return original(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'busy':False})),**kw)
    monkeypatch.setattr(admin.httpx,'Client',client)
    assert admin.main()==0
    assert '"busy": false' in capsys.readouterr().out
