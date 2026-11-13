import importlib.util
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
