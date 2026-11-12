from __future__ import annotations

import json

import httpx
import pytest

from oif.domain import Message, OIFError, ToolDescription
from oif.models import OpenAIResponsesModel

KEY = "TEST_ONLY_NOT_A_REAL_API_KEY"


def text_output(text="Respuesta"):
    return {
        "type": "message",
        "id": "msg_1",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


async def test_responses_replays_reasoning_and_exact_function_call_output_without_storage():
    requests = []
    native = [
        {"type": "reasoning", "id": "rs_1", "summary": [], "encrypted_content": "opaque-state"},
        {
            "type": "function_call",
            "id": "fc_1",
            "call_id": "call_1",
            "name": "consultar",
            "arguments": '{"periodo":"ejemplo"}',
            "status": "completed",
        },
    ]

    def handler(request):
        requests.append(json.loads(request.content))
        assert request.headers["authorization"] == f"Bearer {KEY}"
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": native if len(requests) == 1 else [text_output()],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = OpenAIResponsesModel(model="explicit-test-model", api_key=KEY, client=client)
        tools = [
            ToolDescription(
                name="consultar",
                description="Consulta autorizada",
                input_schema={"type": "object", "properties": {"periodo": {"type": "string"}}},
            )
        ]
        turn = await model.complete([Message(role="user", content="Consulta")], tools)
        assert turn.tool_calls[0].arguments == {"periodo": "ejemplo"}
        assistant = Message(
            role="assistant", tool_calls=turn.tool_calls, provider_items=turn.provider_items
        )
        await model.complete(
            [assistant, Message(role="tool", tool_call_id="call_1", content='{"ok":true}')], tools
        )

    assert requests[0]["store"] is False
    assert requests[0]["model"] == "explicit-test-model"
    assert requests[0]["tools"][0]["strict"] is False
    assert requests[0]["include"] == ["reasoning.encrypted_content"]
    assert requests[1]["input"] == [
        *native,
        {"type": "function_call_output", "call_id": "call_1", "output": '{"ok":true}'},
    ]
    assert KEY not in json.dumps(requests)
    assert "provider_items" not in assistant.model_dump()
    assert "opaque-state" not in repr(assistant)


@pytest.mark.parametrize("arguments", ["{", "[]", '"text"', '{"amount":NaN}'])
async def test_invalid_tool_arguments_fail_safely(arguments):
    output = {"type": "function_call", "call_id": "a", "name": "query", "arguments": arguments}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"output": [output]}))
    ) as client:
        with pytest.raises(OIFError) as error:
            await OpenAIResponsesModel(model="test", api_key=KEY, client=client).complete([], [])
    assert error.value.code == "modelo_respuesta_invalida"
    assert arguments not in str(error.value)


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
async def test_provider_errors_never_expose_raw_body_or_secret(status):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(status, text=f"PRIVATE_DIAGNOSTIC {KEY}")
        )
    ) as client:
        with pytest.raises(OIFError) as error:
            await OpenAIResponsesModel(model="test", api_key=KEY, client=client).complete([], [])
    assert KEY not in str(error.value)
    assert "PRIVATE_DIAGNOSTIC" not in str(error.value)
    assert error.value.retryable == (status == 429 or status >= 500)


async def test_network_timeout_is_safe():
    def timeout(request):
        raise httpx.ReadTimeout(KEY, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(OIFError) as error:
            await OpenAIResponsesModel(model="test", api_key=KEY, client=client).complete([], [])
    assert error.value.code == "modelo_tiempo_agotado"
    assert KEY not in str(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"output": []},
        {"output": "bad"},
        {"output": [None]},
        {"output": [{"type": "message", "content": ["invalid"]}]},
        {"output": [{"type": "message", "content": "invalid"}]},
        {"output": [text_output()], "status": "incomplete"},
        {"output": [{"type": "reasoning", "id": "reason_1", "summary": []}]},
    ],
)
async def test_malformed_or_incomplete_response_is_rejected(payload):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(OIFError) as error:
            await OpenAIResponsesModel(model="test", api_key=KEY, client=client).complete([], [])
    assert error.value.code == "modelo_respuesta_invalida"


def test_no_model_or_key_is_invented_from_environment(monkeypatch):
    monkeypatch.delenv("OIF_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(OIFError) as error:
        OpenAIResponsesModel.from_env()
    assert error.value.code == "modelo_no_configurado"
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    with pytest.raises(OIFError):
        OpenAIResponsesModel.from_env()
    monkeypatch.setenv("OIF_OPENAI_MODEL", "chosen-model")
    assert OpenAIResponsesModel.from_env().model == "chosen-model"
