"""Evidence-grounded synthesis module using structured LLM output with strict guardrails."""

from __future__ import annotations

import json
import re
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas import (
    DataMode,
    ErrorInfo,
    Finding,
    FindingKind,
    ResearchRequest,
    SourceRecord,
)

FORBIDDEN_KEYWORDS = [
    "metar",
    "speci",
    "schedule",
    "scheduled",
    "delay",
    "delays",
    "delayed",
    "gate",
    "gates",
    "approve",
    "approved",
    "approval",
    "authorize",
    "authorized",
    "authorization",
    "allocate",
    "allocated",
    "allocation",
    "instruction",
    "instructed",
]


class LLMFinding(BaseModel):
    """Structured finding emitted by the language model."""

    finding: str = Field(..., description="Finding statement.")
    evidence_refs: list[str] = Field(default_factory=list, description="Citations to source_id.")
    kind: FindingKind = Field(..., description="provider_fact or inference.")
    limitations: list[str] = Field(default_factory=list, description="Caveats and limitations.")


class LLMSynthesis(BaseModel):
    """Structured response schema for LLM synthesis."""

    summary: str = Field(..., description="Concise, source-grounded summary.")
    findings: list[LLMFinding] = Field(default_factory=list, description="List of analytical findings.")


class SynthesisOutcome(BaseModel):
    """Result of synthesis execution."""

    used_llm: bool = False
    summary: str | None = None
    findings: list[Finding] | None = None
    error: ErrorInfo | None = None


def build_evidence_bundle(
    request: ResearchRequest,
    findings: list[Finding],
    sources: list[SourceRecord],
    missing_information: list[str],
    errors: list[ErrorInfo],
) -> dict[str, Any]:
    """Assemble a safe, secret-free evidence bundle for LLM ingestion."""
    return {
        "request_context": {
            "request_id": request.request_id,
            "airport_code": request.airport_code,
            "disruption_type": request.disruption_type.value,
            "disruption_description": request.disruption_description,
            "affected_flights": request.affected_flights,
            "research_requirements": request.research_requirements,
            "data_mode": request.data_mode.value,
            "as_of": request.as_of.isoformat() if request.as_of else None,
        },
        "tool_findings": [
            {
                "finding": f.finding,
                "evidence_refs": f.evidence_refs,
                "kind": f.kind.value,
                "limitations": f.limitations,
            }
            for f in findings
        ],
        "sources": [
            {
                "source_id": s.source_id,
                "provider": s.provider,
                "data_type": s.data_type,
                "retrieved_at": s.retrieved_at.isoformat(),
            }
            for s in sources
        ],
        "missing_information": missing_information,
        "error_codes": [e.code for e in errors],
    }


def _extract_numbers(text: str) -> set[str]:
    """Extract numeric tokens (integers and floating point numbers) from text.

    Known limitations of simple numeric regex matching:
    - Does not normalize number formatting (e.g., '1,000' vs '1000' or scientific notation).
    - Treats numbers embedded inside flight callsigns (e.g. '101' in 'AIC101') as numeric strings.
    - May match dates/timestamps as sequences of integers.
    """
    matches = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    # Normalize by stripping trailing .0 where applicable
    normalized = set()
    for m in matches:
        normalized.add(m)
        try:
            val = float(m)
            if val.is_integer():
                normalized.add(str(int(val)))
        except ValueError:
            pass
    return normalized


def _check_forbidden_keywords(text: str, allowed_context: str) -> str | None:
    """Detect forbidden domain keywords unless they exist legitimately in the evidence context.

    Known limitations of keyword filtering:
    - Case-insensitive whole-word regex matching may flag legitimate advisory explanations
      (e.g., 'No delay information was provided by OpenSky').
    - Does not evaluate grammatical context or negation.
    """
    allowed_lower = allowed_context.lower()
    text_lower = text.lower()

    for kw in FORBIDDEN_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text_lower):
            # Only allow if the exact keyword appeared in the evidence bundle
            if not re.search(pattern, allowed_lower):
                return kw
    return None


