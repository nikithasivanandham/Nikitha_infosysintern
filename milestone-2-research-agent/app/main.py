"""FastAPI application for Airport Operations Coordination Engine - Research Agent."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import Any

from fastapi import Body, Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


from app import __version__
from app.agent import AgentDependencies, run_research_agent
from app.config import Settings, settings as global_settings
from app.providers.llm_provider import is_llm_configured
from app.schemas import SCHEMA_VERSION, ResearchRequest, ResearchResult

# Configure structured application logger
logger = logging.getLogger("app.research_agent")


def get_current_settings() -> Settings:
    """Dependency providing application settings."""
    return global_settings


def get_agent_dependencies(
    current_settings: Settings = Depends(get_current_settings),
) -> AgentDependencies:
    """Dependency providing agent dependencies."""
    return AgentDependencies(settings=current_settings)


# Load examples for OpenAPI documentation
_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
try:
    _REQ_EXAMPLE = json.loads((_EXAMPLES_DIR / "request.json").read_text(encoding="utf-8"))
    _RES_EXAMPLE = json.loads((_EXAMPLES_DIR / "response.json").read_text(encoding="utf-8"))
except Exception:
    _REQ_EXAMPLE = None
    _RES_EXAMPLE = None

# Load bundled airport IATA codes
try:
    _AIRPORTS_DATA = json.loads(
        (Path(__file__).resolve().parent / "data" / "airports.json").read_text(encoding="utf-8")
    )
    _SUPPORTED_AIRPORTS = sorted(list({a["iata"].upper() for a in _AIRPORTS_DATA}))
except Exception:
    _SUPPORTED_AIRPORTS = ["DEL", "BOM", "BLR", "JFK", "LHR"]


app = FastAPI(
    title="Airport Operations Coordination Engine - Research Agent",
    version=__version__,
    description=(
        "Advisory decision support research agent for weather and flight evidence. "
        "Strictly advisory; never allocates gates/runways, approves actions, or controls aircraft."
    ),
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Override validation error handler with a safe, stable error shape without echoing input."""
    details = []
    for error in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in error.get("loc", []) if loc != "body")
        details.append({
            "field": field_loc or "body",
            "message": error.get("msg", "Invalid value"),
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Request validation failed",
                "details": details,
            }
        },
    )


@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected unhandled exceptions outside the agent."""
    logger.error("Unhandled server exception: %s", type(exc).__name__, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal error",
            }
        },
    )


@app.get("/health")
def get_health() -> dict[str, str]:
    """Health check endpoint returning application status and version."""
    return {
        "status": "healthy",
        "version": __version__,
    }


@app.get("/v1/capabilities")
def get_capabilities(
    current_settings: Settings = Depends(get_current_settings),
) -> dict[str, Any]:
    """Return runtime service capabilities, supported modes, tools, and airport list.

    Never returns API keys, secrets, or sensitive configuration values.
    """
    return {
        "version": __version__,
        "schema_version": SCHEMA_VERSION,
        "supported_data_modes": ["live", "synthetic"],
        "default_data_mode": current_settings.DATA_MODE,
        "tools": [
            {
                "name": "weather_tool",
                "provider": "open-meteo",
                "live_supported": True,
                "synthetic_supported": True,
                "notes": "forecast/current model data, not METAR",
            },
            {
                "name": "flight_tool",
                "provider": "opensky",
                "live_supported": True,
                "synthetic_supported": True,
                "notes": "live aircraft state by exact callsign only; no schedule or delay data",
            },
        ],
        "llm": {
            "provider": current_settings.LLM_PROVIDER,
            "configured": is_llm_configured(current_settings),
        },
        "supported_airports": _SUPPORTED_AIRPORTS,
    }


@app.post(
    "/v1/research",
    response_model=ResearchResult,
    responses={
        200: {
            "description": "Research completed (status reflects research outcome: success, partial_success, no_data, or failed).",
            "content": {
                "application/json": {
                    "example": _RES_EXAMPLE,
                }
            },
        },
        422: {
            "description": "Request validation error.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_REQUEST",
                            "message": "Request validation failed",
                            "details": [
                                {"field": "airport_code", "message": "airport_code must be 3 or 4 alphabetic characters"}
                            ],
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal server error.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Internal error",
                        }
                    }
                }
            },
        },
    },
)
def post_research(
    research_request: ResearchRequest = Body(
        openapi_examples={
            "canonical_example": {
                "summary": "Canonical research request (Delhi winter fog scenario)",
                "description": "Standard operational research request for DEL using synthetic fixtures.",
                "value": _REQ_EXAMPLE,
            }
        } if _REQ_EXAMPLE else None
    ),
    deps: AgentDependencies = Depends(get_agent_dependencies),
) -> ResearchResult:

    """Execute synchronous research workflow over weather and flight evidence.

    HTTP status 200 indicates successful transport and validation; the response body
    status field indicates the research result (success, partial_success, no_data, failed).
    """
    start_time = time.perf_counter()

    # Synchronous threadpool execution via FastAPI
    result = run_research_agent(research_request, deps=deps)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Safe logging: log ONLY operational metadata and performance metrics
    # NEVER log disruption_description, API keys, or raw payloads
    log_level = getattr(logging, deps.settings.LOG_LEVEL.upper(), logging.INFO)
    logger.log(
        log_level,
        "Research executed: request_id=%s workflow_id=%s airport_code=%s data_mode=%s status=%s duration_ms=%.2f",
        result.request_id,
        result.workflow_id,
        result.airport_code,
        result.data_mode.value,
        result.status.value,
        duration_ms,
    )

    return result
