"""LangGraph pipeline for Airport Operations Research Agent (Deterministic / No LLM)."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Callable, TypedDict
from langgraph.graph import END, START, StateGraph

from app.schemas import (
    DataMode,
    ErrorInfo,
    Finding,
    FindingKind,
    FlightLookupStatus,
    FlightResult,
    ResearchRequest,
    ResearchResult,
    ResultStatus,
    SourceRecord,
    WeatherDataType,
    WeatherResult,
    WeatherStatus,
)
from app.tools.flight_tool import FlightToolOutput, get_flights
from app.tools.weather_tool import WeatherToolOutput, get_weather

WEATHER_KEYWORDS = [
    "weather",
    "wind",
    "visibility",
    "rain",
    "precipitation",
    "forecast",
    "temperature",
    "cloud",
    "gust",
]

FLIGHT_KEYWORDS = [
    "flight",
    "aircraft",
    "aircraft state",
    "status",
    "delay",
    "schedule",
    "eta",
    "arrival",
    "departure",
]


class ResearchState(TypedDict, total=False):
    """Execution state passed through the LangGraph pipeline."""

    request: ResearchRequest
    required_tools: list[str]
    weather_output: WeatherToolOutput | None
    flight_output: FlightToolOutput | None
    findings: list[Finding]
    sources: list[SourceRecord]
    missing_information: list[str]
    errors: list[ErrorInfo]
    status: ResultStatus
    summary: str
    result: ResearchResult | None
    llm: Any
    # Tool callbacks injected for execution/testing
    weather_fn: Callable[..., WeatherToolOutput]
    flight_fn: Callable[..., FlightToolOutput]
    timeout_seconds: float


def validate_request(state: ResearchState) -> dict[str, Any]:
    """Validate the incoming request. Route to failure if invalid."""
    req = state.get("request")
    if req is None or not isinstance(req, ResearchRequest):
        err = ErrorInfo(
            tool="validate_request",
            code="INVALID_REQUEST",
            message="Research request is missing or invalid.",
            retryable=False,
        )
        return {
            "errors": [err],
            "status": ResultStatus.failed,
            "summary": "Request validation failed.",
        }
    return {}


def determine_required_tools(state: ResearchState) -> dict[str, Any]:
    """Map research requirements to tools by case-insensitive keyword match."""
    req = state["request"]
    required_tools: set[str] = set()
    missing_info: list[str] = list(state.get("missing_information", []))

    for item in req.research_requirements:
        item_lower = item.lower()
        matched = False

        for kw in WEATHER_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", item_lower):
                required_tools.add("weather")
                matched = True
                break

        for kw in FLIGHT_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", item_lower):
                required_tools.add("flight")
                matched = True
                break

        if not matched:
            missing_info.append(f"Unsupported or unrecognized requirement: {item}")

    # Also require flight tool if affected_flights list is non-empty
    if req.affected_flights:
        required_tools.add("flight")

    return {
        "required_tools": sorted(list(required_tools)),
        "missing_information": missing_info,
    }


def collect_weather(state: ResearchState) -> dict[str, Any]:
    """Execute the weather tool if required."""
    req = state["request"]
    weather_fn = state.get("weather_fn", get_weather)
    timeout = state.get("timeout_seconds", 30.0)

    try:
        output = weather_fn(
            airport_code=req.airport_code,
            as_of=req.as_of,
            mode=req.data_mode,
            timeout_seconds=timeout,
        )
        return {"weather_output": output}
    except Exception as exc:
        err = ErrorInfo(
            tool="weather_tool",
            code="UNEXPECTED_ERROR",
            message=f"Weather tool invocation failed: {str(exc)}",
            retryable=False,
        )
        w_res = WeatherResult(
            status=WeatherStatus.error,
            provider="unknown",
            data_type=WeatherDataType.current if req.data_mode == DataMode.live else WeatherDataType.synthetic,
            observations={},
            units={},
            valid_time=None,
            source_id=None,
        )
        return {"weather_output": WeatherToolOutput(weather=w_res, source=None, error=err)}


def collect_flight_data(state: ResearchState) -> dict[str, Any]:
    """Execute the flight tool if required."""
    req = state["request"]
    flight_fn = state.get("flight_fn", get_flights)
    timeout = state.get("timeout_seconds", 30.0)

    try:
        output = flight_fn(
            airport_code=req.airport_code,
            flight_identifiers=req.affected_flights,
            research_requirements=req.research_requirements,
            mode=req.data_mode,
            timeout_seconds=timeout,
        )
        return {"flight_output": output}
    except Exception as exc:
        err = ErrorInfo(
            tool="flight_tool",
            code="UNEXPECTED_ERROR",
            message=f"Flight tool invocation failed: {str(exc)}",
            retryable=False,
        )
        f_results = [
            FlightResult(
                requested_identifier=f_id,
                status=FlightLookupStatus.error,
                provider="unknown",
                data={"error": str(exc)},
                data_timestamp=None,
                source_id=None,
            )
            for f_id in req.affected_flights
        ]
        return {"flight_output": FlightToolOutput(flights=f_results, sources=[], errors=[err])}


def normalize_and_validate_evidence(state: ResearchState) -> dict[str, Any]:
    """Merge sources and errors; record missing information for unavailable items."""
    sources: list[SourceRecord] = []
    errors: list[ErrorInfo] = list(state.get("errors", []))
    missing_info: list[str] = list(state.get("missing_information", []))
    seen_source_ids: set[str] = set()

    weather_out = state.get("weather_output")
    if weather_out:
        if weather_out.source and weather_out.source.source_id not in seen_source_ids:
            sources.append(weather_out.source)
            seen_source_ids.add(weather_out.source.source_id)
        if weather_out.error:
            errors.append(weather_out.error)
        if weather_out.weather.status in (WeatherStatus.unavailable, WeatherStatus.error):
            missing_info.append(
                f"Weather evidence unavailable: {weather_out.error.message if weather_out.error else 'Unknown error'}."
            )

    flight_out = state.get("flight_output")
    if flight_out:
        for s in flight_out.sources:
            if s.source_id not in seen_source_ids:
                sources.append(s)
                seen_source_ids.add(s.source_id)
        errors.extend(flight_out.errors)

        for flt in flight_out.flights:
            if flt.status == FlightLookupStatus.not_found:
                missing_info.append(f"Flight '{flt.requested_identifier}' not found in live aircraft states.")
            elif flt.status == FlightLookupStatus.unsupported:
                unsupported_desc = flt.data.get("unsupported_fields", [])
                missing_info.append(
                    f"Flight '{flt.requested_identifier}' attribute query unsupported: {unsupported_desc}."
                )
            elif flt.status == FlightLookupStatus.error:
                missing_info.append(
                    f"Flight '{flt.requested_identifier}' lookup encountered error: {flt.data.get('error', 'unknown error')}."
                )

    return {
        "sources": sources,
        "errors": errors,
        "missing_information": missing_info,
    }


def build_result(state: ResearchState) -> dict[str, Any]:
    """Construct findings deterministically from gathered tool data and determine status."""
    req = state["request"]
    sources = state.get("sources", [])
    errors = state.get("errors", [])
    missing_info = state.get("missing_information", [])
    required_tools = state.get("required_tools", [])
    is_synth = req.data_mode == DataMode.synthetic

    findings: list[Finding] = []
    weather_out = state.get("weather_output")
    flight_out = state.get("flight_output")

    weather_has_evidence = False
    flight_has_evidence = False

    # 1. Weather findings
    if weather_out and weather_out.weather.status == WeatherStatus.success and weather_out.source:
        weather_has_evidence = True
        obs = weather_out.weather.observations
        units = weather_out.weather.units
        wx_sid = weather_out.source.source_id

        temp = obs.get("temperature_2m")
        temp_u = units.get("temperature_2m", "°C")
        vis = obs.get("visibility")
        vis_u = units.get("visibility", "m")
        wind_spd = obs.get("wind_speed_10m")
        wind_u = units.get("wind_speed_10m", "km/h")
        wind_dir = obs.get("wind_direction_10m")

        details = []
        if vis is not None:
            details.append(f"visibility {vis} {vis_u}")
        if wind_spd is not None and wind_dir is not None:
            details.append(f"wind {wind_spd} {wind_u} at {wind_dir}°")
        if temp is not None:
            details.append(f"temperature {temp} {temp_u}")

        summary_wx = f"Surface weather at {req.airport_code}: " + ", ".join(details) if details else f"Weather observations retrieved for {req.airport_code}."

        limitations = [
            "Open-Meteo numerical forecast/model data; not official METAR or certified aviation observation."
        ]
        if is_synth:
            limitations.append("Synthetic test fixture data.")

        findings.append(
            Finding(
                finding=summary_wx,
                evidence_refs=[wx_sid],
                kind=FindingKind.provider_fact,
                limitations=limitations,
            )
        )

    # 2. Flight findings
    if flight_out:
        found_flights = [f for f in flight_out.flights if f.status == FlightLookupStatus.found and f.source_id]
        if found_flights:
            flight_has_evidence = True

        for flt in found_flights:
            assert flt.source_id is not None
            f_data = flt.data
            alt = f_data.get("baro_altitude")
            spd = f_data.get("velocity")
            ground = f_data.get("on_ground")

            state_desc = "on ground" if ground else f"airborne at baro altitude {alt}m (velocity {spd} m/s)"
            finding_text = f"Flight '{flt.requested_identifier}' live state: {state_desc}."

            limitations = [
                "OpenSky provides live aircraft state vectors only; no commercial schedule or delay data."
            ]
            if is_synth:
                limitations.append("Synthetic test fixture data.")

            findings.append(
                Finding(
                    finding=finding_text,
                    evidence_refs=[flt.source_id],
                    kind=FindingKind.provider_fact,
                    limitations=limitations,
                )
            )

    # 3. Determine status
    if not required_tools:
        # No tools were matched or required
        status = ResultStatus.no_data
    else:
        req_wx = "weather" in required_tools
        req_flt = "flight" in required_tools

        wx_ok = weather_has_evidence if req_wx else True
        flt_ok = flight_has_evidence if req_flt else True

        if wx_ok and flt_ok:
            status = ResultStatus.success
        elif weather_has_evidence or flight_has_evidence:
            status = ResultStatus.partial_success
        else:
            # Check if tools completely errored vs found nothing
            has_errors = len(errors) > 0
            status = ResultStatus.failed if has_errors else ResultStatus.no_data

    # 4. Deterministic summary
    finding_texts = [f.finding for f in findings]
    if findings:
        summary_intro = f"Operational research summary for {req.airport_code} [{status.value}]: "
        summary_body = " ".join(finding_texts)
        if missing_info:
            summary_body += f" Gaps noted: {len(missing_info)} item(s) unfulfilled or missing."
        summary = summary_intro + summary_body
    else:
        summary = (
            f"Operational research for {req.airport_code} concluded with status '{status.value}'. "
            f"No verified evidence findings could be compiled."
        )

    return {
        "findings": findings,
        "status": status,
        "summary": summary,
    }


def synthesize_research_result(state: ResearchState) -> dict[str, Any]:
    """Optionally perform LLM synthesis if evidence exists and an LLM is provided."""
    from app.synthesis import synthesize

    req = state["request"]
    current_status = state.get("status")

    # Skip LLM entirely when there is no evidence (no_data or failed)
    if current_status in (ResultStatus.no_data, ResultStatus.failed):
        return {}

    llm = state.get("llm")
    if llm is None:
        # No LLM configured or provided: keep deterministic summary, no error
        return {}

    deterministic_findings = list(state.get("findings", []))
    sources = list(state.get("sources", []))
    missing_info = list(state.get("missing_information", []))
    errors = list(state.get("errors", []))

    outcome = synthesize(
        llm=llm,
        request=req,
        findings=deterministic_findings,
        sources=sources,
        missing_information=missing_info,
        errors=errors,
    )

    if outcome.used_llm and outcome.summary:
        # Accepted: replace summary with LLM summary
        new_summary = outcome.summary

        # Merge findings: keep deterministic provider_fact findings authoritative,
        # append ONLY LLM findings with kind == 'inference'
        merged_findings = list(deterministic_findings)
        known_source_ids = {s.source_id for s in sources}

        if outcome.findings:
            for f in outcome.findings:
                if f.kind == FindingKind.inference:
                    # Verify evidence_refs all exist in known sources
                    if all(ref in known_source_ids for ref in f.evidence_refs):
                        merged_findings.append(f)

        return {
            "summary": new_summary,
            "findings": merged_findings,
        }
    else:
        # Rejected or failed: keep deterministic summary, record error and missing_info
        updates: dict[str, Any] = {}
        if outcome.error:
            errors.append(outcome.error)
            updates["errors"] = errors
            missing_info.append("LLM synthesis unavailable; deterministic summary used.")
            updates["missing_information"] = missing_info
        return updates


def validate_result(state: ResearchState) -> dict[str, Any]:
    """Construct and validate the final ResearchResult contract."""
    req = state["request"]
    weather_res = state["weather_output"].weather if state.get("weather_output") else None
    flight_res_list = state["flight_output"].flights if state.get("flight_output") else []

    final_result = ResearchResult(
        schema_version="1.0",
        request_id=req.request_id,
        workflow_id=req.workflow_id,
        agent="research_agent",
        status=state["status"],
        airport_code=req.airport_code,
        data_mode=req.data_mode,
        summary=state["summary"],
        weather=weather_res,
        flights=flight_res_list,
        findings=state.get("findings", []),
        sources=state.get("sources", []),
        missing_information=state.get("missing_information", []),
        errors=state.get("errors", []),
        created_at=datetime.now(timezone.utc),
    )
    return {"result": final_result}


# Conditional routing functions
def _route_after_validation(state: ResearchState) -> str:
    if state.get("status") == ResultStatus.failed:
        return "validate_result"
    return "determine_required_tools"


def _route_to_weather(state: ResearchState) -> str:
    return "collect_weather" if "weather" in state.get("required_tools", []) else "normalize_and_validate_evidence"


def _route_to_flight(state: ResearchState) -> str:
    return "collect_flight_data" if "flight" in state.get("required_tools", []) else "normalize_and_validate_evidence"


def build_research_graph() -> Any:
    """Build the LangGraph pipeline for the research agent."""
    graph = StateGraph(ResearchState)

    graph.add_node("validate_request", validate_request)
    graph.add_node("determine_required_tools", determine_required_tools)
    graph.add_node("collect_weather", collect_weather)
    graph.add_node("collect_flight_data", collect_flight_data)
    graph.add_node("normalize_and_validate_evidence", normalize_and_validate_evidence)
    graph.add_node("build_result", build_result)
    graph.add_node("synthesize_research_result", synthesize_research_result)
    graph.add_node("validate_result", validate_result)

    graph.add_edge(START, "validate_request")

    graph.add_conditional_edges(
        "validate_request",
        _route_after_validation,
        {
            "determine_required_tools": "determine_required_tools",
            "validate_result": "validate_result",
        },
    )

    # Fork to weather and flight collection independently
    graph.add_conditional_edges(
        "determine_required_tools",
        _route_to_weather,
        {
            "collect_weather": "collect_weather",
            "normalize_and_validate_evidence": "normalize_and_validate_evidence",
        },
    )

    graph.add_conditional_edges(
        "determine_required_tools",
        _route_to_flight,
        {
            "collect_flight_data": "collect_flight_data",
            "normalize_and_validate_evidence": "normalize_and_validate_evidence",
        },
    )

    graph.add_edge("collect_weather", "normalize_and_validate_evidence")
    graph.add_edge("collect_flight_data", "normalize_and_validate_evidence")
    graph.add_edge("normalize_and_validate_evidence", "build_result")
    graph.add_edge("build_result", "synthesize_research_result")
    graph.add_edge("synthesize_research_result", "validate_result")
    graph.add_edge("validate_result", END)

    return graph.compile()
