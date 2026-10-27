from pydantic import BaseModel, Field, model_validator


class RunwaySlot(BaseModel):
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

    runway_id: str = Field(
        ...,
        min_length=1
    )

    # Minutes after midnight.
    # 10:00 AM = 600
    # 10:30 AM = 630
    # Midnight at the end of the day = 1440.

    start_minute: int = Field(
        ...,
        ge=0,
        le=1439
    )

    end_minute: int = Field(
        ...,
        ge=1,
        le=1440
    )

    @model_validator(mode="after")
    def validate_time_interval(self):
        if self.end_minute <= self.start_minute:
            raise ValueError(
                "End time must be later than start time."
            )

        return self


class RunwayConflictResult(BaseModel):
    airport_code: str
    runway_id: str

    first_flight: str
    second_flight: str

    conflict_detected: bool

    message: str

    advisory_only: bool = True


def detect_runway_conflict(
    first: RunwaySlot,
    second: RunwaySlot
) -> RunwayConflictResult:

    # Both flights must belong to the same airport.
    if first.airport_code != second.airport_code:
        return RunwayConflictResult(
            airport_code=first.airport_code,
            runway_id=first.runway_id,
            first_flight=first.flight_number,
            second_flight=second.flight_number,
            conflict_detected=False,
            message=(
                "No comparison performed: flights belong "
                "to different airports."
            ),
        )

    # Different runways do not trigger this particular rule.
    if first.runway_id != second.runway_id:
        return RunwayConflictResult(
            airport_code=first.airport_code,
            runway_id=first.runway_id,
            first_flight=first.flight_number,
            second_flight=second.flight_number,
            conflict_detected=False,
            message="No conflict detected: flights use different runways.",
        )

    # Do not compare a flight slot against itself.
    if first.flight_number == second.flight_number:
        return RunwayConflictResult(
            airport_code=first.airport_code,
            runway_id=first.runway_id,
            first_flight=first.flight_number,
            second_flight=second.flight_number,
            conflict_detected=False,
            message="No conflict detected: both entries identify the same flight.",
        )

    # Two intervals overlap when each begins before the other ends.
    overlap = (
        first.start_minute < second.end_minute
        and second.start_minute < first.end_minute
    )

    if overlap:
        message = (
            f"Potential runway scheduling conflict between "
            f"{first.flight_number} and {second.flight_number} "
            f"on runway {first.runway_id}."
        )
    else:
        message = (
            f"No time overlap detected between "
            f"{first.flight_number} and {second.flight_number}."
        )

    return RunwayConflictResult(
        airport_code=first.airport_code,
        runway_id=first.runway_id,
        first_flight=first.flight_number,
        second_flight=second.flight_number,
        conflict_detected=overlap,
        message=message,
    )