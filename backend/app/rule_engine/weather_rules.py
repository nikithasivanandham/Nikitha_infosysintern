from typing import Literal

from pydantic import BaseModel, Field


# --------------------------------------------------
# 1. WEATHER INPUT SCHEMA
# --------------------------------------------------

class WeatherConditions(BaseModel):
    airport_code: str = Field(
        ...,
        min_length=3,
        max_length=4
    )

    flight_number: str = Field(
        ...,
        min_length=2,
        max_length=10
    )

    rainfall_mm: float = Field(
        default=0.0,
        ge=0
    )

    visibility_m: float = Field(
        default=10000.0,
        ge=0
    )

    wind_speed_kmh: float = Field(
        default=0.0,
        ge=0
    )


# --------------------------------------------------
# 2. WEATHER RISK RESULT SCHEMA
# --------------------------------------------------

class WeatherRiskResult(BaseModel):
    airport_code: str

    flight_number: str

    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    triggered_rules: int = Field(
        ge=0
    )

    messages: list[str]

    advisory_only: bool = True


# --------------------------------------------------
# 3. WEATHER RISK EVALUATION
# --------------------------------------------------

def evaluate_weather_risk(
    conditions: WeatherConditions
) -> WeatherRiskResult:

    messages = []

    # Illustrative demonstration thresholds.
    # These are NOT official aviation safety limits.

    if conditions.rainfall_mm >= 10.0:
        messages.append(
            "Heavy-rainfall threshold triggered."
        )

    if conditions.visibility_m < 1000.0:
        messages.append(
            "Low-visibility threshold triggered."
        )

    if conditions.wind_speed_kmh >= 40.0:
        messages.append(
            "High-wind threshold triggered."
        )

    triggered_rules = len(messages)

    # Determine a demonstration risk category.
    if triggered_rules >= 2:
        risk_level = "HIGH"

    elif triggered_rules == 1:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    # Add a message when no weather threshold is triggered.
    if triggered_rules == 0:
        messages.append(
            "No configured weather thresholds were triggered."
        )

    result = WeatherRiskResult(
        airport_code=conditions.airport_code,
        flight_number=conditions.flight_number,
        risk_level=risk_level,
        triggered_rules=triggered_rules,
        messages=messages,
        advisory_only=True
    )

    return result