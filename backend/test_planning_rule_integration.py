from app.rule_engine.engine import evaluate_operational_rules
from app.rule_engine.schemas import OperationalInput


def test_planning_rule_integration():
    print("\n=== PLANNING AGENT + RULE ENGINE INTEGRATION ===")

    # Simulated operational data for a flight.
    # This test does not call Gemini.
    operational_data = OperationalInput(
        airport_code="HYD",
        flight_number="AI501",
        delay_minutes=45,
        rainfall_mm=12.0,
        runway_available=True,
    )

    # Execute the existing Rule Engine.
    result = evaluate_operational_rules(operational_data)

    # Validate the result.
    assert result.airport_code == "HYD"
    assert result.flight_number == "AI501"

    # Delay and rainfall rules should trigger.
    assert result.triggered_rules == 2

    assert result.results[0].triggered is True
    assert result.results[1].triggered is True
    assert result.results[2].triggered is False

    # The Rule Engine must remain advisory-only.
    assert result.advisory_only is True

    print("Test 1 passed: Operational data was evaluated.")
    print("Test 2 passed: Flight delay rule was triggered.")
    print("Test 3 passed: Heavy rainfall rule was triggered.")
    print("Test 4 passed: Available runway did not trigger a warning.")
    print("Test 5 passed: Results remain advisory-only.")

    print("\nRule Engine result:")
    print(result.model_dump())

    print("\nIntegration test passed.")


if __name__ == "__main__":
    test_planning_rule_integration()