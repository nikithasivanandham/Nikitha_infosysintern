from pydantic import ValidationError

from app.rule_engine.gate_management import (
    GateAssignment,
    detect_gate_conflict,
    suggest_alternative_gates,
)


def main():

    print("\n=== GATE MANAGEMENT TESTS ===")

    # Test 1: Same gate with overlapping assignments.
    first = GateAssignment(
        airport_code="HYD",
        flight_number="AI501",
        gate_id="G1",
        start_minute=600,
        end_minute=630,
    )

    second = GateAssignment(
        airport_code="HYD",
        flight_number="AI502",
        gate_id="G1",
        start_minute=620,
        end_minute=650,
    )

    result = detect_gate_conflict(first, second)

    assert result.conflict_detected is True

    print("Test 1 passed: Overlapping gate assignments detected.")

    # Test 2: Different gates.
    second = second.model_copy(
        update={"gate_id": "G2"}
    )

    result = detect_gate_conflict(first, second)

    assert result.conflict_detected is False

    print("Test 2 passed: Different gates do not conflict.")

    # Test 3: Adjacent assignments at the same gate.
    second = GateAssignment(
        airport_code="HYD",
        flight_number="AI502",
        gate_id="G1",
        start_minute=630,
        end_minute=660,
    )

    result = detect_gate_conflict(first, second)

    assert result.conflict_detected is False

    print("Test 3 passed: Adjacent assignments do not overlap.")

    # Test 4: Suggest available alternative gates.
    assignments = [
        GateAssignment(
            airport_code="HYD",
            flight_number="AI501",
            gate_id="G1",
            start_minute=600,
            end_minute=630,
        ),
        GateAssignment(
            airport_code="HYD",
            flight_number="AI503",
            gate_id="G2",
            start_minute=640,
            end_minute=670,
        ),
    ]

    alternatives = suggest_alternative_gates(
        airport_code="HYD",
        flight_number="AI502",
        start_minute=620,
        end_minute=650,
        candidate_gates=["G1", "G2", "G3"],
        existing_assignments=assignments,
    )

    assert alternatives == ["G3"]

    print("Test 4 passed: Only an available alternative gate was suggested.")
    print("Suggested gates:", alternatives)

    # Test 5: Invalid time interval.
    try:
        GateAssignment(
            airport_code="HYD",
            flight_number="AI504",
            gate_id="G1",
            start_minute=650,
            end_minute=640,
        )

        raise AssertionError(
            "Invalid gate interval should have been rejected."
        )

    except ValidationError:
        print("Test 5 passed: Invalid gate interval rejected.")

    print("\nAll gate management tests passed.")


if __name__ == "__main__":
    main()