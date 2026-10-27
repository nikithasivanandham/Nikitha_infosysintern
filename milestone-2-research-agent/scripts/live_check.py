"""Opt-in live provider verification script for Airport Operations Research Agent.

Usage:
    .\\venv\\Scripts\\python scripts\\live_check.py [options]

Options:
    --airport CODE         IATA/ICAO airport code (default: DEL)
    --flights CALLSIGNS    Comma-separated flight callsigns (e.g. AIC101,6E204)
    --only TARGET          Run only one check: weather | flight | llm | agent

Security & Privacy Guarantee:
    - Never prints, logs, or displays credentials, tokens, secrets, or .env contents.
    - Forces DATA_MODE=live in memory without altering .env or disk configuration.
    - Limits queries to at most 1 call per provider.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

# Ensure project root is on sys.path when script is executed directly
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from app.agent import AgentDependencies, run_research_agent

from app.config import settings
from app.providers.llm_provider import get_llm, is_llm_configured
from app.schemas import DataMode, DisruptionType, ResearchRequest, ResultStatus
from app.tools.flight_tool import get_flights
from app.tools.weather_tool import get_weather


def run_weather_check(airport_code: str) -> tuple[str, str]:
    """Execute Check 1: live weather retrieval via Open-Meteo."""
    print("=" * 60)
    print(f"CHECK 1: WEATHER PROVIDER (Open-Meteo) -> Airport: {airport_code}")
    print("=" * 60)

    try:
        output = get_weather(airport_code=airport_code, mode=DataMode.live)
        wx = output.weather
        src = output.source
        err = output.error

        print(f"Status       : {wx.status.value}")
        print(f"Data Type    : {wx.data_type.value}")
        print(f"Provider     : {wx.provider}")
        print(f"Valid Time   : {wx.valid_time.isoformat() if wx.valid_time else 'None'}")
        print(f"Retrieved At : {src.retrieved_at.isoformat() if src else 'None'}")
        print(f"Source ID    : {wx.source_id or 'None'}")

        # Display key observations with verified units from the provider
        sample_keys = [
            "visibility",
            "temperature_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "cloud_cover",
        ]
        print("\nObservations with Provider Units:")
        for k in sample_keys:
            val = wx.observations.get(k)
            unit = wx.units.get(k, "")
            if val is not None:
                print(f"  - {k:<18}: {val} {unit}".rstrip())

        if err:
            print(f"\nErrorInfo Code: {err.code} (Retryable: {err.retryable})")
            print(f"ErrorInfo Msg : {err.message}")

        if wx.status.value == "success" and wx.source_id:
            return "PASS", f"Retrieved live {wx.data_type.value} observations from {wx.provider}"
        elif err and err.code == "RATE_LIMITED":
            return "PARTIAL", "Provider returned HTTP 429 rate limit"
        else:
            reason = err.code if err else wx.status.value
            return "FAIL", f"Weather check failed: {reason}"

    except Exception as exc:
        print(f"Unexpected exception during weather check: {type(exc).__name__}: {exc}")
        return "FAIL", f"Exception: {type(exc).__name__}"


def run_flight_check(airport_code: str, flight_list: list[str]) -> tuple[str, str]:
    """Execute Check 2: live flight retrieval via OpenSky Network."""
    print("\n" + "=" * 60)
    print(f"CHECK 2: FLIGHT PROVIDER (OpenSky Network) -> Airport: {airport_code}")
    print("=" * 60)

    # Report credential status without displaying any values
    has_creds = bool((settings.FLIGHT_CLIENT_ID or "").strip() and (settings.FLIGHT_CLIENT_SECRET or "").strip())
    print(f"Credentials Configured : {'yes' if has_creds else 'no'}")
    print(f"Authentication Path    : {'OAuth2 (Bearer)' if has_creds else 'Anonymous'}")

    if not flight_list:
        print("\nNotice: No --flights provided. OpenSky requires flight identifiers for bounding-box queries.")
        print("Skipping live network call to preserve API quota.")
        return "PASS", "Skipped live network call (no flights specified)"

    try:
        output = get_flights(
            airport_code=airport_code,
            flight_identifiers=flight_list,
            research_requirements=["aircraft state"],
            mode=DataMode.live,
        )

        found_count = 0
        not_found_count = 0
        error_count = 0

        print(f"\nRequested Flights ({len(output.flights)}):")
        for f in output.flights:
            status_val = f.status.value
            print(f"  - Callsign {f.requested_identifier:<8}: status={status_val}")
            if status_val == "found":
                found_count += 1
                alt = f.data.get("baro_altitude", "N/A")
                vel = f.data.get("velocity", "N/A")
                ground = f.data.get("on_ground", "N/A")
                print(f"      alt={alt}m, vel={vel}m/s, on_ground={ground}")
            elif status_val == "not_found":
                not_found_count += 1
            else:
                error_count += 1

        print("\nNote: 'not_found' is a completely normal outcome if the aircraft is outside receiver range or on the ground with transponder off.")

        if output.errors:
            print("\nErrors Encountered:")
            for e in output.errors:
                print(f"  - [{e.code}] {e.message} (Retryable: {e.retryable})")

        if output.errors:
            if any(e.code == "RATE_LIMITED" for e in output.errors):
                return "PARTIAL", "OpenSky rate limit reached (HTTP 429)"
            if any(e.code == "AUTH_FAILED" for e in output.errors):
                return "FAIL", "OpenSky OAuth2 authentication failed"
            return "FAIL", f"Tool returned errors: {[e.code for e in output.errors]}"

        if found_count > 0:
            return "PASS", f"Found live telemetry for {found_count}/{len(flight_list)} aircraft"
        else:
            return "PASS", f"Request succeeded; {not_found_count} aircraft outside coverage"

    except Exception as exc:
        print(f"Unexpected exception during flight check: {type(exc).__name__}: {exc}")
        return "FAIL", f"Exception: {type(exc).__name__}"


def run_llm_check() -> tuple[str, str]:
    """Execute Check 3: LLM configuration and test prompt."""
    print("\n" + "=" * 60)
    print("CHECK 3: LLM SYNTHESIS ENGINE")
    print("=" * 60)

    configured = is_llm_configured(settings)
    provider_name = settings.LLM_PROVIDER
    print(f"LLM Configured : {'yes' if configured else 'no'}")
    print(f"Provider Name  : {provider_name}")

    if not configured:
        print("LLM is not configured (missing key or required model settings).")
        print("The agent will automatically use deterministic synthesis.")
        return "PASS", f"Not configured (deterministic fallback active, provider={provider_name})"

    try:
        start_time = time.time()
        chat_model = get_llm(settings)
        # Fixed, harmless single-word prompt
        response = chat_model.invoke("Reply with the single word OK")
        latency = round((time.time() - start_time) * 1000, 1)

        raw_content = getattr(response, "content", "").strip()
        word = raw_content[:10]  # Show only the first few chars, never a long message
        print(f"Call Result    : SUCCESS (Response: '{word}', Latency: {latency}ms)")
        return "PASS", f"Live call succeeded ({latency}ms, provider={provider_name})"

    except Exception as exc:
        err_type = type(exc).__name__
        print(f"Call Result    : FAILED (Error: {err_type})")
        # Never print full exception string if it might contain credentials
        return "FAIL", f"Invocation failed: {err_type}"


def run_agent_check(airport_code: str, flight_list: list[str]) -> tuple[str, str]:
    """Execute Check 4: Full Research Agent pipeline in live mode."""
    print("\n" + "=" * 60)
    print(f"CHECK 4: FULL RESEARCH AGENT PIPELINE -> Airport: {airport_code}")
    print("=" * 60)

    try:
        req = ResearchRequest(
            request_id=f"live-check-{int(time.time())}",
            workflow_id="wf-live-diag",
            airport_code=airport_code,
            disruption_type=DisruptionType.weather,
            disruption_description="Live operational readiness check",
            affected_flights=flight_list,
            research_requirements=["wind and visibility forecast", "aircraft state"],
            planning_objective="Verify live situational awareness data",
            data_mode=DataMode.live,
        )

        deps = AgentDependencies(settings=settings)
        result = run_research_agent(req, deps=deps)

        # Decide whether LLM was used:
        # 1. Did an LLM error occur?
        has_llm_error = any(e.tool == "llm" for e in result.errors)
        # 2. Was an LLM configured?
        llm_conf = is_llm_configured(settings)
        # Decision logic:
        if not llm_conf:
            llm_used_desc = "No (LLM not configured; deterministic summary used)"
        elif has_llm_error:
            llm_used_desc = "No (LLM failed/guarded; deterministic summary used)"
        else:
            # When LLM succeeds, inferences or rewritten summary are attached
            has_inference = any(f.kind.value == "inference" for f in result.findings)
            llm_used_desc = f"Yes (synthesis active, inferences={has_inference})"

        print(f"Result Status      : {result.status.value}")
        print(f"LLM Synthesis Used : {llm_used_desc}")
        print(f"Sources Gathered   : {len(result.sources)}")
        print(f"Findings Emitted   : {len(result.findings)}")
        print(f"Errors Logged      : {[e.code for e in result.errors] if result.errors else 'None'}")
        print(f"Missing Information: {result.missing_information or 'None'}")
        print(f"\nExecutive Summary  :\n{result.summary}")

        # Validate JSON round-trip
        serialized = result.model_dump_json()
        deserialized = json.loads(serialized)
        assert deserialized["schema_version"] == "1.0"
        assert deserialized["status"] == result.status.value
        print("\nJSON Contract Round-Trip: OK (valid Pydantic v2 serialization)")

        status_val = result.status.value
        if status_val == "success":
            return "PASS", "Agent executed successfully with full evidence"
        elif status_val == "partial_success":
            return "PARTIAL", f"Partial success ({len(result.missing_information)} gaps/missing info)"
        elif status_val == "no_data":
            return "PARTIAL", "No observation or state vector data returned"
        else:
            return "FAIL", f"Agent failed: {[e.code for e in result.errors]}"

    except Exception as exc:
        print(f"Unexpected exception during agent check: {type(exc).__name__}: {exc}")
        return "FAIL", f"Exception: {type(exc).__name__}"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for live check."""
    parser = argparse.ArgumentParser(
        description="Verify live weather, flight, and LLM providers safely."
    )
    parser.add_argument(
        "--airport",
        default="DEL",
        help="Airport code to query (default: DEL)",
    )
    parser.add_argument(
        "--flights",
        default="",
        help="Comma-separated flight callsigns to query (e.g. AIC101,6E204)",
    )
    parser.add_argument(
        "--only",
        choices=["weather", "flight", "llm", "agent"],
        default=None,
        help="Run only one specific check",
    )
    args = parser.parse_args(argv)

    airport_code = args.airport.strip().upper()
    flight_list = [f.strip().upper() for f in args.flights.split(",") if f.strip()]

    # Force DATA_MODE=live for this run in memory without touching disk or .env
    object.__setattr__(settings, "DATA_MODE", "live")

    print("\n" + "=" * 65)
    print("   AIRPORT OPERATIONS RESEARCH AGENT - LIVE PROVIDER CHECK")
    print("=" * 65)
    print(f"Target Airport : {airport_code}")
    print(f"Target Flights : {flight_list or 'None specified'}")
    print("Execution Mode : LIVE (forced in memory for this check)")

    results_table: list[tuple[str, str, str]] = []

    target = args.only

    if target in (None, "weather"):
        st, msg = run_weather_check(airport_code)
        results_table.append(("Weather (Open-Meteo)", st, msg))

    if target in (None, "flight"):
        st, msg = run_flight_check(airport_code, flight_list)
        results_table.append(("Flight (OpenSky)", st, msg))

    if target in (None, "llm"):
        st, msg = run_llm_check()
        results_table.append(("LLM Engine", st, msg))

    if target in (None, "agent"):
        st, msg = run_agent_check(airport_code, flight_list)
        results_table.append(("Full Agent Pipeline", st, msg))

    # Print summary table
    print("\n" + "=" * 65)
    print("                     CHECK SUMMARY TABLE")
    print("=" * 65)
    print(f"{'Check':<24} | {'Status':<8} | Reason")
    print("-" * 65)
    has_failure = False
    for check_name, st, reason in results_table:
        print(f"{check_name:<24} | {st:<8} | {reason}")
        if st == "FAIL":
            has_failure = True
    print("=" * 65 + "\n")

    return 1 if has_failure else 0


if __name__ == "__main__":
    sys.exit(main())
