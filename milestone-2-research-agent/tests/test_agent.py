from datetime import datetime, timezone
from pathlib import Path
import pytest

from app.agent import AgentDependencies, run_research_agent
from app.schemas import (
    DataMode,
    DisruptionType,
    ErrorInfo,
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
from app.tools.flight_tool import FlightToolOutput
from app.tools.weather_tool import WeatherToolOutput


def _make_req(requirements=None, affected_flights=None, mode=DataMode.synthetic) -> ResearchRequest:
    return ResearchRequest(
        request_id="req-agent-test-1",
        workflow_id="wf-agent-test-1",
        airport_code="DEL",
        disruption_type=DisruptionType.weather,
        disruption_description="Adverse conditions",
        affected_flights=affected_flights or [],
        research_requirements=requirements or ["Assess weather forecast"],
        data_mode=mode,
    )


def test_agent_both_tools_succeed():
    # Weather and flight both succeed
    wx_source = SourceRecord(
        source_id="wx-src-1",
        provider="open-meteo",
        data_type="current",
        retrieved_at=datetime.now(timezone.utc),
    )
    flt_source = SourceRecord(
        source_id="flt-src-1",
        provider="opensky",
        data_type="current",
        retrieved_at=datetime.now(timezone.utc),
    )

    def stub_weather(*args, **kwargs):
        res = WeatherResult(
            status=WeatherStatus.success,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={"temperature_2m": 25.0, "visibility": 9000.0},
            units={"temperature_2m": "°C", "visibility": "m"},
            valid_time=datetime.now(timezone.utc),
            source_id="wx-src-1",
        )
        return WeatherToolOutput(weather=res, source=wx_source, error=None)

    def stub_flight(*args, **kwargs):
        flt = FlightResult(
            requested_identifier="AIC101",
            status=FlightLookupStatus.found,
            provider="opensky",
            data={"baro_altitude": 4000.0, "velocity": 150.0, "on_ground": False},
            data_timestamp=datetime.now(timezone.utc),
            source_id="flt-src-1",
        )
        return FlightToolOutput(flights=[flt], sources=[flt_source], errors=[])

    deps = AgentDependencies(weather_fn=stub_weather, flight_fn=stub_flight)
    req = _make_req(
        requirements=["Check weather and forecast", "Track flight positions"],
        affected_flights=["AIC101"],
    )

    res = run_research_agent(req, deps=deps)
    assert res.status == ResultStatus.success
    assert len(res.findings) == 2
    assert res.weather is not None
    assert len(res.flights) == 1
    assert len(res.sources) == 2


def test_agent_only_weather_succeeds():
    wx_source = SourceRecord(
        source_id="wx-src-2",
        provider="open-meteo",
        data_type="current",
        retrieved_at=datetime.now(timezone.utc),
    )

    def stub_weather(*args, **kwargs):
        res = WeatherResult(
            status=WeatherStatus.success,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={"visibility": 5000.0},
            units={"visibility": "m"},
            valid_time=datetime.now(timezone.utc),
            source_id="wx-src-2",
        )
        return WeatherToolOutput(weather=res, source=wx_source, error=None)

    def stub_flight(*args, **kwargs):
        flt = FlightResult(
            requested_identifier="AIC101",
            status=FlightLookupStatus.not_found,
            provider="opensky",
            data={"note": "not found"},
            data_timestamp=None,
            source_id=None,
        )
        return FlightToolOutput(flights=[flt], sources=[], errors=[])

    deps = AgentDependencies(weather_fn=stub_weather, flight_fn=stub_flight)
    req = _make_req(
        requirements=["Check visibility", "Check aircraft status"],
        affected_flights=["AIC101"],
    )

    res = run_research_agent(req, deps=deps)
    assert res.status == ResultStatus.partial_success
    assert any("not found" in g for g in res.missing_information)
    assert len(res.findings) == 1


def test_agent_only_flight_succeeds():
    flt_source = SourceRecord(
        source_id="flt-src-3",
        provider="opensky",
        data_type="current",
        retrieved_at=datetime.now(timezone.utc),
    )

    def stub_weather(*args, **kwargs):
        err = ErrorInfo(
            tool="weather_tool",
            code="PROVIDER_ERROR",
            message="Weather service unavailable",
            retryable=True,
        )
        res = WeatherResult(
            status=WeatherStatus.error,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={},
            units={},
            valid_time=None,
            source_id=None,
        )
        return WeatherToolOutput(weather=res, source=None, error=err)

    def stub_flight(*args, **kwargs):
        flt = FlightResult(
            requested_identifier="6E204",
            status=FlightLookupStatus.found,
            provider="opensky",
            data={"baro_altitude": 0.0, "velocity": 0.0, "on_ground": True},
            data_timestamp=datetime.now(timezone.utc),
            source_id="flt-src-3",
        )
        return FlightToolOutput(flights=[flt], sources=[flt_source], errors=[])

    deps = AgentDependencies(weather_fn=stub_weather, flight_fn=stub_flight)
    req = _make_req(
        requirements=["Check wind", "Track flight"],
        affected_flights=["6E204"],
    )

    res = run_research_agent(req, deps=deps)
    assert res.status == ResultStatus.partial_success
    assert len(res.findings) == 1
    assert any("Weather evidence unavailable" in g for g in res.missing_information)


def test_agent_both_fail():
    def stub_weather(*args, **kwargs):
        err = ErrorInfo(tool="weather_tool", code="PROVIDER_ERROR", message="WX down", retryable=False)
        res = WeatherResult(
            status=WeatherStatus.error,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={},
            units={},
            valid_time=None,
            source_id=None,
        )
        return WeatherToolOutput(weather=res, source=None, error=err)

    def stub_flight(*args, **kwargs):
        err = ErrorInfo(tool="flight_tool", code="PROVIDER_ERROR", message="OpenSky down", retryable=False)
        flt = FlightResult(
            requested_identifier="AIC101",
            status=FlightLookupStatus.error,
            provider="opensky",
            data={},
            data_timestamp=None,
            source_id=None,
        )
        return FlightToolOutput(flights=[flt], sources=[], errors=[err])

    deps = AgentDependencies(weather_fn=stub_weather, flight_fn=stub_flight)
    req = _make_req(
        requirements=["Check weather", "Check flight"],
        affected_flights=["AIC101"],
    )

    res = run_research_agent(req, deps=deps)
    assert res.status == ResultStatus.failed
    assert len(res.errors) >= 2
    assert len(res.findings) == 0


def test_agent_requirement_matching_neither_tool():
    req = _make_req(requirements=["Analyze passenger baggage processing times"])
    res = run_research_agent(req)
    assert res.status == ResultStatus.no_data
    assert any("Unsupported or unrecognized requirement" in m for m in res.missing_information)


def test_agent_delay_schedule_requirement_unsupported():
    req = _make_req(
        requirements=["Check commercial schedule and flight delay status"],
        affected_flights=["AIC101"],
        mode=DataMode.synthetic,
    )
    res = run_research_agent(req)
    # The requirement asks for schedule/delay which OpenSky cannot provide
    assert any(f.status == FlightLookupStatus.unsupported for f in res.flights)
    assert any("unsupported" in m.lower() for m in res.missing_information)


def test_agent_synthetic_mode_zero_network_and_limitations_mention_synthetic():
    req = _make_req(
        requirements=["Check wind and visibility", "Track aircraft state"],
        affected_flights=["AIC101"],
        mode=DataMode.synthetic,
    )
    res = run_research_agent(req)
    assert res.status == ResultStatus.success
    assert len(res.findings) >= 2
    for finding in res.findings:
        assert any("synthetic" in lim.lower() for lim in finding.limitations)
        assert len(finding.evidence_refs) > 0


def test_agent_every_finding_evidence_ref_exists_in_sources():
    req = _make_req(
        requirements=["Check wind", "Track flight"],
        affected_flights=["AIC101"],
        mode=DataMode.synthetic,
    )
    res = run_research_agent(req)
    source_ids = {s.source_id for s in res.sources}
    for finding in res.findings:
        for ref in finding.evidence_refs:
            assert ref in source_ids


def test_agent_unexpected_exception_inside_stub_never_raises():
    def exploding_weather(*args, **kwargs):
        raise RuntimeError("Catastrophic hardware fault!")

    deps = AgentDependencies(weather_fn=exploding_weather)
    req = _make_req(requirements=["Check weather"])

    # Must NEVER raise
    res = run_research_agent(req, deps=deps)
    assert res.status == ResultStatus.failed
    assert any(e.code in ("UNEXPECTED_ERROR", "INTERNAL_ERROR") for e in res.errors)


def test_agent_examples_request_runs_end_to_end_and_roundtrips():
    examples_dir = Path(__file__).resolve().parent.parent / "examples"
    req_file = examples_dir / "request.json"

    with open(req_file, "r", encoding="utf-8") as f:
        req_json = f.read()

    req = ResearchRequest.model_validate_json(req_json)
    res = run_research_agent(req)

    assert res.status in (ResultStatus.success, ResultStatus.partial_success)
    assert res.agent == "research_agent"
    assert res.airport_code == "DEL"
    assert res.data_mode == DataMode.synthetic

    # JSON round trip validation
    res_json = res.model_dump_json(indent=2)
    validated = ResearchResult.model_validate_json(res_json)
    assert validated == res
