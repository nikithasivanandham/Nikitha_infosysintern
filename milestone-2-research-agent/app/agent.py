"""Public entry point for the Airport Operations Research Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from app.config import Settings, settings as global_settings
from app.graph import build_research_graph
from app.providers.llm_provider import LLMConfigError, get_llm, is_llm_configured
from app.schemas import (
    DataMode,
    ErrorInfo,
    ResearchRequest,
    ResearchResult,
    ResultStatus,
)
from app.tools.flight_tool import FlightToolOutput, get_flights
from app.tools.weather_tool import WeatherToolOutput, get_weather


@dataclass
class AgentDependencies:
    """Injectable dependencies for research agent execution."""

    weather_fn: Callable[..., WeatherToolOutput] = get_weather
    flight_fn: Callable[..., FlightToolOutput] = get_flights
    settings: Settings = field(default_factory=lambda: global_settings)
    llm_factory: Callable[[], Any] | None = None


_COMPILED_GRAPH = None


def _get_graph():
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_research_graph()
    return _COMPILED_GRAPH


def run_research_agent(
    request: ResearchRequest,
    deps: AgentDependencies | None = None,
) -> ResearchResult:
    """Execute the Research Agent pipeline for a given request.

    Never raises exceptions to callers; any unhandled error is converted
    into a safe failed ResearchResult contract.
    """
    if deps is None:
        deps = AgentDependencies()

    llm_instance = None
    llm_init_error: ErrorInfo | None = None

    if deps.llm_factory is not None:
        try:
            llm_instance = deps.llm_factory()
        except LLMConfigError as exc:
            llm_init_error = ErrorInfo(
                tool="llm",
                code="LLM_CONFIG_ERROR",
                message=exc.message,
                retryable=False,
            )
        except Exception as exc:
            llm_init_error = ErrorInfo(
                tool="llm",
                code="LLM_UNAVAILABLE",
                message=f"Failed to instantiate LLM: {type(exc).__name__}",
                retryable=False,
            )
    else:
        # Default behavior: if configured, instantiate via get_llm
        if is_llm_configured(deps.settings):
            try:
                llm_instance = get_llm(deps.settings)
            except LLMConfigError as exc:
                llm_init_error = ErrorInfo(
                    tool="llm",
                    code="LLM_CONFIG_ERROR",
                    message=exc.message,
                    retryable=False,
                )
            except Exception as exc:
                llm_init_error = ErrorInfo(
                    tool="llm",
                    code="LLM_UNAVAILABLE",
                    message=f"Failed to instantiate LLM: {type(exc).__name__}",
                    retryable=False,
                )

    try:
        graph = _get_graph()

        initial_errors = [llm_init_error] if llm_init_error else []
        initial_missing = (
            ["LLM synthesis unavailable; deterministic summary used."]
            if llm_init_error
            else []
        )

        initial_state = {
            "request": request,
            "llm": llm_instance,
            "weather_fn": deps.weather_fn,
            "flight_fn": deps.flight_fn,
            "timeout_seconds": float(deps.settings.REQUEST_TIMEOUT_SECONDS),
            "missing_information": initial_missing,
            "errors": initial_errors,
        }

        final_state = graph.invoke(initial_state)
        result = final_state.get("result")
        if isinstance(result, ResearchResult):
            return result

        raise RuntimeError("Pipeline failed to produce a valid ResearchResult object.")

    except Exception as exc:
        err = ErrorInfo(
            tool="agent",
            code="INTERNAL_ERROR",
            message=f"An unexpected internal error occurred: {type(exc).__name__}",
            retryable=False,
        )

        req_id = getattr(request, "request_id", "unknown-request")
        wf_id = getattr(request, "workflow_id", "unknown-workflow")
        airport = getattr(request, "airport_code", "ZZZ")
        mode = getattr(request, "data_mode", DataMode.synthetic)

        return ResearchResult(
            schema_version="1.0",
            request_id=req_id,
            workflow_id=wf_id,
            agent="research_agent",
            status=ResultStatus.failed,
            airport_code=airport,
            data_mode=mode,
            summary="Research execution failed due to an unexpected internal error.",
            weather=None,
            flights=[],
            findings=[],
            sources=[],
            missing_information=["Execution failed before evidence could be gathered."],
            errors=[err],
            created_at=datetime.now(timezone.utc),
        )
