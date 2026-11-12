"""Small authenticated HTTP surface for the shared development service."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from oif.auth import DevelopmentTokenAuth
from oif.domain import OIFError, RunReply, Session
from oif.service import SharedService


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_id: str = Field(min_length=1, max_length=200)
    audience_ids: tuple[str, ...] = ()


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=100_000)


def create_app(
    service: SharedService,
    runner: Any,
    auth: DevelopmentTokenAuth,
    *,
    model: str | None = None,
    model_provider: str | None = None,
) -> FastAPI:
    app = FastAPI(title="OIF shared development service")

    def principal(authorization: Annotated[str | None, Header()] = None) -> str:
        identity = auth.authenticate(authorization)
        service.registry.principal(identity)
        return identity

    @app.exception_handler(OIFError)
    async def classified_error(_request: Request, error: OIFError) -> JSONResponse:
        status = {
            "no_autenticado": 401,
            "acceso_denegado": 403,
            "modelo_no_configurado": 503,
            "fuente_no_disponible": 503,
            "tiempo_agotado": 504,
            "argumentos_invalidos": 400,
            "capacidad_modificada": 409,
            "contexto_modificado": 409,
            "ruta_no_disponible": 403,
        }.get(error.code, 400)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
        return JSONResponse(
            status_code=status, content={"error": error.info().model_dump()}, headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, _error: RequestValidationError) -> JSONResponse:
        # Pydantic's default errors include user input; keep request bodies out of errors.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "solicitud_invalida",
                    "message": "La solicitud no es válida.",
                    "retryable": False,
                }
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str | None]:
        return {
            "status": "ok",
            "authentication": "development-token",
            "model": model,
            "model_provider": model_provider,
        }

    @app.get("/v1/agents")
    async def agents(identity: str = Depends(principal)) -> dict[str, list[dict[str, str]]]:
        allowed = []
        for agent in service.registry.agents.values():
            try:
                service.registry.authorize_agent(identity, agent.id)
            except OIFError:
                continue
            allowed.append(
                {
                    "id": agent.id,
                    "organization_id": agent.organization_id,
                    "project_id": agent.project_id,
                }
            )
        return {"agents": allowed}

    @app.post("/v1/sessions", response_model=Session, status_code=201)
    async def create_session(
        request: SessionRequest, identity: str = Depends(principal)
    ) -> Session:
        return service.create_session(identity, request.agent_id, request.audience_ids)

    @app.get("/v1/sessions/{session_id}", response_model=Session)
    async def get_session(session_id: str, identity: str = Depends(principal)) -> Session:
        session = service.get_session(identity, session_id)
        await service.revalidate_memory(session)
        return session

    @app.post("/v1/sessions/{session_id}/messages", response_model=RunReply)
    async def message(
        session_id: str, request: MessageRequest, identity: str = Depends(principal)
    ) -> RunReply:
        session = service.get_session(identity, session_id)
        if runner is None:
            raise OIFError("modelo_no_configurado", "Falta configurar el modelo del servicio.")
        try:
            reply = await runner.turn(session, request.text)
        except OIFError:
            raise
        except Exception:
            # Do not let unclassified provider details reach HTTP errors/server traces.
            raise OIFError("fallo_ejecucion", "No se pudo completar el turno.") from None
        service.authorize_session(session)
        return reply

    @app.post("/v1/sessions/{session_id}/cancel")
    async def cancel(session_id: str, identity: str = Depends(principal)) -> dict[str, bool]:
        service.get_session(identity, session_id)
        cancelled = bool(runner is not None and runner.cancel(session_id))
        return {"cancelled": cancelled}

    return app
