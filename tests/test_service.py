"""Service policy checks use synthetic identities and an in-process transport."""

import asyncio

import pytest

from oif.domain import (
    AgentDefinition,
    CapabilityVersion,
    Configuration,
    Connection,
    MemoryNode,
    Message,
    OIFError,
    OrganizationContext,
    Principal,
    RemoteTool,
    ToolCall,
)
from oif.memory import PermissionedMemory
from oif.registry import Registry
from oif.service import SharedService

INPUT_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}},
    "required": ["kind"],
    "additionalProperties": False,
}
REMOTE_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "project_id": {"type": "string"}},
    "required": ["kind", "project_id"],
    "additionalProperties": False,
}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"total": {"type": "number"}},
    "required": ["total"],
    "additionalProperties": False,
}


def capability(**changes):
    values = {
        "id": "query",
        "version": 1,
        "organization_id": "atlas",
        "title": "Consulta",
        "instructions": "No inventar datos; informar errores.",
        "connection_id": "records",
        "tool_name": "query_records",
        "allowed_projects": frozenset({"costs", "contracts"}),
        "input_schema": INPUT_SCHEMA,
        "output_schema": OUTPUT_SCHEMA,
        "status": "published",
    }
    return CapabilityVersion(**(values | changes))


class Transport:
    def __init__(self):
        self.calls = []
        self.result = {"total": 12}
        self.schema = REMOTE_SCHEMA
        self.error = None
        self.before_list = None
        self.before_call = None

    async def list_tools(self, connection):
        if self.before_list:
            self.before_list()
        return [RemoteTool(name="query_records", input_schema=self.schema)]

    async def call(self, connection, tool_name, arguments):
        self.calls.append((connection.id, tool_name, arguments))
        if self.before_call:
            self.before_call()
        if self.error:
            raise self.error
        return self.result


def build_service(capabilities=None):
    config = Configuration(
        organizations=(
            OrganizationContext(
                id="atlas", content="Reglas comunes Atlas.", version=1, status="published"
            ),
            OrganizationContext(
                id="other", content="Contexto ajeno.", version=1, status="published"
            ),
        ),
        principals=(
            Principal(id="ana", organization_id="atlas", project_ids=frozenset({"costs"})),
            Principal(id="bea", organization_id="atlas", project_ids=frozenset({"contracts"})),
            Principal(id="reviewer", organization_id="atlas", project_ids=frozenset({"costs"})),
            Principal(id="outsider", organization_id="other", project_ids=frozenset({"costs"})),
        ),
        connections=(
            Connection(id="records", organization_id="atlas", url="http://127.0.0.1:8766/mcp"),
        ),
        capabilities=tuple(capabilities if capabilities is not None else [capability()]),
        agents=tuple(
            AgentDefinition(
                id=project,
                organization_id="atlas",
                project_id=project,
                instructions=f"Analizar {project}.",
                capability_ids=("query",),
                argument_bindings={"query": {"project_id": project}},
            )
            for project in ("costs", "contracts")
        ),
    )
    transport = Transport()
    return SharedService(Registry(config), transport), transport


def call(**arguments):
    return ToolCall(id="synthetic-call", name="query", arguments={"kind": "summary"} | arguments)


@pytest.mark.parametrize(
    "principal,agent",
    [
        ("outsider", "costs"),
        ("ana", "contracts"),
        ("missing", "costs"),
    ],
)
def test_session_creation_denies_wrong_organization_project_and_unknown(principal, agent):
    service, _ = build_service()
    with pytest.raises(OIFError, match="autorizada"):
        service.create_session(principal, agent)


def test_audience_is_resolved_by_server_and_must_have_project_access():
    service, _ = build_service()
    for audience in ("outsider", "bea", "unknown"):
        with pytest.raises(OIFError):
            service.create_session("ana", "costs", (audience,))


def test_sessions_are_private_and_metadata_cannot_forge_authority():
    service, _ = build_service()
    session = service.create_session("ana", "costs")
    with pytest.raises(OIFError):
        service.get_session("reviewer", session.id)
    session.principal_id = "reviewer"
    with pytest.raises(OIFError):
        service.authorize_session(session)


async def test_two_agents_reuse_one_capability_with_project_specific_bindings():
    service, transport = build_service()
    costs = service.create_session("ana", "costs")
    contracts = service.create_session("bea", "contracts")
    for session in (costs, contracts):
        prepared = await service.prepare(session)
        assert prepared.capability_versions == {"query": 1}
        assert "Reglas comunes Atlas" in prepared.system
        assert (await service.execute(session, call())).ok
    assert [item[2]["project_id"] for item in transport.calls] == ["costs", "contracts"]


