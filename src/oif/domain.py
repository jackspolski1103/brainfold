"""Provider-independent values exchanged by the service, runtime and adapters.

Only trusted service configuration creates principals, bindings and capability versions.
Requests and model output cannot grant authority or select connection credentials.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Value(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Principal(Value):
    id: str
    organization_id: str
    project_ids: frozenset[str]
    active: bool = True


class OrganizationContext(Value):
    id: str
    content: str
    version: int = Field(ge=1)
    status: Literal["draft", "published", "revoked"] = "draft"


class Connection(Value):
    id: str
    organization_id: str
    url: str
    token_env: str | None = None
    timeout_seconds: float = Field(default=15, gt=0, le=300)


class CapabilityVersion(Value):
    id: str
    version: int = Field(ge=1)
    organization_id: str
    title: str
    instructions: str
    connection_id: str
    tool_name: str
    allowed_projects: frozenset[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    fixed_arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["draft", "published", "revoked"] = "draft"


class AgentDefinition(Value):
    id: str
    organization_id: str
    project_id: str
    instructions: str
    capability_ids: tuple[str, ...]
    argument_bindings: dict[str, dict[str, Any]] = Field(default_factory=dict)


class MemoryNode(Value):
    """An entry in the service's virtual repository, not an operating-system path."""

    organization_id: str
    path: str
    kind: Literal["directory", "file"]
    allowed_projects: frozenset[str] | None = None
    allowed_principals: frozenset[str] | None = None
    content: str = Field(default="", repr=False)
    version: int = Field(default=1, ge=1)
    status: Literal["draft", "published", "revoked"] = "draft"


class Configuration(Value):
    organizations: tuple[OrganizationContext, ...]
    principals: tuple[Principal, ...]
    connections: tuple[Connection, ...]
    capabilities: tuple[CapabilityVersion, ...]
    agents: tuple[AgentDefinition, ...]
    memory_nodes: tuple[MemoryNode, ...] = ()


class ToolDescription(Value):
    name: str
    description: str
    input_schema: dict[str, Any]


class RemoteTool(Value):
    name: str
    input_schema: dict[str, Any]


class ToolCall(Value):
    id: str
    name: str
    arguments: dict[str, Any]


class ErrorInfo(Value):
    code: str
    message: str
    retryable: bool = False


class ToolResult(Value):
    call_id: str
    capability_id: str
    capability_version: int | None = None
    ok: bool
    data: Any = None
    error: ErrorInfo | None = None


class Message(Value):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    provider_items: tuple[dict[str, Any], ...] = Field(default=(), exclude=True, repr=False)


class ModelTurn(Value):
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    provider_items: tuple[dict[str, Any], ...] = Field(default=(), exclude=True, repr=False)


class Session(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    principal_id: str
    agent_id: str
    audience_ids: tuple[str, ...]
    messages: list[Message] = Field(default_factory=list)


class PreparedContext(Value):
    system: str
    tools: tuple[ToolDescription, ...]
    capability_versions: dict[str, int]
    memory_revision: int = 0
    authorization_revision: str = ""


class RunReply(Value):
    session_id: str
    agent_id: str
    text: str
    tool_results: tuple[ToolResult, ...]
    capability_versions: dict[str, int]


class OIFError(Exception):
    """A safe, classified error; its message may be returned to the user/model."""

    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def info(self) -> ErrorInfo:
        return ErrorInfo(code=self.code, message=self.message, retryable=self.retryable)
