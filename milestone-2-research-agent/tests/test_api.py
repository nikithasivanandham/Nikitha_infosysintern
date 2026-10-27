from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.agent import AgentDependencies
from app.config import Settings
from app.main import app, get_agent_dependencies, get_current_settings
from app.schemas import (
    DataMode,
    DisruptionType,
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
from app.tools.flight_tool import FlightToolOutput
from app.tools.weather_tool import WeatherToolOutput

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_clean_environment(monkeypatch):
    """Ensure tests run hermetically with clean settings and no real .env or live keys."""
    # Force clean isolated Settings instance with synthetic mode and no LLM key
    isolated_settings = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY="",
        GEMINI_MODEL="",
        DATA_MODE="synthetic",
    )
    isolated_deps = AgentDependencies(
        settings=isolated_settings,
        llm_factory=lambda: None,
    )

    app.dependency_overrides[get_current_settings] = lambda: isolated_settings
    app.dependency_overrides[get_agent_dependencies] = lambda: isolated_deps

    yield

    app.dependency_overrides.clear()


def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "version" in response.json()


def test_get_capabilities_structure_and_no_secrets():
    fake_secret = "AIzaSySuperSecretNeverExposeInCapabilities"
    secret_settings = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY=fake_secret,
        GEMINI_MODEL="gemini-1.5-flash",
        DATA_MODE="synthetic",
    )
    app.dependency_overrides[get_current_settings] = lambda: secret_settings

    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    data = response.json()

    assert data["schema_version"] == "1.0"
    assert "live" in data["supported_data_modes"]
    assert "synthetic" in data["supported_data_modes"]
    assert data["default_data_mode"] == "synthetic"

    # Tool capabilities
    tool_names = [t["name"] for t in data["tools"]]
    assert "weather_tool" in tool_names
    assert "flight_tool" in tool_names

    # LLM capabilities (provider name and boolean only)
    assert data["llm"]["provider"] == "gemini"
    assert data["llm"]["configured"] is True

    # Supported airports list
    assert "DEL" in data["supported_airports"]
    assert "JFK" in data["supported_airports"]

    # Security assertion: fake key NEVER appears anywhere in the response text
    assert fake_secret not in response.text


def test_post_research_examples_request_synthetic():
    req_path = Path(__file__).resolve().parent.parent / "examples" / "request.json"
    req_data = json.loads(req_path.read_text(encoding="utf-8"))

    response = client.post("/v1/research", json=req_data)
    assert response.status_code == 200

    data = response.json()
    result = ResearchResult.model_validate(data)

    assert result.agent == "research_agent"
    assert result.request_id == req_data["request_id"]
    assert result.workflow_id == req_data["workflow_id"]
    assert result.airport_code == "DEL"
    assert result.data_mode == DataMode.synthetic

    # Response matches key structure of examples/response.json
    res_example_path = Path(__file__).resolve().parent.parent / "examples" / "response.json"
    example_keys = set(json.loads(res_example_path.read_text(encoding="utf-8")).keys())
    assert set(data.keys()) == example_keys