async def test_one_published_correction_updates_both_agents_without_copying():
    service, _ = build_service()
    costs = service.create_session("ana", "costs")
    contracts = service.create_session("bea", "contracts")
    await service.prepare(costs)
    await service.prepare(contracts)
    service.registry.publish_capability(
        capability(version=2, instructions="Corrección compartida.")
    )
    for session in (costs, contracts):
        prepared = await service.prepare(session)
        assert prepared.capability_versions == {"query": 2}
        assert "Corrección compartida" in prepared.system
        assert (await service.execute(session, call())).capability_version == 2
    assert set(service.registry.capability_history["query"]) == {1, 2}


async def test_draft_successor_does_not_replace_published_version():
    service, _ = build_service([capability(), capability(version=2, status="draft")])
    prepared = await service.prepare(service.create_session("ana", "costs"))
    assert prepared.capability_versions == {"query": 1}


@pytest.mark.parametrize("status", ["draft", "revoked"])
async def test_unpublished_or_revoked_capability_never_becomes_a_tool(status):
    service, transport = build_service([capability(status=status)])
    session = service.create_session("ana", "costs")
    assert (await service.prepare(session)).tools == ()
    result = await service.execute(session, call())
    assert not result.ok and result.error.code == "acceso_denegado"
    assert transport.calls == []


async def test_revoked_head_never_falls_back_to_old_published_version():
    service, _ = build_service([capability(), capability(version=2)])
    service.registry.revoke_capability("query")
    session = service.create_session("ana", "costs")
    assert (await service.prepare(session)).tools == ()


@pytest.mark.parametrize("invalid", [{"project_id": "contracts"}, {"kind": 42}, {"extra": True}])
async def test_invalid_inputs_and_bound_argument_override_never_reach_mcp(invalid):
    service, transport = build_service()
    result = await service.execute(service.create_session("ana", "costs"), call(**invalid))
    assert not result.ok and result.error.code == "argumentos_invalidos"
    assert transport.calls == []


async def test_remote_schema_is_checked_before_calling_tool():
    service, transport = build_service()
    transport.schema = REMOTE_SCHEMA | {"required": ["unavailable_field"]}
    result = await service.execute(service.create_session("ana", "costs"), call())
    assert not result.ok and result.error.code == "argumentos_invalidos"
    assert transport.calls == []


async def test_invalid_output_is_sanitized_and_not_returned():
    service, transport = build_service()
    transport.result = {"secret": "must-not-be-returned"}
    result = await service.execute(service.create_session("ana", "costs"), call())
    assert not result.ok and result.error.code == "respuesta_invalida"
    assert result.data is None and "must-not-be-returned" not in result.model_dump_json()


@pytest.mark.parametrize("stage", ["list", "call"])
@pytest.mark.parametrize("subject", ["ana", "reviewer"])
async def test_membership_revocation_during_mcp_await_blocks_result(stage, subject):
    service, transport = build_service()
    session = service.create_session("ana", "costs", ("reviewer",))

    def revoke():
        principal = service.registry.principals[subject]
        service.registry.replace_principal(
            principal.model_copy(update={"project_ids": frozenset()})
        )

    setattr(transport, f"before_{stage}", revoke)
    result = await service.execute(session, call())
    assert not result.ok and result.error.code == "acceso_denegado" and result.data is None
    if stage == "list":
        assert not transport.calls


async def test_capability_revocation_during_mcp_await_blocks_result():
    service, transport = build_service()
    transport.before_call = lambda: service.registry.revoke_capability("query")
    result = await service.execute(service.create_session("ana", "costs"), call())
    assert not result.ok and result.error.code == "acceso_denegado"
    assert result.data is None


async def test_revoked_history_cannot_be_replayed_even_with_published_successor():
    service, _ = build_service()
    session = service.create_session("ana", "costs")
    await service.prepare(session)
    service.registry.publish_capability(capability(version=2))
    service.registry.revoke_capability("query", 1)
    with pytest.raises(OIFError):
        service.authorize_session(session)


