from __future__ import annotations

import asyncio
from collections import deque

import pytest

from oif.domain import (
    Message,
    ModelTurn,
    OIFError,
    PreparedContext,
    Session,
    ToolCall,
    ToolDescription,
    ToolResult,
)
from oif.runtime import AgentRunner


class Service:
    def __init__(self):
        self.active = True
        self.version = 1
        self.memory_revision = 0
        self.executed = []

    def authorize_session(self, session):
        if not self.active:
            raise OIFError("acceso_denegado", "El acceso fue revocado.")

    async def prepare(self, session):
        self.authorize_session(session)
        return PreparedContext(
            system=f"Contexto autorizado v{self.version}",
            tools=(ToolDescription(name="consultar", description="Consulta", input_schema={}),),
            capability_versions={"consultar": self.version},
            memory_revision=self.memory_revision,
        )

    async def execute(self, session, call):
        self.authorize_session(session)
        self.executed.append(call)
        return ToolResult(
            call_id=call.id,
            capability_id="consultar",
            capability_version=self.version,
            ok=True,
            data={"filas": [{"valor": 4}]},
        )


class Model:
    def __init__(self, *outputs):
        self.outputs = deque(outputs)
        self.requests = []

    async def complete(self, messages, tools):
        self.requests.append((list(messages), tools))
        value = self.outputs.popleft()
        return await value() if callable(value) else value


def session(identifier="session-a"):
    return Session(id=identifier, principal_id="ana", agent_id="costos", audience_ids=("ana",))


def call(identifier="call-a"):
    return ToolCall(id=identifier, name="consultar", arguments={"periodo": "ejemplo"})


async def test_tool_results_use_tool_role_and_commit_only_complete_turn():
    service = Service()
    model = Model(ModelTurn(tool_calls=(call(),)), ModelTurn(content="El valor es 4."))
    runner = AgentRunner(service, model)
    current = session()

    reply = await runner.turn(current, "Consultá el valor")

    assert reply.text == "El valor es 4."
    assert reply.tool_results[0].data == {"filas": [{"valor": 4}]}
    assert [m.role for m in current.messages] == ["user", "assistant", "tool", "assistant"]
    sent = model.requests[1][0]
    assert sent[-1].role == "tool" and sent[-1].tool_call_id == "call-a"
    assert '"ok":true' in sent[-1].content
    assert current.messages[0].role != "system"


async def test_history_is_per_session_and_is_reused_only_for_its_owner():
    model = Model(
        ModelTurn(content="Primera"), ModelTurn(content="Otra"), ModelTurn(content="Sigue")
    )
    runner = AgentRunner(Service(), model)
    one, two = session(), session("session-b")
    await runner.turn(one, "Trabajo privado A")
    await runner.turn(two, "Trabajo privado B")
    await runner.turn(one, "Continuá")
    assert "Trabajo privado A" not in str(model.requests[1][0])
    assert "Trabajo privado B" not in str(model.requests[2][0])
    assert [m.content for m in model.requests[2][0][1:]] == [
        "Trabajo privado A",
        "Primera",
        "Continuá",
    ]


async def test_revocation_while_model_runs_denies_final_answer():
    service = Service()

    async def revoked():
        service.active = False
        return ModelTurn(content="Esta respuesta ya no debe salir")

    model = Model(revoked)
    current = session()
    with pytest.raises(OIFError, match="revocado") as error:
        await AgentRunner(service, model).turn(current, "Pregunta")
    assert error.value.code == "acceso_denegado"
    assert current.messages == []


@pytest.mark.parametrize("attribute", ["version", "memory_revision"])
async def test_change_during_model_await_does_not_return_stale_context(attribute):
    service = Service()

    async def changed():
        setattr(service, attribute, 2)
        return ModelTurn(content="Respuesta basada en v1")

    current = session()
    with pytest.raises(OIFError) as error:
        await AgentRunner(service, Model(changed)).turn(current, "Pregunta")
    assert error.value.code == "contexto_modificado"
    assert current.messages == []