def synthesize(
    llm: BaseChatModel | None,
    request: ResearchRequest,
    findings: list[Finding],
    sources: list[SourceRecord],
    missing_information: list[str],
    errors: list[ErrorInfo],
) -> SynthesisOutcome:
    """Perform evidence-grounded LLM synthesis with pre- and post-generation guardrails.

    Never raises exceptions; all errors return SynthesisOutcome with an ErrorInfo.
    """
    # 1. Skip synthesis if there is no evidence
    if not findings and not sources:
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=None)

    if llm is None:
        err = ErrorInfo(
            tool="llm",
            code="LLM_UNAVAILABLE",
            message="LLM instance not provided or configured.",
            retryable=False,
        )
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

    # 2. Build sanitized bundle
    evidence_bundle = build_evidence_bundle(
        request=request,
        findings=findings,
        sources=sources,
        missing_information=missing_information,
        errors=errors,
    )
    bundle_str = json.dumps(evidence_bundle, default=str)
    allowed_numbers = _extract_numbers(bundle_str)
    known_source_ids = {s.source_id for s in sources}

    # 3. Format messages and invoke with structured output
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_user_prompt(evidence_bundle)),
    ]

    try:
        structured_llm = llm.with_structured_output(LLMSynthesis)
        response = structured_llm.invoke(messages)
    except Exception as exc:
        exc_name = type(exc).__name__.lower()
        if "timeout" in exc_name:
            code = "LLM_TIMEOUT"
            retryable = True
            msg = "LLM synthesis invocation timed out."
        else:
            code = "LLM_UNAVAILABLE"
            retryable = False
            msg = f"LLM synthesis invocation failed: {type(exc).__name__}"

        err = ErrorInfo(tool="llm", code=code, message=msg, retryable=retryable)
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

    # 4. Type validation
    if not isinstance(response, LLMSynthesis):
        err = ErrorInfo(
            tool="llm",
            code="LLM_INVALID_OUTPUT",
            message="LLM failed to return structured synthesis output.",
            retryable=False,
        )
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

    # 5. Guardrail validations
    summary = response.summary.strip()
    if not summary:
        err = ErrorInfo(
            tool="llm",
            code="LLM_REJECTED_UNGROUNDED",
            message="LLM generated an empty summary.",
            retryable=False,
        )
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

    # Validate findings structure and citations
    validated_findings: list[Finding] = []
    for idx, f in enumerate(response.findings):
        # provider_fact requires evidence_refs
        if f.kind == FindingKind.provider_fact and not f.evidence_refs:
            err = ErrorInfo(
                tool="llm",
                code="LLM_REJECTED_UNGROUNDED",
                message=f"LLM finding at index {idx} has kind 'provider_fact' but no evidence_refs.",
                retryable=False,
            )
            return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

        # evidence_ref existence
        for ref in f.evidence_refs:
            if ref not in known_source_ids:
                err = ErrorInfo(
                    tool="llm",
                    code="LLM_REJECTED_UNGROUNDED",
                    message=f"LLM finding at index {idx} cites unknown source_id '{ref}'.",
                    retryable=False,
                )
                return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

        validated_findings.append(
            Finding(
                finding=f.finding,
                evidence_refs=f.evidence_refs,
                kind=f.kind,
                limitations=f.limitations,
            )
        )

    # Numeric grounding check across summary and finding texts
    all_output_text = summary + " " + " ".join(f.finding for f in response.findings)
    output_numbers = _extract_numbers(all_output_text)
    invented_numbers = output_numbers - allowed_numbers
    if invented_numbers:
        err = ErrorInfo(
            tool="llm",
            code="LLM_REJECTED_UNGROUNDED",
            message=f"LLM output contains ungrounded numeric values: {sorted(list(invented_numbers))}.",
            retryable=False,
        )
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

    # Forbidden keyword guard
    violation_kw = _check_forbidden_keywords(all_output_text, bundle_str)
    if violation_kw:
        err = ErrorInfo(
            tool="llm",
            code="LLM_REJECTED_UNGROUNDED",
            message=f"LLM output contains forbidden unauthorized or ungrounded term '{violation_kw}'.",
            retryable=False,
        )
        return SynthesisOutcome(used_llm=False, summary=None, findings=None, error=err)

    return SynthesisOutcome(
        used_llm=True,
        summary=summary,
        findings=validated_findings,
        error=None,
    )
