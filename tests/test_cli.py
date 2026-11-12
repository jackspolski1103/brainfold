from __future__ import annotations

import json
import sys
import warnings
from types import SimpleNamespace

import httpx
import pytest

from oif.cli import main

TOKEN = "TEST_ACCESS_TOKEN_NEVER_PRINT"
SERVER = "http://127.0.0.1:8765"


def install_client(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setenv("OIF_ACCESS_TOKEN", TOKEN)
    monkeypatch.setattr(
        "oif.cli.httpx.Client", lambda **kw: original(**kw, transport=httpx.MockTransport(handler))
    )


def input_values(monkeypatch, *values):
    iterator = iter(values)

    def read(_):
        value = next(iterator, EOFError())
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr("builtins.input", read)


def test_run_uses_service_bearer_header_and_server_session(monkeypatch, capsys):
    seen = []

    def handler(request):
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        seen.append((request.url.path, json.loads(request.content or b"{}")))
        if request.url.path == "/health":
            return httpx.Response(200, json={"model": "chosen-model", "model_provider": "openai"})
        if request.url.path == "/v1/sessions":
            return httpx.Response(200, json={"id": "session-one", "agent_id": "costos"})
        return httpx.Response(200, json={"text": "Respuesta del servicio"})

    install_client(monkeypatch, handler)
    assert main(["run", "--server", SERVER, "--agent", "costos", "Pregunta natural"]) == 0
    assert seen == [
        ("/health", {}),
        ("/v1/sessions", {"agent_id": "costos", "audience_ids": []}),
        ("/v1/sessions/session-one/messages", {"text": "Pregunta natural"}),
    ]
    output = capsys.readouterr()
    assert "Respuesta del servicio" in output.out
    assert TOKEN not in output.out + output.err


def test_chat_resumes_existing_session_and_shows_model_destination(monkeypatch, capsys):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path == "/health":
            return httpx.Response(200, json={"model": "chosen-model", "model_provider": "openai"})
        if request.method == "GET":
            return httpx.Response(200, json={"id": "own-session", "agent_id": "costos"})
        return httpx.Response(200, json={"text": "Continuación"})

    install_client(monkeypatch, handler)
    input_values(monkeypatch, "", "Seguí el trabajo", EOFError())
    assert main(["chat", "--server", SERVER, "--agent", "costos", "--session", "own-session"]) == 0
    assert paths == ["/health", "/v1/sessions/own-session", "/v1/sessions/own-session/messages"]
    output = capsys.readouterr()
    assert "chosen-model" in output.out and "openai" in output.out
    assert "Continuación" in output.out and "Contexto compartido autorizado" in output.out
    assert TOKEN not in output.out + output.err


def test_ctrl_c_during_request_asks_server_to_cancel(monkeypatch, capsys):
    cancelled = []

    def handler(request):
        if request.url.path.endswith("/messages"):
            raise KeyboardInterrupt
        if request.url.path.endswith("/cancel"):
            cancelled.append(request.url.path)
            return httpx.Response(200, json={"cancelled": True})
        if request.url.path == "/health":
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"id": "one", "agent_id": "costos"})

    install_client(monkeypatch, handler)
    input_values(monkeypatch, "Tarea larga")
    assert main(["chat", "--server", SERVER, "--agent", "costos"]) == 130
    assert cancelled == ["/v1/sessions/one/cancel"]
    assert "Traceback" not in capsys.readouterr().err


def test_http_error_body_is_not_printed(monkeypatch, capsys):
    install_client(monkeypatch, lambda _: httpx.Response(503, text=f"PROVIDER_PRIVATE {TOKEN}"))
    assert main(["run", "--server", SERVER, "--agent", "costos", "Pregunta"]) == 1
    output = capsys.readouterr()
    assert "PROVIDER_PRIVATE" not in output.out + output.err
    assert TOKEN not in output.out + output.err
    assert "Traceback" not in output.err


def test_absent_token_uses_hidden_input_not_command_argument(monkeypatch, capsys):
    install_client(monkeypatch, lambda _: httpx.Response(401))
    monkeypatch.delenv("OIF_ACCESS_TOKEN")
    monkeypatch.setattr("oif.cli.getpass.getpass", lambda _: TOKEN)
    assert main(["run", "--server", SERVER, "--agent", "costos", "Pregunta"]) == 1
    assert TOKEN not in capsys.readouterr().err


def test_serve_builds_shared_app_and_binds_only_loopback(monkeypatch):
    calls = []
    application = object()
    monkeypatch.setitem(
        sys.modules, "oif.bootstrap", SimpleNamespace(build_service_app=lambda path: application)
    )
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append((app, kwargs)))
    assert main(["serve", "--config", "synthetic.json"]) == 0
    assert calls[0][0] is application
    assert calls[0][1]["host"] == "127.0.0.1"
    assert calls[0][1]["access_log"] is False


def test_example_mcp_is_synthetic_loopback_server(monkeypatch, capsys):
    calls = []
    application = object()
    monkeypatch.setitem(
        sys.modules,
        "oif.fixtures.mcp_server",
        SimpleNamespace(create_mcp_app=lambda **kwargs: application),
    )
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append((app, kwargs)))
    assert main(["example-mcp"]) == 0
    assert calls[0][0] is application
    assert calls[0][1]["host"] == "127.0.0.1"
    assert calls[0][1]["port"] == 8011
    assert "sintético" in capsys.readouterr().out


def test_hidden_input_never_falls_back_to_echoed_input(monkeypatch, capsys):
    import getpass

    monkeypatch.delenv("OIF_ACCESS_TOKEN", raising=False)

    def unsafe_fallback(_):
        warnings.warn("Could echo input", getpass.GetPassWarning, stacklevel=1)
        pytest.fail("No se debe llegar a leer una credencial con eco")

    monkeypatch.setattr("oif.cli.getpass.getpass", unsafe_fallback)
    assert main(["run", "--server", SERVER, "--agent", "costos", "Pregunta"]) == 1
    assert "OIF_ACCESS_TOKEN" in capsys.readouterr().err


def test_verify_example_is_explicit_and_not_a_canned_chat(monkeypatch, capsys):
    async def verify():
        return {"synthetic": True, "model_calls": 0}

    monkeypatch.setitem(sys.modules, "oif.verification", SimpleNamespace(verify_example=verify))
    assert main(["verify-example"]) == 0
    assert json.loads(capsys.readouterr().out) == {"synthetic": True, "model_calls": 0}


@pytest.mark.parametrize(
    "args",
    [
        ["chat", "--agent", "costos"],
        ["serve", "--config", "example.json", "--host", "0.0.0.0"],
        ["chat", "--server", "http://example.org", "--agent", "costos"],
    ],
)
def test_cli_requires_service_and_safe_development_bind(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