async def test_changed_version_while_model_was_thinking_is_not_executed():
    service, transport = build_service()
    session = service.create_session("ana", "costs")
    await service.prepare(session)
    service.registry.publish_capability(capability(version=2))
    result = await service.execute(session, call())
    assert not result.ok and result.error.code == "capacidad_modificada"
    assert not transport.calls


@pytest.mark.parametrize(
    "exception,code",
    [
        (RuntimeError("private-backend-error"), "fuente_no_disponible"),
        (TimeoutError("private-backend-error"), "tiempo_agotado"),
    ],
)
async def test_unexpected_errors_use_common_safe_codes(exception, code):
    service, transport = build_service()
    transport.error = exception
    for principal, agent in (("ana", "costs"), ("bea", "contracts")):
        result = await service.execute(service.create_session(principal, agent), call())
        assert not result.ok and result.error.code == code
        assert "private-backend-error" not in result.model_dump_json()


async def test_cancellation_propagates_instead_of_becoming_source_failure():
    service, transport = build_service()
    transport.error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await service.execute(service.create_session("ana", "costs"), call())


@pytest.mark.parametrize("reference", ["https://example.invalid/schema", "file:///etc/passwd"])
def test_trusted_contract_rejects_external_schema_references(reference):
    with pytest.raises(OIFError, match="contrato"):
        build_service([capability(input_schema={"$ref": reference})])


async def test_remote_schema_cannot_trigger_external_resolution():
    service, transport = build_service()
    transport.schema = {"$dynamicRef": "https://example.invalid/schema"}
    result = await service.execute(service.create_session("ana", "costs"), call())
    assert not result.ok and result.error.code == "configuracion_invalida"
    assert not transport.calls


def memory_nodes():
    return [
        MemoryNode(
            organization_id="atlas",
            path="/",
            kind="directory",
            status="published",
            allowed_projects=frozenset({"costs", "contracts"}),
        ),
        MemoryNode(organization_id="atlas", path="/common", kind="directory", status="published"),
        MemoryNode(
            organization_id="atlas",
            path="/common/process.md",
            kind="file",
            content="Procedimiento sintético común.",
            status="published",
        ),
        MemoryNode(
            organization_id="atlas",
            path="/costs",
            kind="directory",
            status="published",
            allowed_projects=frozenset({"costs"}),
        ),
        MemoryNode(
            organization_id="atlas",
            path="/costs/private.md",
            kind="file",
            content="Contenido privado sintético.",
            status="published",
            allowed_principals=frozenset({"ana"}),
        ),
        MemoryNode(
            organization_id="atlas",
            path="/contracts",
            kind="directory",
            status="published",
            allowed_projects=frozenset({"contracts"}),
        ),
    ]


def memory_call(tool, path):
    return ToolCall(id="memory-fixture", name=tool, arguments={"path": path})


async def test_memory_tools_navigate_authorized_repository_without_automatic_content_injection():
    service, transport = build_service()
    service.memory = PermissionedMemory(memory_nodes())
    session = service.create_session("ana", "costs")
    prepared = await service.prepare(session)
    assert {tool.name for tool in prepared.tools} == {"query", "listar_memoria", "leer_memoria"}
    assert "Procedimiento sintético común." not in prepared.system
    listing = await service.execute(session, memory_call("listar_memoria", "/"))
    assert listing.ok and listing.capability_version is None
    assert [entry["path"] for entry in listing.data] == ["/common", "/costs"]
    nested = await service.execute(session, memory_call("listar_memoria", "/common"))
    assert nested.data == [{"path": "/common/process.md", "kind": "file", "version": 1}]
    document = await service.execute(session, memory_call("leer_memoria", "/common/process.md"))
    assert document.ok and document.data["content"] == "Procedimiento sintético común."
    assert not transport.calls


async def test_memory_resolves_requester_and_audience_acl_before_returning_content():
    service, _ = build_service()
    service.memory = PermissionedMemory(memory_nodes())
    session = service.create_session("ana", "costs", ("reviewer",))
    listing = await service.execute(session, memory_call("listar_memoria", "/costs"))
    assert listing.ok and listing.data == []
    hidden = await service.execute(session, memory_call("leer_memoria", "/costs/private.md"))
    assert not hidden.ok and hidden.error.code == "ruta_no_disponible" and hidden.data is None


@pytest.mark.parametrize("path", ["/contracts", "/missing", "/../etc/passwd"])
async def test_memory_inaccessible_and_invalid_paths_have_same_safe_error(path):
    service, _ = build_service()
    service.memory = PermissionedMemory(memory_nodes())
    result = await service.execute(
        service.create_session("ana", "costs"), memory_call("listar_memoria", path)
    )
    assert not result.ok and result.error.code == "ruta_no_disponible" and result.data is None


