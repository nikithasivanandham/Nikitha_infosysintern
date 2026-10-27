import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.schemas import (
    ResearchRequest,
    ResearchResult,
    Finding,
    FindingKind,
    SourceRecord,
    DisruptionType,
    DataMode,
    ResultStatus,
)


def _make_valid_request_dict() -> dict:
    return {
        "request_id": "req-123",
        "workflow_id": "wf-456",
        "airport_code": "JFK",
        "disruption_type": "weather",
        "disruption_description": "Thunderstorms on approach corridor",
        "affected_flights": ["DAL123"],
        "research_requirements": ["Check wind speed and shear"],
        "planning_objective": "Determine runway acceptance rate impact",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "data_mode": "synthetic",
    }


def _make_valid_result_dict() -> dict:
    return {
        "schema_version": "1.0",
        "request_id": "req-123",
        "workflow_id": "wf-456",
        "agent": "research_agent",
        "status": "success",
        "airport_code": "JFK",
        "data_mode": "synthetic",
        "summary": "Synthetic summary for JFK",
        "weather": None,
        "flights": [],
        "findings": [
            {
                "finding": "Observed wind gust at 25 knots",
                "evidence_refs": ["src-1"],
                "kind": "provider_fact",
                "limitations": [],
            }
        ],
        "sources": [
            {
                "source_id": "src-1",
                "provider": "open-meteo",
                "data_type": "synthetic",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "source_url": "https://example.com",
            }
        ],
        "missing_information": [],
        "errors": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def test_valid_request_and_result():
    req_data = _make_valid_request_dict()
    req = ResearchRequest(**req_data)
    assert req.request_id == "req-123"
    assert req.airport_code == "JFK"

    res_data = _make_valid_result_dict()
    res = ResearchResult(**res_data)
    assert res.request_id == "req-123"
    assert res.agent == "research_agent"
    assert len(res.findings) == 1


def test_airport_code_normalization_and_validation():
    # Normalization: strip and uppercase
    req_data = _make_valid_request_dict()
    req_data["airport_code"] = " del "
    req = ResearchRequest(**req_data)
    assert req.airport_code == "DEL"

    req_data["airport_code"] = "  egll  "
    req_icao = ResearchRequest(**req_data)
    assert req_icao.airport_code == "EGLL"

    # Rejection of invalid codes
    for invalid_code in ["D3L", "AB", "ABCDE", "123", "", "   "]:
        req_data["airport_code"] = invalid_code
        with pytest.raises(ValidationError):
            ResearchRequest(**req_data)


def test_empty_request_id_or_workflow_id_rejected():
    req_data = _make_valid_request_dict()
    req_data["request_id"] = "   "
    with pytest.raises(ValidationError):
        ResearchRequest(**req_data)

    req_data = _make_valid_request_dict()
    req_data["workflow_id"] = ""
    with pytest.raises(ValidationError):
        ResearchRequest(**req_data)


def test_empty_research_requirements_rejected():
    req_data = _make_valid_request_dict()
    req_data["research_requirements"] = []
    with pytest.raises(ValidationError):
        ResearchRequest(**req_data)


def test_provider_fact_without_evidence_refs_rejected():
    with pytest.raises(ValidationError) as exc_info:
        Finding(
            finding="Fact with no evidence",
            evidence_refs=[],
            kind=FindingKind.provider_fact,
            limitations=[],
        )
    assert "evidence_ref" in str(exc_info.value)

    # Inferences can have empty evidence_refs if needed
    inf = Finding(
        finding="Inference without explicit evidence",
        evidence_refs=[],
        kind=FindingKind.inference,
        limitations=["Speculative"],
    )
    assert inf.kind == FindingKind.inference


def test_finding_referencing_missing_source_id_rejected():
    res_data = _make_valid_result_dict()
    res_data["findings"] = [
        {
            "finding": "Fact referencing missing source",
            "evidence_refs": ["unknown-source-999"],
            "kind": "provider_fact",
            "limitations": [],
        }
    ]
    with pytest.raises(ValidationError) as exc_info:
        ResearchResult(**res_data)
    assert "unknown source_id 'unknown-source-999'" in str(exc_info.value)


def test_naive_datetime_rejected():
    # Naive datetime in request as_of
    req_data = _make_valid_request_dict()
    req_data["as_of"] = datetime(2026, 10, 27, 12, 0, 0)  # naive
    with pytest.raises(ValidationError) as exc_info:
        ResearchRequest(**req_data)
    assert "timezone-aware" in str(exc_info.value)

    # Naive datetime in source retrieved_at
    with pytest.raises(ValidationError) as exc_info:
        SourceRecord(
            source_id="src-1",
            provider="open-meteo",
            data_type="forecast",
            retrieved_at=datetime(2026, 10, 27, 12, 0, 0),  # naive
        )
    assert "timezone-aware" in str(exc_info.value)


def test_json_round_trip():
    res_data = _make_valid_result_dict()
    original_result = ResearchResult(**res_data)

    json_str = original_result.model_dump_json()
    validated_result = ResearchResult.model_validate_json(json_str)

    assert original_result == validated_result


def test_examples_load_and_validate():
    examples_dir = Path(__file__).resolve().parent.parent / "examples"

    req_path = examples_dir / "request.json"
    with open(req_path, "r", encoding="utf-8") as f:
        req_json = f.read()
    request_obj = ResearchRequest.model_validate_json(req_json)
    assert request_obj.airport_code == "DEL"
    assert request_obj.data_mode == DataMode.synthetic

    res_path = examples_dir / "response.json"
    with open(res_path, "r", encoding="utf-8") as f:
        res_json = f.read()
    result_obj = ResearchResult.model_validate_json(res_json)
    assert result_obj.airport_code == "DEL"
    assert result_obj.agent == "research_agent"
    assert result_obj.data_mode == DataMode.synthetic
    assert result_obj.status == ResultStatus.success
