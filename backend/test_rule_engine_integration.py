from app.rule_engine.engine import evaluate_operational_rules
from app.rule_engine.schemas import OperationalInput


def main():
    print("\n=== RULE ENGINE INTEGRATION TEST ===")

    operational_data = OperationalInput(
        airport_code="HYD",
        flight_number="AI501",
        delay_minutes=45,
        rainfall_mm=15.0,
        runway_available=True,
    )

    result = evaluate_operational_rules(operational_data)

    print("\nOperational Input:")
    print(operational_data.model_dump())

    print("\nRule Engine Result:")
    print(result.model_dump())

    assert result.airport_code == "HYD"
    assert result.flight_number == "AI501"
    assert result.triggered_rules == 2
    assert result.advisory_only is True

    triggered_rule_ids = [
        rule.rule_id
        for rule in result.results
        if rule.triggered
    ]

    assert "RULE-001" in triggered_rule_ids
    assert "RULE-002" in triggered_rule_ids
    assert "RULE-003" not in triggered_rule_ids

    print("\nAll Rule Engine integration checks passed.")


if __name__ == "__main__":
    main()