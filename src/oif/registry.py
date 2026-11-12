"""Trusted, in-memory development registry; no request can mutate this authority."""

from __future__ import annotations

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from oif.domain import (
    AgentDefinition,
    CapabilityVersion,
    Configuration,
    Connection,
    OIFError,
    OrganizationContext,
    Principal,
)


def denied() -> OIFError:
    return OIFError("acceso_denegado", "La operación no está autorizada.")


def check_contract_schema(schema: dict) -> None:
    """Contracts are local JSON schemas; validation never resolves external URLs."""

    def inspect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"$ref", "$dynamicRef"} and (
                    not isinstance(item, str) or not item.startswith("#")
                ):
                    raise OIFError("configuracion_invalida", "El contrato no es válido.")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)

    inspect(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        raise OIFError("configuracion_invalida", "El contrato no es válido.") from None


def _unique[T](items: tuple[T, ...]) -> dict[str, T]:
    values: dict[str, T] = {}
    for item in items:
        item_id = item.id
        if item_id in values:
            raise OIFError("configuracion_invalida", "Hay identificadores duplicados.")
        values[item_id] = item
    return values


class Registry:
    """Published state is resolved on each operation, including after external awaits.

    Mutators are a trusted server administration API, deliberately absent from HTTP.
    Draft successors do not replace a published version. Revoking the published head
    does not silently restore an older version.
    """

    def __init__(self, configuration: Configuration):
        self.principals: dict[str, Principal] = _unique(configuration.principals)
        self.agents: dict[str, AgentDefinition] = _unique(configuration.agents)
        self.connections: dict[str, Connection] = _unique(configuration.connections)
        self.organization_history: dict[str, dict[int, OrganizationContext]] = {}
        self.capability_history: dict[str, dict[int, CapabilityVersion]] = {}
        self.capabilities: dict[str, CapabilityVersion] = {}
        self.organizations: dict[str, OrganizationContext] = {}
        for context in configuration.organizations:
            versions = self.organization_history.setdefault(context.id, {})
            if context.version in versions:
                raise OIFError("configuracion_invalida", "Hay versiones duplicadas.")
            versions[context.version] = context.model_copy(deep=True)
        for organization_id, versions in self.organization_history.items():
            self.organizations[organization_id] = versions[max(versions)]
        for capability in configuration.capabilities:
            self._store_capability(capability)

    def _store_capability(self, capability: CapabilityVersion) -> None:
        if capability.id in {"listar_memoria", "leer_memoria"}:
            raise OIFError("configuracion_invalida", "El identificador está reservado.")
        check_contract_schema(capability.input_schema)
        check_contract_schema(capability.output_schema)
        versions = self.capability_history.setdefault(capability.id, {})
        if capability.version in versions:
            raise OIFError("configuracion_invalida", "La versión ya está registrada.")
        if versions and any(
            value.organization_id != capability.organization_id for value in versions.values()
        ):
            raise OIFError("configuracion_invalida", "El ámbito de la capacidad no es válido.")
        versions[capability.version] = capability.model_copy(deep=True)
        self.capabilities[capability.id] = versions[max(versions)]

    def replace_principal(self, principal: Principal) -> None:
        self.principals[principal.id] = principal.model_copy(deep=True)

    def publish_capability(self, capability: CapabilityVersion) -> None:
        """Register a new immutable published version, preserving previous versions."""
        self._store_capability(capability.model_copy(update={"status": "published"}, deep=True))

    def revoke_capability(self, capability_id: str, version: int | None = None) -> None:
        versions = self.capability_history.get(capability_id)
        if not versions:
            raise denied()
        selected = (
            version if version is not None else self.current_capability(capability_id).version
        )
        if selected not in versions:
            raise denied()
        versions[selected] = versions[selected].model_copy(update={"status": "revoked"}, deep=True)
        self.capabilities[capability_id] = versions[max(versions)]

    def principal(self, principal_id: str) -> Principal:
        principal = self.principals.get(principal_id)
        if principal is None or not principal.active:
            raise denied()
        return principal

    def agent(self, agent_id: str) -> AgentDefinition:
        agent = self.agents.get(agent_id)
        if agent is None:
            raise denied()
        return agent

    def organization(self, organization_id: str) -> OrganizationContext:
        versions = self.organization_history.get(organization_id, {})
        candidates = [item for item in versions.values() if item.status != "draft"]
        if not candidates:
            raise denied()
        current = max(candidates, key=lambda item: item.version)
        if current.status != "published":
            raise denied()
        return current

    def current_capability(self, capability_id: str) -> CapabilityVersion:
        candidates = [
            item
            for item in self.capability_history.get(capability_id, {}).values()
            if item.status != "draft"
        ]
        if not candidates:
            raise denied()
        current = max(candidates, key=lambda item: item.version)
        if current.status != "published":
            raise denied()
        return current

    def authorize_agent(self, principal_id: str, agent_id: str) -> AgentDefinition:
        principal = self.principal(principal_id)
        agent = self.agent(agent_id)
        if (
            principal.organization_id != agent.organization_id
            or agent.project_id not in principal.project_ids
        ):
            raise denied()
        self.organization(agent.organization_id)
        return agent
