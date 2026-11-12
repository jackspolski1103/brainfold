"""Bounded, transactional conversational turns over the shared service contracts."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

from oif.domain import Message, OIFError, PreparedContext, RunReply, Session, ToolResult
from oif.ports import ModelPort


class AgentRunner:
    def __init__(
        self,
        service: Any,
        model: ModelPort,
        *,
        max_steps: int = 6,
        max_tool_calls: int = 12,
        timeout_seconds: float = 120,
        max_history_messages: int = 120,
        max_history_chars: int = 240_000,
    ) -> None:
        if min(max_steps, max_tool_calls, max_history_messages, max_history_chars) < 1:
            raise ValueError("Los límites del runtime deben ser positivos.")
        if timeout_seconds <= 0:
            raise ValueError("El tiempo máximo debe ser positivo.")
        self.service = service
        self.model = model
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.timeout_seconds = timeout_seconds
        self.max_history_messages = max_history_messages
        self.max_history_chars = max_history_chars
        self._locks: dict[str, asyncio.Lock] = {}
        self._active: dict[str, asyncio.Task[Any]] = {}
        self._contexts: dict[str, str] = {}

    def cancel(self, session_id: str) -> bool:
        """Cancel only an active turn; completed external operations are not undone."""
        task = self._active.get(session_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def turn(self, session: Session, text: str) -> RunReply:
        self.service.authorize_session(session)
        if not text.strip():
            raise OIFError("mensaje_vacio", "Escribí una tarea o una pregunta.")
        lock = self._locks.setdefault(session.id, asyncio.Lock())
        try:
            # Includes time waiting for another turn: concurrent requests cannot wait forever.
            async with asyncio.timeout(self.timeout_seconds):
                async with lock:
                    task = asyncio.current_task()
                    assert task is not None
                    self._active[session.id] = task
                    try:
                        return await self._turn(session, text)
                    finally:
                        if self._active.get(session.id) is task:
                            self._active.pop(session.id, None)
        except TimeoutError:
            raise OIFError(
                "tiempo_agotado",
                "El turno superó su tiempo máximo. Una operación ya completada puede "
                "haber surtido efecto; revisá su estado antes de repetirla.",
                retryable=True,
            ) from None
        except asyncio.CancelledError:
            raise OIFError(
                "turno_cancelado",
                "Turno cancelado. Las operaciones ya completadas no se deshacen.",
            ) from None
        except OIFError:
            raise
        except Exception:
            raise OIFError(
                "fallo_ejecucion", "No se pudo completar el turno. El historial no cambió."
            ) from None

    async def _prepare(self, session: Session) -> PreparedContext:
        self.service.authorize_session(session)
        context = await self.service.prepare(session)
        self.service.authorize_session(session)
        return context

    @staticmethod
    def _fingerprint(context: PreparedContext) -> str:
        value = json.dumps(context.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(value.encode()).hexdigest()

    async def _unchanged(self, session: Session, fingerprint: str) -> PreparedContext:
        context = await self._prepare(session)
        if self._fingerprint(context) != fingerprint:
            raise OIFError(
                "contexto_modificado",
                "El contexto o los permisos cambiaron durante el turno. "
                "No se entregó una respuesta con información anterior. Volvé a intentarlo.",
                retryable=True,
            )
        return context

    def _bounded(self, messages: list[Message]) -> None:
        # Include opaque provider state and arguments, not just the visible message text.
        size = sum(
            len(m.content)
            + len(json.dumps(m.provider_items, ensure_ascii=False))
            + sum(len(json.dumps(c.arguments, ensure_ascii=False)) for c in m.tool_calls)
            for m in messages
        )
        if len(messages) > self.max_history_messages or size > self.max_history_chars:
            raise OIFError(
                "historial_lleno",
                "La sesión alcanzó su límite de contexto. Iniciá otra sesión para continuar.",
            )

    async def _turn(self, session: Session, text: str) -> RunReply:
        context = await self._prepare(session)
        fingerprint = self._fingerprint(context)
        reset = session.id in self._contexts and self._contexts[session.id] != fingerprint
        # No partial turn enters the committed history, including on cancellation or denial.
        messages = [] if reset else list(session.messages)
        messages.append(Message(role="user", content=text))
        self._bounded(messages)
        results: list[ToolResult] = []
        call_ids = {call.id for message in messages for call in message.tool_calls}

        for step in range(self.max_steps):
            context = await self._unchanged(session, fingerprint)
            turn = await self.model.complete(
                [Message(role="system", content=context.system), *messages], context.tools
            )
            # A principal, audience or published artifact can be revoked while the model runs.
            context = await self._unchanged(session, fingerprint)
            if not turn.content.strip() and not turn.tool_calls:
                raise OIFError("respuesta_vacia", "El modelo no devolvió una respuesta utilizable.")
            messages.append(
                Message(
                    role="assistant",
                    content=turn.content,
                    tool_calls=turn.tool_calls,
                    provider_items=turn.provider_items,
                )
            )
            self._bounded(messages)
            if not turn.tool_calls:
                self.service.authorize_session(session)
                session.messages[:] = messages
                self._contexts[session.id] = fingerprint
                text_out = turn.content
                if reset:
                    text_out = (
                        "El contexto compartido cambió; reinicié el historial de esta sesión.\n\n"
                        + text_out
                    )
                return RunReply(
                    session_id=session.id,
                    agent_id=session.agent_id,
                    text=text_out,
                    tool_results=tuple(results),
                    capability_versions=context.capability_versions,
                )
            if step + 1 >= self.max_steps:
                raise OIFError("limite_pasos", "La tarea alcanzó el máximo de pasos de este turno.")
            if len(results) + len(turn.tool_calls) > self.max_tool_calls:
                raise OIFError(
                    "limite_herramientas",
                    "La tarea alcanzó el máximo de herramientas de este turno.",
                )
            # Validate the entire batch before any external call, including duplicate ids.
            new_ids = [call.id for call in turn.tool_calls]
            if (
                any(not identifier for identifier in new_ids)
                or len(set(new_ids)) != len(new_ids)
                or call_ids.intersection(new_ids)
            ):
                raise OIFError(
                    "llamada_invalida",
                    "El modelo devolvió identificadores de herramienta inválidos.",
                )
            call_ids.update(new_ids)
            for call in turn.tool_calls:
                self.service.authorize_session(session)
                result = await self.service.execute(session, call)
                await self._unchanged(session, fingerprint)
                results.append(result)
                messages.append(
                    Message(
                        role="tool",
                        content=result.model_dump_json(),
                        tool_call_id=call.id,
                    )
                )
                self._bounded(messages)

        raise OIFError("limite_pasos", "La tarea alcanzó el máximo de pasos de este turno.")
