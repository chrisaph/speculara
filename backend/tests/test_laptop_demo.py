import importlib.util
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app import access,main


@pytest.fixture
def launcher():
    spec=importlib.util.spec_from_file_location('laptop_demo',Path(__file__).resolve().parents[2]/'deploy/laptop-demo.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_tunnel_preflight_checks_real_auth_and_operator_separation(launcher,monkeypatch):
    monkeypatch.setattr(access,'get_settings',lambda:SimpleNamespace(require_access_code=True,demo_access_token='test-demo',operator_access_token='test-operator'))
    launcher.verify_protection(TestClient(main.app),{'demo':'test-demo','operator':'test-operator'})


def test_tunnel_is_refused_when_local_backend_is_unprotected(launcher,monkeypatch):
    monkeypatch.setattr(access,'get_settings',lambda:SimpleNamespace(require_access_code=False,demo_access_token='',operator_access_token=''))
    with pytest.raises(AssertionError,match='not protected'):
        launcher.verify_protection(TestClient(main.app),{'demo':'test-demo','operator':'test-operator'})


def test_tunnel_is_refused_for_an_unmatched_demo_key(launcher,monkeypatch):
    monkeypatch.setattr(access,'get_settings',lambda:SimpleNamespace(require_access_code=True,demo_access_token='actual-demo',operator_access_token='test-operator'))
    with pytest.raises(AssertionError,match='Demo key check failed'):
        launcher.verify_protection(TestClient(main.app),{'demo':'wrong-demo','operator':'test-operator'})


def test_ngrok_uses_private_token_and_closes_its_own_listener(launcher,monkeypatch,tmp_path):
    closed=[];saved=[]
    class Listener:
        def url(self):return 'https://demo.ngrok-free.app'
        async def close(self):closed.append(True)
    class Builder:
        def authtoken(self,token):assert token=='test-private-ngrok-token';return self
        def root_cas(self,value):assert value=='host';return self
        async def connect(self):return self
        def http_endpoint(self):return self
        async def listen_and_forward(self,address):assert address==launcher.LOCAL;return Listener()
        async def close(self):closed.append('session')
    monkeypatch.setitem(sys.modules,'ngrok',SimpleNamespace(SessionBuilder=Builder))
    stop=tmp_path/'stop.request';stop.touch()
    monkeypatch.setattr(launcher,'STOP',stop)
    monkeypatch.setattr(launcher,'save_state',lambda **values:saved.append(values))
    asyncio.run(launcher.host_ngrok({'ngrok':'test-private-ngrok-token'},SimpleNamespace(poll=lambda:None)))
    assert closed==[True,'session'] and saved[0]['url']=='https://demo.ngrok-free.app'


def test_non_https_ngrok_endpoint_is_closed_and_rejected(launcher,monkeypatch):
    closed=[]
    class Listener:
        def url(self):return 'http://unprotected.invalid'
        async def close(self):closed.append(True)
    class Builder:
        def authtoken(self,token):return self
        def root_cas(self,value):assert value=='host';return self
        async def connect(self):return self
        def http_endpoint(self):return self
        async def listen_and_forward(self,address):return Listener()
        async def close(self):closed.append('session')
    monkeypatch.setitem(sys.modules,'ngrok',SimpleNamespace(SessionBuilder=Builder))
    with pytest.raises(RuntimeError,match='HTTPS endpoint'):
        asyncio.run(launcher.host_ngrok({'ngrok':'test-private-token'},SimpleNamespace(poll=lambda:None)))
    assert closed==[True,'session']


def test_ngrok_tls_failure_is_actionable_without_disabling_verification(launcher,monkeypatch):
    class Builder:
        def authtoken(self,token):return self
        def root_cas(self,value):assert value=='host';return self
        async def connect(self):raise ValueError('failed to connect session','tls handshake error')
    monkeypatch.setitem(sys.modules,'ngrok',SimpleNamespace(SessionBuilder=Builder))
    with pytest.raises(RuntimeError,match='Windows trusted certificates'):
        asyncio.run(launcher.host_ngrok({'ngrok':'test-private-token'},SimpleNamespace(poll=lambda:None)))