@pytest.mark.parametrize("attribute", ["version", "memory_revision"])
async def test_new_published_version_discards_dependent_history_before_model(attribute):
    service = Service()
    model = Model(ModelTurn(content="Respuesta v1"), ModelTurn(content="Respuesta v2"))
    runner = AgentRunner(service, model)
    current = session()
    await runner.turn(current, "Contenido de versión anterior")
    setattr(service, attribute, 2)
    reply = await runner.turn(current, "Consulta actual")
    assert "reinicié el historial" in reply.text
    assert [m.content for m in model.requests[1][0]] == [
        f"Contexto autorizado v{service.version}",
        "Consulta actual",
    ]
    assert [m.content for m in current.messages] == ["Consulta actual", "Respuesta v2"]


async def test_cancel_keeps_committed_history_and_releases_session():
    started = asyncio.Event()

    async def blocked():
        started.set()
        await asyncio.Event().wait()

    model = Model(blocked, ModelTurn(content="Recuperada"))
    runner = AgentRunner(Service(), model)
    current = session()
    current.messages.append(Message(role="assistant", content="Historial previo"))
    task = asyncio.create_task(runner.turn(current, "Pendiente"))
    await started.wait()
    assert runner.cancel(current.id)
    with pytest.raises(OIFError) as error:
        await task
    assert error.value.code == "turno_cancelado"
    assert [m.content for m in current.messages] == ["Historial previo"]
    assert not runner.cancel(current.id)
    assert (await runner.turn(current, "Continuar")).text == "Recuperada"


async def test_timeout_does_not_store_partial_turn():
    async def blocked():
        await asyncio.Event().wait()

    current = session()
    with pytest.raises(OIFError) as error:
        await AgentRunner(Service(), Model(blocked), timeout_seconds=0.01).turn(current, "Pregunta")
    assert error.value.code == "tiempo_agotado"
    assert current.messages == []


async def test_step_limit_blocks_tool_execution_on_final_step():
    service = Service()
    current = session()
    with pytest.raises(OIFError) as error:
        await AgentRunner(service, Model(ModelTurn(tool_calls=(call(),))), max_steps=1).turn(
            current, "Pregunta"
        )
    assert error.value.code == "limite_pasos"
    assert not service.executed and current.messages == []


async def test_batch_tool_limit_is_checked_before_any_execution():
    service = Service()
    model = Model(ModelTurn(tool_calls=(call("a"), call("b"))))
    with pytest.raises(OIFError) as error:
        await AgentRunner(service, model, max_tool_calls=1).turn(session(), "Pregunta")
    assert error.value.code == "limite_herramientas"
    assert not service.executed


async def test_history_limit_prevents_unbounded_model_context():
    model = Model(ModelTurn(content="No debe ejecutarse"))
    with pytest.raises(OIFError) as error:
        await AgentRunner(Service(), model, max_history_chars=20).turn(session(), "x" * 30)
    assert error.value.code == "historial_lleno"
    assert model.requests == []


async def test_concurrent_turns_for_same_session_are_serialized():
    started, release = asyncio.Event(), asyncio.Event()

    async def first():
        started.set()
        await release.wait()
        return ModelTurn(content="Primera respuesta")

    model = Model(first, ModelTurn(content="Segunda respuesta"))
    runner = AgentRunner(Service(), model)
    current = session()
    first_task = asyncio.create_task(runner.turn(current, "Primera pregunta"))
    await started.wait()
    second_task = asyncio.create_task(runner.turn(current, "Segunda pregunta"))
    await asyncio.sleep(0)
    assert len(model.requests) == 1
    release.set()
    await asyncio.gather(first_task, second_task)
    assert [m.content for m in model.requests[1][0][1:]] == [
        "Primera pregunta",
        "Primera respuesta",
        "Segunda pregunta",
    ]


async def test_unexpected_failures_are_safe_and_do_not_commit_history():
    class BrokenService(Service):
        async def execute(self, session, call):
            raise RuntimeError("PRIVATE_PROVIDER_SECRET")

    current = session()
    with pytest.raises(OIFError) as error:
        await AgentRunner(BrokenService(), Model(ModelTurn(tool_calls=(call(),)))).turn(
            current, "Pregunta"
        )
    assert "PRIVATE_PROVIDER_SECRET" not in str(error.value)
    assert current.messages == []


async def test_already_revoked_session_never_calls_model():
    service = Service()
    service.active = False
    model = Model(ModelTurn(content="No debe salir"))
    with pytest.raises(OIFError):
        await AgentRunner(service, model).turn(session(), "Pregunta")
    assert model.requests == []