async def test_memory_generation_change_drops_history_and_exposes_current_revision():
    service, _ = build_service()
    memory = PermissionedMemory(memory_nodes())
    service.memory = memory
    session = service.create_session("ana", "costs")
    original_revision = (await service.prepare(session)).memory_revision
    session.messages.append(Message(role="tool", content="previous-private-content"))
    memory.replace_node(
        memory_nodes()[2].model_copy(
            update={
                "version": 2,
                "content": "Procedimiento corregido.",
            }
        )
    )
    assert service.get_session("ana", session.id).messages == []
    assert (await service.prepare(session)).memory_revision > original_revision
    result = await service.execute(session, memory_call("leer_memoria", "/common/process.md"))
    assert result.ok and result.data["content"] == "Procedimiento corregido."


async def test_memory_revision_change_during_read_drops_stale_result():
    service, _ = build_service()
    delegate = PermissionedMemory(memory_nodes())

    class ChangingMemory:
        @property
        def revision(self):
            return delegate.revision

        async def read_file(self, organization_id, path, principals):
            result = await delegate.read_file(organization_id, path, principals)
            delegate.replace_node(memory_nodes()[2].model_copy(update={"status": "revoked"}))
            return result

        async def list_directory(self, organization_id, path, principals):
            return await delegate.list_directory(organization_id, path, principals)

    service.memory = ChangingMemory()
    result = await service.execute(
        service.create_session("ana", "costs"), memory_call("leer_memoria", "/common/process.md")
    )
    assert not result.ok and result.error.code == "contexto_modificado" and result.data is None


async def test_memory_rechecks_audience_membership_after_adapter_await():
    service, _ = build_service()
    delegate = PermissionedMemory(memory_nodes())

    class RevokingMemory:
        @property
        def revision(self):
            return delegate.revision

        async def read_file(self, organization_id, path, principals):
            result = await delegate.read_file(organization_id, path, principals)
            principal = service.registry.principals["reviewer"]
            service.registry.replace_principal(principal.model_copy(update={"active": False}))
            return result

        async def list_directory(self, organization_id, path, principals):
            return await delegate.list_directory(organization_id, path, principals)

    service.memory = RevokingMemory()
    session = service.create_session("ana", "costs", ("reviewer",))
    result = await service.execute(session, memory_call("leer_memoria", "/common/process.md"))
    assert not result.ok and result.error.code == "acceso_denegado" and result.data is None


def test_partial_membership_revocation_clears_history_while_agent_remains_authorized():
    service, _ = build_service()
    service.memory = PermissionedMemory(memory_nodes())
    original = service.registry.principals["ana"]
    service.registry.replace_principal(
        original.model_copy(
            update={
                "project_ids": frozenset({"costs", "contracts"}),
            }
        )
    )
    session = service.create_session("ana", "costs")
    session.messages.append(Message(role="tool", content="previous-contracts-file-content"))
    memory_revision = service.memory.revision
    service.registry.replace_principal(original)
    assert service.get_session("ana", session.id).messages == []
    assert service.memory.revision == memory_revision


async def test_partial_membership_revocation_changes_prepared_authorization_revision():
    service, _ = build_service()
    original = service.registry.principals["ana"]
    service.registry.replace_principal(
        original.model_copy(
            update={
                "project_ids": frozenset({"costs", "contracts"}),
            }
        )
    )
    session = service.create_session("ana", "costs")
    previous = await service.prepare(session)
    service.registry.replace_principal(original)
    current = await service.prepare(session)
    assert previous.authorization_revision != current.authorization_revision
    assert previous.capability_versions == current.capability_versions
    assert previous.memory_revision == current.memory_revision


async def test_published_capability_scope_restriction_blocks_old_history():
    service, _ = build_service()
    session = service.create_session("ana", "costs")
    await service.prepare(session)
    session.messages.append(Message(role="tool", content="previous-costs-data"))
    service.registry.publish_capability(
        capability(version=2, allowed_projects=frozenset({"contracts"}))
    )
    with pytest.raises(OIFError):
        service.get_session("ana", session.id)


def test_capability_cannot_override_memory_builtin_names():
    with pytest.raises(OIFError, match="reservado"):
        build_service([capability(id="leer_memoria")])
