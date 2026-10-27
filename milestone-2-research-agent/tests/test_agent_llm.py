from datetime import datetime, timezone
import pytest

from app.agent import AgentDependencies, run_research_agent
from app.config import Settings
from app.providers.llm_provider import LLMConfigError
from app.schemas import (
    DataMode,
    DisruptionType,
    FindingKind,
    ResearchRequest,
    ResultStatus,
)
from app.synthesis import LLMFinding, LLMSynthesis
from tests.test_synthesis import StubLLM


def _make_req(mode=DataMode.synthetic) -> ResearchRequest:
    return ResearchRequest(
        request_id="req-test-llm-1",
        workflow_id="wf-test-llm-1",
        airport_code="DEL",
        disruption_type=DisruptionType.weather,
        disruption_description="Dense fog morning bank",
        affected_flights=["AIC101"],
        research_requirements=["Check visibility", "Check aircraft position"],
        data_mode=mode,
    )


def test_agent_no_llm_configured_deterministic_summary():
    # Explicitly unconfigured settings (no key, no model)
    s = Settings(LLM_PROVIDER="gemini", GOOGLE_API_KEY="", GEMINI_MODEL="")
    deps = AgentDependencies(settings=s, llm_factory=lambda: None)

    req = _make_req()
    res = run_research_agent(req, deps=deps)

    assert res.status == ResultStatus.success
    assert "Operational research summary for DEL" in res.summary
    assert not any(e.tool == "llm" for e in res.errors)
    assert not any("LLM synthesis unavailable" in m for m in res.missing_information)
    assert len(res.findings) >= 2
    assert all(f.kind == FindingKind.provider_fact for f in res.findings)


def test_agent_stub_llm_valid_grounded_output_accepted():
    req = _make_req()

    # Pre-determined source ids matching synthetic mode output
    # The deterministic tool run creates sources like weather-open-meteo-DEL-<ts> and flight-opensky-DEL-<ts>
    # In order to make grounded citations, our stub LLM reads existing source ids or we pass existing ones
    # We can pass an LLMSynthesis with an inference finding citing the real source
    class DynamicStubLLM:
        def __init__(self):
            self.invoked = False

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            self.invoked = True
            # Read source id from message content to ensure 100% citation grounding
            import json, re
            content = messages[1].content
            wx_source_match = re.search(r'"source_id":\s*"(weather-open-meteo-DEL-\d+)"', content)
            wx_sid = wx_source_match.group(1) if wx_source_match else "dummy-sid"

            return LLMSynthesis(
                summary="Synthesized LLM Summary: Visibility at DEL is 10000.0m and aircraft AIC101 is airborne at 3200.0m.",
                findings=[
                    LLMFinding(
                        finding="Visibility is sufficient for approach operations.",
                        evidence_refs=[wx_sid],
                        kind=FindingKind.inference,
                        limitations=["Advisory inference based on synthetic model data."],
                    ),
                    LLMFinding(
                        finding="Duplicate provider fact that should be dropped by merge.",
                        evidence_refs=[wx_sid],
                        kind=FindingKind.provider_fact,
                        limitations=[],
                    ),
                ],
            )

    stub = DynamicStubLLM()
    deps = AgentDependencies(llm_factory=lambda: stub)

    res = run_research_agent(req, deps=deps)

    assert stub.invoked is True
    assert res.status == ResultStatus.success
    assert "Synthesized LLM Summary" in res.summary

    # Merged findings check:
    # 1. Deterministic provider_fact findings are still present and authoritative
    provider_facts = [f for f in res.findings if f.kind == FindingKind.provider_fact]
    assert len(provider_facts) >= 2
    assert not any("Duplicate provider fact" in f.finding for f in provider_facts)

    # 2. Extra findings appended from LLM are INFERENCE only
    inferences = [f for f in res.findings if f.kind == FindingKind.inference]
    assert len(inferences) == 1
    assert "Visibility is sufficient" in inferences[0].finding

    # 3. All evidence_refs exist in sources
    source_ids = {s.source_id for s in res.sources}
    for f in res.findings:
        for ref in f.evidence_refs:
            assert ref in source_ids


def test_agent_stub_llm_ungrounded_output_rejected():
    # LLM outputs an invented number or unknown source id
    canned = LLMSynthesis(
        summary="DEL visibility is 999999 meters.",  # ungrounded number!
        findings=[],
    )
    stub = StubLLM(canned_response=canned)
    deps = AgentDependencies(llm_factory=lambda: stub)

    req = _make_req()
    res = run_research_agent(req, deps=deps)

    # Status reflects tool evidence only
    assert res.status == ResultStatus.success
    # Falls back to deterministic summary
    assert "Operational research summary for DEL" in res.summary
    assert any(e.tool == "llm" and e.code == "LLM_REJECTED_UNGROUNDED" for e in res.errors)
    assert any("LLM synthesis unavailable" in m for m in res.missing_information)


def test_agent_stub_llm_timeout():
    class MockTimeout(Exception):
        pass

    stub = StubLLM(exception_to_raise=MockTimeout("LLM read timeout"))
    deps = AgentDependencies(llm_factory=lambda: stub)

    req = _make_req()
    res = run_research_agent(req, deps=deps)

    assert res.status == ResultStatus.success
    assert "Operational research summary for DEL" in res.summary
    assert any(e.tool == "llm" and e.code == "LLM_TIMEOUT" and e.retryable is True for e in res.errors)
    assert any("LLM synthesis unavailable" in m for m in res.missing_information)


def test_agent_llm_config_error_from_factory_handled_safely():
    def exploding_factory():
        raise LLMConfigError("Gemini provider requires environment variable GOOGLE_API_KEY.")

    deps = AgentDependencies(llm_factory=exploding_factory)
    req = _make_req()

    res = run_research_agent(req, deps=deps)

    assert res.status == ResultStatus.success
    assert "Operational research summary for DEL" in res.summary
    assert any(e.tool == "llm" and e.code == "LLM_CONFIG_ERROR" for e in res.errors)
    assert any("LLM synthesis unavailable" in m for m in res.missing_information)


def test_agent_no_evidence_skips_llm():
    # When status is no_data or failed, LLM is never invoked
    req = ResearchRequest(
        request_id="req-test-none-1",
        workflow_id="wf-test-none-1",
        airport_code="DEL",
        disruption_type=DisruptionType.other,
        disruption_description="Baggage belt failure",
        research_requirements=["Inspect luggage conveyor status"],
    )
    stub = StubLLM()
    deps = AgentDependencies(llm_factory=lambda: stub)

    res = run_research_agent(req, deps=deps)

    assert res.status == ResultStatus.no_data
    assert stub.was_invoked is False
    assert not any(e.tool == "llm" for e in res.errors)


def test_agent_synthetic_mode_with_stub_llm_labeled_synthetic():
    canned = LLMSynthesis(
        summary="Synthetic advisory analysis for DEL conditions.",
        findings=[],
    )
    stub = StubLLM(canned_response=canned)
    deps = AgentDependencies(llm_factory=lambda: stub)

    req = _make_req(mode=DataMode.synthetic)
    res = run_research_agent(req, deps=deps)

    assert res.data_mode == DataMode.synthetic
    assert res.summary == canned.summary
    for s in res.sources:
        assert s.data_type == "synthetic"
    for f in res.findings:
        assert any("synthetic" in lim.lower() for lim in f.limitations)

    # JSON round trip validation
    json_str = res.model_dump_json(indent=2)
    assert res == type(res).model_validate_json(json_str)
