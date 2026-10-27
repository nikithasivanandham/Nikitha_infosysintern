from app.rule_engine.scheduling import (
    RunwaySlot,
    detect_runway_conflict,
)

from app.rule_engine.gate_management import (
    GateAssignment,
    detect_gate_conflict,
)

from app.rule_engine.weather_rules import (
    WeatherConditions,
    evaluate_weather_risk,
)

from app.rule_engine.permission_rules import (
    PermissionRequestInput,
    evaluate_permission_request,
)


def main():

    print("\n=== COMBINED RULE ENGINE TEST ===")

    # --------------------------------------------------
    # TEST 1: RUNWAY CONFLICT
    # --------------------------------------------------

    runway_a = RunwaySlot(
        airport_code="HYD",
        flight_number="AI501",
        runway_id="RWY-09",
        start_minute=600,
        end_minute=630,
    )

    runway_b = RunwaySlot(
        airport_code="HYD",
        flight_number="AI502",
        runway_id="RWY-09",
        start_minute=620,
        end_minute=650,
    )

    runway_result = detect_runway_conflict(
        runway_a,
        runway_b,
    )

    assert runway_result.conflict_detected is True

    print("Test 1 passed: Runway conflict detected.")

    # --------------------------------------------------
    # TEST 2: GATE CONFLICT
    # --------------------------------------------------

    gate_a = GateAssignment(
        airport_code="HYD",
        flight_number="AI501",
        gate_id="G1",
        start_minute=600,
        end_minute=630,
    )

    gate_b = GateAssignment(
        airport_code="HYD",
        flight_number="AI502",
        gate_id="G1",
        start_minute=620,
        end_minute=650,
    )

    gate_result = detect_gate_conflict(
        gate_a,
        gate_b,
    )

    assert gate_result.conflict_detected is True

    print("Test 2 passed: Gate conflict detected.")

    # --------------------------------------------------
    # TEST 3: WEATHER RISK
    # --------------------------------------------------

    weather = WeatherConditions(
        airport_code="HYD",
        flight_number="AI501",
        rainfall_mm=15.0,
        visibility_m=500.0,
        wind_speed_kmh=50.0,
    )

    weather_result = evaluate_weather_risk(weather)

    assert weather_result.risk_level == "HIGH"

    print("Test 3 passed: Weather risk evaluated.")

    # --------------------------------------------------
    # TEST 4: PERMISSION DECISION
    # --------------------------------------------------

    permission = PermissionRequestInput(
        request_id="REQ-101",
        user_id="pilot001",
        flight_number="AI501",
        requested_action="gate_access",
        identity_verified=True,
        permission_valid=True,
        operational_block=False,
        requires_manual_review=False,
    )

    permission_result = evaluate_permission_request(
        permission
    )

    assert permission_result.decision == "GRANT"

    print("Test 4 passed: Permission recommendation generated.")

    # --------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------

    print("\nCombined test results:")

    print("Runway:", runway_result.model_dump())
    print("Gate:", gate_result.model_dump())
    print("Weather:", weather_result.model_dump())
    print("Permission:", permission_result.model_dump())

    print("\nAll combined tests passed.")


if __name__ == "__main__":
    main()