def test_post_research_malformed_json_returns_422_safe_shape():
    response = client.post(
        "/v1/research",
        content="This is not valid json {{{",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "INVALID_REQUEST"
    assert data["error"]["message"] == "Request validation failed"
    assert isinstance(data["error"]["details"], list)


def test_post_research_missing_required_field_returns_422():
    payload = {
        "request_id": "req-1",
        # missing workflow_id
        "airport_code": "DEL",
        "disruption_type": "weather",
        "disruption_description": "Fog",
        "research_requirements": ["Check visibility"],
    }
    response = client.post("/v1/research", json=payload)
    assert response.status_code == 422
    data = response.json()

    assert data["error"]["code"] == "INVALID_REQUEST"
    assert any("workflow_id" in d["field"] for d in data["error"]["details"])


def test_post_research_invalid_airport_code_returns_422():
    payload = {
        "request_id": "req-1",
        "workflow_id": "wf-1",
        "airport_code": "D3L",  # invalid format
        "disruption_type": "weather",
        "disruption_description": "Fog",
        "research_requirements": ["Check visibility"],
    }
    response = client.post("/v1/research", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("airport_code" in d["field"] for d in data["error"]["details"])


def test_post_research_empty_requirements_returns_422():
    payload = {
        "request_id": "req-1",
        "workflow_id": "wf-1",
        "airport_code": "DEL",
        "disruption_type": "weather",
        "disruption_description": "Fog",
        "research_requirements": [],  # invalid min_length=1
    }
    response = client.post("/v1/research", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert any("research_requirements" in d["field"] for d in data["error"]["details"])


def test_post_research_422_never_echoes_sensitive_disruption_description():
    marker_sensitive_text = "SECRET_DISRUPTION_CONFIDENTIAL_PASSENGER_DATA"
    payload = {
        "request_id": "req-1",
        "airport_code": "INVALID_CODE_99",  # triggers validation error
        "disruption_type": "weather",
        "disruption_description": marker_sensitive_text,
        "research_requirements": ["Check visibility"],
    }
    response = client.post("/v1/research", json=payload)
    assert response.status_code == 422
    # Verify the sensitive disruption text is NEVER echoed anywhere in the 422 response
    assert marker_sensitive_text not in response.text


def test_post_research_failed_tools_still_returns_200_with_failed_body():
    # Stub both tools to fail
    def failing_weather(*args, **kwargs):
        err = ErrorInfo(tool="weather_tool", code="PROVIDER_ERROR", message="WX down", retryable=False)
        w = WeatherResult(
            status=WeatherStatus.error,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={},
            units={},
        )
        return WeatherToolOutput(weather=w, source=None, error=err)

    def failing_flight(*args, **kwargs):
        err = ErrorInfo(tool="flight_tool", code="PROVIDER_ERROR", message="Flight down", retryable=False)
        f = FlightResult(
            requested_identifier="AIC101",
            status=FlightLookupStatus.error,
            provider="opensky",
            data={},
        )
        return FlightToolOutput(flights=[f], sources=[], errors=[err])

    failing_deps = AgentDependencies(weather_fn=failing_weather, flight_fn=failing_flight, llm_factory=lambda: None)
    app.dependency_overrides[get_agent_dependencies] = lambda: failing_deps

    req_payload = {
        "request_id": "req-fail-1",
        "workflow_id": "wf-fail-1",
        "airport_code": "DEL",
        "disruption_type": "weather",
        "disruption_description": "Severe storm",
        "affected_flights": ["AIC101"],
        "research_requirements": ["Check wind", "Track flight"],
    }

    response = client.post("/v1/research", json=req_payload)
    # HTTP status reflects transport success (200), body status reflects research failure
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert len(data["errors"]) >= 2


def test_post_research_partial_success_returns_200():
    # Weather succeeds, flight not found
    wx_src = SourceRecord(
        source_id="wx-part-1",
        provider="open-meteo",
        data_type="current",
        retrieved_at=datetime.now(timezone.utc),
    )

    def ok_weather(*args, **kwargs):
        w = WeatherResult(
            status=WeatherStatus.success,
            provider="open-meteo",
            data_type=WeatherDataType.current,
            observations={"visibility": 1000.0},
            units={"visibility": "m"},
            valid_time=datetime.now(timezone.utc),
            source_id="wx-part-1",
        )
        return WeatherToolOutput(weather=w, source=wx_src, error=None)

    def missing_flight(*args, **kwargs):
        f = FlightResult(
            requested_identifier="AIC101",
            status=FlightLookupStatus.not_found,
            provider="opensky",
            data={},
        )
        return FlightToolOutput(flights=[f], sources=[], errors=[])

    part_deps = AgentDependencies(weather_fn=ok_weather, flight_fn=missing_flight, llm_factory=lambda: None)
    app.dependency_overrides[get_agent_dependencies] = lambda: part_deps

    req_payload = {
        "request_id": "req-part-1",
        "workflow_id": "wf-part-1",
        "airport_code": "DEL",
        "disruption_type": "weather",
        "disruption_description": "Visibility issues",
        "affected_flights": ["AIC101"],
        "research_requirements": ["Check visibility", "Track flight"],
    }

    response = client.post("/v1/research", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial_success"
    assert len(data["findings"]) == 1


def test_post_research_unexpected_exception_outside_agent_returns_500():
    def exploding_dependency():
        raise RuntimeError("Fatal outside exception before agent call")

    app.dependency_overrides[get_agent_dependencies] = exploding_dependency

    req_payload = {
        "request_id": "req-500-1",
        "workflow_id": "wf-500-1",
        "airport_code": "DEL",
        "disruption_type": "weather",
        "disruption_description": "Test",
        "research_requirements": ["Check visibility"],
    }

    no_raise_client = TestClient(app, raise_server_exceptions=False)
    response = no_raise_client.post("/v1/research", json=req_payload)
    assert response.status_code == 500
    data = response.json()

    assert data["error"]["code"] == "INTERNAL_ERROR"
    assert data["error"]["message"] == "Internal error"
    # Never leak stack trace or internal exception details
    assert "Traceback" not in response.text
    assert "Fatal outside exception" not in response.text


def test_settings_isolation_with_process_env(monkeypatch):
    """Verify that process environment variables like real/fake keys do not leak into execution."""
    real_looking_fake_key = "AIzaSyRealLookingFakeKeyForIsolationVerification999"
    monkeypatch.setenv("GOOGLE_API_KEY", real_looking_fake_key)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")

    # With isolated fixture in place, the test client executes safely in synthetic mode
    req_path = Path(__file__).resolve().parent.parent / "examples" / "request.json"
    req_data = json.loads(req_path.read_text(encoding="utf-8"))

    response = client.post("/v1/research", json=req_data)
    assert response.status_code == 200
    assert real_looking_fake_key not in response.text


def test_post_research_openapi_example_configured():
    """Verify that OpenAPI documentation provides canonical request body examples for Swagger UI."""
    schema = app.openapi()
    post_op = schema["paths"]["/v1/research"]["post"]
    req_body_content = post_op["requestBody"]["content"]["application/json"]
    assert "examples" in req_body_content
    assert "canonical_example" in req_body_content["examples"]
    canonical_val = req_body_content["examples"]["canonical_example"]["value"]
    assert canonical_val["airport_code"] == "DEL"
    # Ensure canonical example validates against ResearchRequest
    validated_req = ResearchRequest.model_validate(canonical_val)
    assert validated_req.airport_code == "DEL"


def test_post_research_swagger_default_string_triggers_422():
    """Verify that unedited Swagger UI default 'string' value for airport_code is cleanly rejected with 422."""
    raw_swagger_default = {
        "request_id": "string",
        "workflow_id": "string",
        "airport_code": "string",
        "disruption_type": "weather",
        "disruption_description": "string",
        "affected_flights": ["string"],
        "research_requirements": ["string"],
        "planning_objective": "string",
        "as_of": "2026-10-28T00:00:00Z",
        "data_mode": "synthetic",
    }
    response = client.post("/v1/research", json=raw_swagger_default)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "INVALID_REQUEST"
    details = data["error"]["details"]
    assert any(
        d["field"] == "airport_code"
        and "3 or 4 alphabetic characters" in d["message"]
        for d in details
    )

