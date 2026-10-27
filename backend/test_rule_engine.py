from pydantic import ValidationError

from app.rule_engine.schemas import OperationalInput
from app.rule_engine.engine import evaluate_operational_rules


def main():
    print("\n=== AIRPORT RULE ENGINE TEST ===")

    # Scenario 1: Normal operating conditions
    normal_input = OperationalInput(
        airport_code="HYD",
        flight_number="AI501",
        delay_minutes=5,
        rainfall_mm=2.0,
        runway_available=True,
    )

    normal_result = evaluate_operational_rules(normal_input)

    print("\nScenario 1: Normal Conditions")
    print(normal_result.model_dump())

    assert normal_result.triggered_rules == 0

    # Scenario 2: Delay and rainfall risks
    disruption_input = OperationalInput(
        airport_code="HYD",
        flight_number="AI502",
        delay_minutes=45,
        rainfall_mm=15.0,
        runway_available=True,
    )

    disruption_result = evaluate_operational_rules(disruption_input)

    print("\nScenario 2: Delay and Rainfall")
    print(disruption_result.model_dump())

    assert disruption_result.triggered_rules == 2

    # Scenario 3: Runway unavailable
    runway_input = OperationalInput(
        airport_code="HYD",
        flight_number="AI503",
        delay_minutes=0,
        rainfall_mm=0.0,
        runway_available=False,
    )

    runway_result = evaluate_operational_rules(runway_input)

    print("\nScenario 3: Runway Unavailable")
    print(runway_result.model_dump())

    assert runway_result.triggered_rules == 1

    # Scenario 4: Invalid input
    print("\nScenario 4: Invalid Input")

    try:
        OperationalInput(
            airport_code="HYD",
            flight_number="AI504",
            delay_minutes=-5,
            rainfall_mm=0.0,
            runway_available=True,
        )
    except ValidationError:
        print("Invalid delay rejected successfully.")
    else:
        raise AssertionError("Negative delay should be rejected.")

    test_rule_boundaries()

    print("\nAll Rule Engine tests passed.")

def test_rule_boundaries():
    from app.rule_engine.rules import (
        evaluate_delay_rule,
        evaluate_rainfall_rule,
        evaluate_runway_rule,
    )

    from app.rule_engine.schemas import OperationalInput

    print("\n=== RULE BOUNDARY TESTS ===")

    # Test 1: Delay below the threshold
    data = OperationalInput(
        airport_code="HYD",
        flight_number="AI501",
        delay_minutes=29,
        rainfall_mm=0,
        runway_available=True,
    )

    assert evaluate_delay_rule(data).triggered is False
    print("Test 1 passed: 29-minute delay does not trigger the rule.")

    # Test 2: Delay exactly at the threshold
    data = data.model_copy(
        update={"delay_minutes": 30}
    )

    assert evaluate_delay_rule(data).triggered is True
    print("Test 2 passed: 30-minute delay triggers the rule.")

    # Test 3: Rainfall below the threshold
    data = OperationalInput(
        airport_code="HYD",
        flight_number="AI501",
        delay_minutes=0,
        rainfall_mm=9.9,
        runway_available=True,
    )

    assert evaluate_rainfall_rule(data).triggered is False
    print("Test 3 passed: 9.9 mm rainfall does not trigger the rule.")

    # Test 4: Rainfall exactly at the threshold
    data = data.model_copy(
        update={"rainfall_mm": 10.0}
    )

    assert evaluate_rainfall_rule(data).triggered is True
    print("Test 4 passed: 10 mm rainfall triggers the rule.")

    # Test 5: Runway unavailable
    data = data.model_copy(
        update={"runway_available": False}
    )

    assert evaluate_runway_rule(data).triggered is True
    print("Test 5 passed: unavailable runway triggers the rule.")

    print("\nAll rule boundary tests passed.")


if __name__ == "__main__":
    main()