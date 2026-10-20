"""注册/验证码接口在 SMTP 未配置时的行为。"""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from backend.main import app


@pytest.fixture(autouse=True)
def smtp_off(monkeypatch):
    """强制关闭 SMTP，保证测试结果与机器上的 .env 无关。"""
    monkeypatch.setattr(settings, 'SMTP_ENABLE', False)
    monkeypatch.setattr(settings, 'SMTP_USER', '')
    monkeypatch.setattr(settings, 'SMTP_PASSWORD', '')


def test_capabilities_reports_email_verification_off():
    client = TestClient(app)
    res = client.get('/api/auth/capabilities')

    assert res.status_code == 200
    assert res.json()['email_verification'] is False


def test_verify_code_returns_503_without_smtp():
    client = TestClient(app)
    res = client.post(
        '/api/auth/verify-code', json={'email': 'test@example.com'}
    )

    assert res.status_code == 503
    assert '邮箱' in res.json()['detail']


def test_register_without_email():
    client = TestClient(app)
    res = client.post(
        '/api/auth/register',
        json={
            'username': 'reguser',
            'password': 'Pass12345',
            'email': '',
            'verify_code': '',
        },
    )

    assert res.status_code == 200
    assert res.json()['username'] == 'reguser'


def test_register_with_email_skips_code_when_smtp_disabled():
    client = TestClient(app)
    res = client.post(
        '/api/auth/register',
        json={
            'username': 'reguser2',
            'password': 'Pass12345',
            'email': 'x@example.com',
            'verify_code': '',
        },
    )

    assert res.status_code == 200
    assert res.json()['username'] == 'reguser2'
