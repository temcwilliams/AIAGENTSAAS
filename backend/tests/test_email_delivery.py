import httpx

from app import email_delivery
from app.config import settings


class FakeClient:
    def __init__(self, response_status=201, exception=None, **_kwargs):
        self.response_status = response_status
        self.exception = exception
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url, **kwargs):
        if self.exception:
            raise self.exception
        self.request = (url, kwargs)
        FakeClient.last_request = self.request
        return httpx.Response(self.response_status)


def configure(monkeypatch, provider='brevo'):
    monkeypatch.setattr(settings, 'email_provider', provider)
    monkeypatch.setattr(settings, 'email_api_key', 'private-test-key')
    monkeypatch.setattr(settings, 'email_from', 'Agent Meadow <owner@outlook.com>')


def test_brevo_uses_https_api_and_structured_sender(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(email_delivery.httpx, 'Client', FakeClient)

    assert email_delivery.available()
    assert email_delivery.send('client@example.com', 'setup', 'https://example.com/#private-link')
    url, request = FakeClient.last_request
    assert url == 'https://api.brevo.com/v3/smtp/email'
    assert request['headers'] == {'api-key': 'private-test-key', 'accept': 'application/json'}
    assert request['json']['sender'] == {'name': 'Agent Meadow', 'email': 'owner@outlook.com'}
    assert request['json']['to'] == [{'email': 'client@example.com'}]
    assert request['json']['subject'] == 'Set up your Agent Meadow password'
    assert 'https://example.com/#private-link' in request['json']['textContent']


def test_brevo_failure_is_safe_and_invalid_sender_disables_delivery(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setattr(email_delivery.httpx, 'Client', lambda **kwargs: FakeClient(response_status=400, **kwargs))
    assert not email_delivery.send('client@example.com', 'reset', 'https://example.com/#private')

    monkeypatch.setattr(settings, 'email_from', 'invalid\nheader@example.com')
    assert not email_delivery.available()
    assert not email_delivery.send('client@example.com', 'reset', 'https://example.com/#private')


def test_brevo_network_error_returns_false(monkeypatch):
    configure(monkeypatch)
    error = httpx.ConnectError('unavailable')
    monkeypatch.setattr(email_delivery.httpx, 'Client', lambda **kwargs: FakeClient(exception=error, **kwargs))
    assert not email_delivery.send('client@example.com', 'verify', 'https://example.com/#private')
