from app.rule_engine.schemas import OperationalInput, RuleResult


def evaluate_delay_rule(data: OperationalInput) -> RuleResult:
    """Flag a reported delay of 30 minutes or more."""

    triggered = data.delay_minutes >= 30

    return RuleResult(
        rule_id="RULE-001",
        rule_name="Flight Delay Risk",
        triggered=triggered,
        severity="MEDIUM" if triggered else "LOW",
        message=(
            f"Flight {data.flight_number} has a reported delay "
            f"of {data.delay_minutes} minutes."
            if triggered
            else "The reported delay is below the configured threshold."
        ),
    )


def evaluate_rainfall_rule(data: OperationalInput) -> RuleResult:
    """Flag reported rainfall of 10 mm or more."""

    triggered = data.rainfall_mm >= 10.0

    return RuleResult(
        rule_id="RULE-002",
        rule_name="Heavy Rainfall Risk",
        triggered=triggered,
        severity="HIGH" if triggered else "LOW",
        message=(
            f"Reported rainfall is {data.rainfall_mm} mm. "
            "Further operational assessment is recommended."
            if triggered
            else "The reported rainfall is below the configured threshold."
        ),
    )


def evaluate_runway_rule(data: OperationalInput) -> RuleResult:
    """Flag a runway reported as unavailable."""

    triggered = not data.runway_available

    return RuleResult(
        rule_id="RULE-003",
        rule_name="Runway Availability Risk",
        triggered=triggered,
        severity="HIGH" if triggered else "LOW",
        message=(
            "The runway is reported unavailable. "
            "Further operational assessment is required."
            if triggered
            else "The runway is reported available."
        ),
    )