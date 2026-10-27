from pydantic import BaseModel, Field, model_validator


class GateAssignment(BaseModel):
    airport_code: str = Field(min_length=3, max_length=4)
    flight_number: str = Field(min_length=2, max_length=10)
    gate_id: str = Field(min_length=1)

    # Minutes after midnight.
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)

    @model_validator(mode="after")
    def validate_time_interval(self):
        if self.end_minute <= self.start_minute:
            raise ValueError(
                "Gate assignment end time must be later than start time."
            )
        return self


class GateConflictResult(BaseModel):
    airport_code: str
    gate_id: str
    first_flight: str
    second_flight: str
    conflict_detected: bool
    message: str
    advisory_only: bool = True


def detect_gate_conflict(
    first: GateAssignment,
    second: GateAssignment,
) -> GateConflictResult:

    if first.airport_code != second.airport_code:
        conflict = False
        message = "No comparison: assignments belong to different airports."

    elif first.gate_id != second.gate_id:
        conflict = False
        message = "No conflict: assignments use different gates."

    elif first.flight_number == second.flight_number:
        conflict = False
        message = "No conflict: both assignments identify the same flight."

    else:
        conflict = (
            first.start_minute < second.end_minute
            and second.start_minute < first.end_minute
        )

        if conflict:
            message = (
                f"Potential double-booking detected at gate {first.gate_id} "
                f"for flights {first.flight_number} and "
                f"{second.flight_number}."
            )
        else:
            message = "No overlapping gate assignments detected."

    return GateConflictResult(
        airport_code=first.airport_code,
        gate_id=first.gate_id,
        first_flight=first.flight_number,
        second_flight=second.flight_number,
        conflict_detected=conflict,
        message=message,
    )


def suggest_alternative_gates(
    airport_code: str,
    flight_number: str,
    start_minute: int,
    end_minute: int,
    candidate_gates: list[str],
    existing_assignments: list[GateAssignment],
) -> list[str]:
    """
    Return candidate gates without overlapping assignments.

    The caller must supply the candidate gate inventory and
    all relevant existing assignments for the time interval.
    """

    if not airport_code.strip():
        raise ValueError("Airport code is required.")

    if not flight_number.strip():
        raise ValueError("Flight number is required.")

    if not 0 <= start_minute < end_minute <= 1440:
        raise ValueError("Invalid requested time interval.")

    available_gates = []

    for gate_id in candidate_gates:

        if not gate_id.strip():
            continue

        conflict_found = False

        for assignment in existing_assignments:

            # Only assignments at this airport matter.
            if assignment.airport_code != airport_code:
                continue

            # A flight cannot conflict with its own existing assignment.
            if assignment.flight_number == flight_number:
                continue

            # Different gates cannot conflict with this candidate gate.
            if assignment.gate_id != gate_id:
                continue

            # Check whether the requested interval overlaps the assignment.
            overlaps = (
                start_minute < assignment.end_minute
                and assignment.start_minute < end_minute
            )

            if overlaps:
                conflict_found = True
                break

        if not conflict_found:
            available_gates.append(gate_id)

    return available_gates