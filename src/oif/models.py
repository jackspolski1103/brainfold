"""OpenAI Responses adapter. Credentials stay outside prompts and protocol history.

References: https://developers.openai.com/api/docs/guides/function-calling
and https://developers.openai.com/api/docs/guides/migrate-to-responses
"""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Sequence
from typing import Any

import httpx

from oif.domain import Message, ModelTurn, OIFError, ToolCall, ToolDescription

RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIResponsesModel:
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 60,
        max_output_tokens: int = 4096,
    ) -> None:
        if not model.strip() or not api_key.strip():
            raise OIFError(
                "modelo_no_configurado",
                "Configurá OPENAI_API_KEY y OIF_OPENAI_MODEL en el entorno del servidor.",
            )
        if timeout_seconds <= 0 or max_output_tokens < 1:
            raise ValueError("Los límites del modelo deben ser positivos.")
        self.model = model.strip()
        self._api_key = api_key.strip()
        self._client = client
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens

    @classmethod
    def from_env(cls, **kwargs: Any) -> OpenAIResponsesModel:
        return cls(
            model=os.environ.get("OIF_OPENAI_MODEL", ""),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            **kwargs,
        )

    async def complete(
        self, messages: Sequence[Message], tools: Sequence[ToolDescription]
    ) -> ModelTurn:
        payload = {
            "model": self.model,
            "store": False,
            "include": ["reasoning.encrypted_content"],
            "input": self._input(messages),
            "tools": [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                    "strict": False,
                }
                for tool in tools
            ],
            "max_output_tokens": self.max_output_tokens,
        }
        try:
            if self._client is not None:
                response = await self._post(self._client, payload)
            else:
                async with httpx.AsyncClient(trust_env=False) as client:
                    response = await self._post(client, payload)
        except httpx.TimeoutException:
            raise OIFError(
                "modelo_tiempo_agotado",
                "El proveedor del modelo no respondió a tiempo.",
                retryable=True,
            ) from None
        except httpx.HTTPError:
            raise OIFError(
                "modelo_no_disponible",
                "No se pudo conectar con el proveedor del modelo.",
                retryable=True,
            ) from None
        if response.status_code in (401, 403):
            raise OIFError(
                "modelo_no_autorizado", "El proveedor rechazó el acceso al modelo configurado."
            )
        if response.status_code == 429:
            raise OIFError(
                "modelo_limite", "El proveedor alcanzó un límite de uso o cuota.", retryable=True
            )
        if response.status_code >= 500:
            raise OIFError(
                "modelo_no_disponible",
                "El proveedor del modelo no está disponible.",
                retryable=True,
            )
        if not response.is_success:
            raise OIFError(
                "modelo_solicitud_rechazada", "El proveedor rechazó la solicitud al modelo."
            )
        try:
            return self._parse(response.json())
        except (ValueError, TypeError, KeyError):
            raise OIFError(
                "modelo_respuesta_invalida", "El proveedor devolvió una respuesta no utilizable."
            ) from None

    async def _post(self, client: httpx.AsyncClient, payload: dict[str, Any]) -> httpx.Response:
        return await client.post(
            RESPONSES_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self.timeout_seconds,
            follow_redirects=False,
        )

    @staticmethod
    def _input(messages: Sequence[Message]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "tool":
                if not message.tool_call_id:
                    raise OIFError(
                        "historial_invalido", "Un resultado no identifica su herramienta."
                    )
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.tool_call_id,
                        "output": message.content,
                    }
                )
            elif message.role == "assistant" and message.provider_items:
                # Replay native items in their original order, including encrypted reasoning.
                items.extend(copy.deepcopy(message.provider_items))
            else:
                if message.content:
                    items.append({"role": message.role, "content": message.content})
                for call in message.tool_calls:
                    items.append(
                        {
                            "type": "function_call",
                            "call_id": call.id,
                            "name": call.name,
                            "arguments": json.dumps(
                                call.arguments, ensure_ascii=False, allow_nan=False
                            ),
                        }
                    )
        return items

    @staticmethod
    def _parse(payload: Any) -> ModelTurn:
        if not isinstance(payload, dict) or payload.get("status", "completed") != "completed":
            raise ValueError("incomplete response")
        outputs = payload["output"]
        if not isinstance(outputs, list):
            raise ValueError("output is not a list")
        text: list[str] = []
        calls: list[ToolCall] = []
        provider_items: list[dict[str, Any]] = []
        for item in outputs:
            if not isinstance(item, dict):
                raise ValueError("invalid item")
            kind = item.get("type")
            if kind == "message":
                parts = item.get("content", [])
                if not isinstance(parts, list):
                    raise ValueError("invalid message content")
                for part in parts:
                    if not isinstance(part, dict):
                        raise ValueError("invalid content part")
                    if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                        text.append(part["text"])
                    elif part.get("type") == "refusal" and isinstance(part.get("refusal"), str):
                        text.append(part["refusal"])
                provider_items.append(item)
            elif kind == "function_call":
                raw = item["arguments"]
                if not isinstance(raw, str):
                    raise ValueError("arguments are not JSON text")
                arguments = json.loads(raw, parse_constant=_invalid_constant)
                if not isinstance(arguments, dict):
                    raise ValueError("arguments are not an object")
                if not isinstance(item.get("call_id"), str) or not item["call_id"]:
                    raise ValueError("missing call id")
                if not isinstance(item.get("name"), str) or not item["name"]:
                    raise ValueError("missing tool name")
                calls.append(ToolCall(id=item["call_id"], name=item["name"], arguments=arguments))
                provider_items.append(item)
            elif kind == "reasoning":
                if (
                    not isinstance(item.get("encrypted_content"), str)
                    or not item["encrypted_content"]
                ):
                    raise ValueError("reasoning state is not replayable")
                provider_items.append(
                    {
                        key: value
                        for key, value in item.items()
                        if key in {"type", "id", "summary", "encrypted_content", "status"}
                    }
                )
            else:
                raise ValueError("unexpected output item")
        if not text and not calls:
            raise ValueError("empty response")
        return ModelTurn(
            content="\n".join(text), tool_calls=tuple(calls), provider_items=tuple(provider_items)
        )


def _invalid_constant(value: str) -> None:
    raise ValueError("non-finite JSON number")
