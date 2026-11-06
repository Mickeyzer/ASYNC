import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app


class ProviderFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__("sensitive-provider-details fake-secret-marker")


def blocked_connection():
    error = httpx.ConnectError("sensitive-provider-details fake-secret-marker")
    error.__cause__ = PermissionError(13, "private socket information")
    return error


@pytest.mark.parametrize("failure,reason", [
    (blocked_connection(), "network_blocked"),
    (httpx.ConnectError("fake-secret-marker"), "network_unavailable"),
    (httpx.ReadTimeout("fake-secret-marker"), "timeout"),
    (ProviderFailure(401), "access_denied"),
    (ProviderFailure(403), "access_denied"),
    (ProviderFailure(404), "model_unavailable"),
    (ProviderFailure(429), "quota_exceeded"),
    (ProviderFailure(503), "provider_unavailable"),
    (ProviderFailure(504), "timeout"),
    (ProviderFailure(400), "invalid_request"),
    (RuntimeError("fake-secret-marker"), "unexpected_error"),
])
def test_diagnostics_are_specific_and_redacted(monkeypatch, caplog, failure, reason):
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "fake-secret-marker")

    class FailingClient:
        def __init__(self, **kwargs):
            raise failure

    monkeypatch.setattr(genai, "Client", FailingClient)
    response = TestClient(app).post("/api/discover", json={"message": "A synthetic clinic", "language": "hi", "consent": True})
    assert response.status_code == 200
    result = response.json()
    assert result["reason"] == reason
    assert result["mode"] == "guided"
    assert result["draft"] is None
    assert result["message_hi"]
    assert "fake-secret-marker" not in response.text + caplog.text
    assert "sensitive-provider-details" not in response.text + caplog.text
    code = getattr(failure, "code", None)
    if type(code) is int and 400 <= code <= 599:
        assert result["provider_http_status"] == code
    else:
        assert "provider_http_status" not in result


@pytest.mark.parametrize("code", [500, 503, 504, None])
def test_checker_reports_safe_status_without_provider_details(monkeypatch, capsys, code):
    import check_gemini
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "fake-secret-marker")
    monkeypatch.setattr("sys.argv", ["check_gemini.py"])

    class FailingClient:
        def __init__(self, **kwargs):
            if code is None:
                raise blocked_connection()
            raise ProviderFailure(code)

    monkeypatch.setattr(genai, "Client", FailingClient)
    assert check_gemini.main() == 1
    output = capsys.readouterr().out
    assert "fake-secret-marker" not in output
    assert "sensitive-provider-details" not in output
    if code is None:
        assert "network_blocked" in output
        assert "Provider HTTP status:" not in output
    else:
        assert f"Provider HTTP status: {code}" in output
        assert ("Diagnostic category: timeout" if code == 504 else "Diagnostic category: provider_unavailable") in output
    assert "Request timeout: 60 seconds; one attempt." in output
    assert "Elapsed:" in output


def test_checker_and_app_use_configured_model_and_bounded_attempt(monkeypatch):
    from google import genai

    observed = {}
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    class Client:
        def __init__(self, **kwargs):
            observed["options"] = kwargs["http_options"]
            self.models = self
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def generate_content(self, **kwargs):
            observed["model"] = kwargs["model"]
            return SimpleNamespace(text=json.dumps({"business_type": "clinic", "employees": 5, "sites": 1, "needs": ["internet"], "follow_up": "What is your budget?"}))

    monkeypatch.setattr(genai, "Client", Client)
    response = TestClient(app).post("/api/discover", json={"message": "Clinic with 5 staff and one site needs internet.", "consent": True})
    assert response.json()["mode"] == "gemini"
    assert observed["model"] == "test-model"
    assert observed["options"].timeout == 60000
    assert observed["options"].retry_options.attempts == 1


@pytest.mark.parametrize("status", [200, 504])
def test_sdk_sends_longer_deadline_and_handles_response(monkeypatch, status):
    from backend.advisor import discover
    from backend.models import DiscoveryRequest

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    requests = []

    def send(client, request, **kwargs):
        requests.append(request)
        assert request.headers["x-server-timeout"] == "60"
        assert request.extensions["timeout"]["read"] == 60
        if status == 504:
            return httpx.Response(504, request=request, json={"error": {
                "code": 504, "status": "DEADLINE_EXCEEDED", "message": "private-provider-detail",
            }})
        draft = {"business_type": "clinic", "employees": 5, "sites": 1,
                 "needs": ["internet"], "follow_up": "What is your budget?"}
        return httpx.Response(200, request=request, json={"candidates": [{
            "content": {"role": "model", "parts": [{"text": json.dumps(draft)}]},
            "finishReason": "STOP",
        }]})

    monkeypatch.setattr(httpx.Client, "send", send)
    result = discover(DiscoveryRequest(message="A clinic with 5 employees needs internet.", consent=True))
    assert len(requests) == 1
    if status == 200:
        assert result["mode"] == "gemini"
        assert result["draft"]["employees"] == 5
    else:
        assert result["reason"] == "timeout"
        assert result["provider_http_status"] == 504
        assert "private-provider-detail" not in json.dumps(result)


def test_blank_key_is_missing_and_not_sent(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    response = TestClient(app).post("/api/discover", json={"message": "Clinic", "consent": True})
    assert response.json()["reason"] == "missing_key"


@pytest.mark.parametrize("plain", [True, False])
@pytest.mark.parametrize("status", [200, 504])
def test_checker_isolates_plain_generation_and_temporary_model(monkeypatch, capsys, plain, status):
    import check_gemini
    import os

    monkeypatch.setenv("GEMINI_API_KEY", "fake-secret-marker")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-original-model")
    monkeypatch.setattr("sys.argv", ["check_gemini.py", "--model", "gemini-test-model"] + (["--plain"] if plain else []))
    calls = []

    def send(client, request, **kwargs):
        calls.append(request)
        assert request.url.path.endswith("/gemini-test-model:generateContent")
        body = json.loads(request.content)
        if plain:
            assert "generationConfig" not in body
            assert "systemInstruction" not in body
        else:
            assert body["generationConfig"]["responseJsonSchema"]
            assert "temperature" not in body["generationConfig"]
        if status == 504:
            return httpx.Response(504, request=request, json={"error": {
                "code": 504, "status": "DEADLINE_EXCEEDED", "message": "fake-secret-marker",
            }})
        response_text = "fake-secret-marker" if plain else json.dumps({"follow_up": "fake-secret-marker", "needs": []})
        return httpx.Response(200, request=request, json={"candidates": [{
            "content": {"role": "model", "parts": [{"text": response_text}]}, "finishReason": "STOP",
        }]})

    monkeypatch.setattr(httpx.Client, "send", send)
    assert check_gemini.main() == (0 if status == 200 else 1)
    assert len(calls) == 1
    assert os.environ["GEMINI_MODEL"] == "gemini-original-model"
    output = capsys.readouterr().out
    assert "fake-secret-marker" not in output
    assert "Model: gemini-test-model" in output
    if status == 200:
        assert ("Structured advisor generation has not been tested" if plain else "App settings have not changed") in output
    else:
        assert "Provider HTTP status: 504" in output


def test_client_configuration_is_not_served():
    client = TestClient(app)
    for path in ["/.env", "/package.json", "/src/App.tsx", "/node_modules/react/package.json"]:
        assert client.get(path).status_code == 404
