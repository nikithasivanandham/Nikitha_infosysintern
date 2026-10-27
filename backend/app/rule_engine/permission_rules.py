from typing import Literal

from pydantic import BaseModel, Field


# --------------------------------------------------
# 1. PERMISSION REQUEST INPUT
# --------------------------------------------------

class PermissionRequestInput(BaseModel):
    request_id: str = Field(
        ...,
        min_length=1
    )

    user_id: str = Field(
        ...,
        min_length=1
    )

    flight_number: str = Field(
        ...,
        min_length=2,
        max_length=10
    )

    requested_action: str = Field(
        ...,
        min_length=1
    )

    identity_verified: bool

    permission_valid: bool

    operational_block: bool

    requires_manual_review: bool = False


# --------------------------------------------------
# 2. DECISION RESULT
# --------------------------------------------------

class PermissionDecisionResult(BaseModel):
    request_id: str

    flight_number: str

    decision: Literal[
        "GRANT",
        "HOLD",
        "DELAY"
    ]

    reasons: list[str]

    advisory_only: bool = True


# --------------------------------------------------
# 3. PERMISSION DECISION ENGINE
# --------------------------------------------------

def evaluate_permission_request(
    request: PermissionRequestInput
) -> PermissionDecisionResult:

    reasons = []

    # Rule 1: An operational block takes priority.
    if request.operational_block:

        decision = "DELAY"

        reasons.append(
            "A configured operational blocking condition exists."
        )

    # Rule 2: Missing verification or invalid permission
    # prevents a positive recommendation.
    elif (
        not request.identity_verified
        or not request.permission_valid
    ):

        decision = "HOLD"

        if not request.identity_verified:
            reasons.append(
                "Identity verification is incomplete."
            )

        if not request.permission_valid:
            reasons.append(
                "Permission validity has not been established."
            )

    # Rule 3: Requests requiring human review remain on hold.
    elif request.requires_manual_review:

        decision = "HOLD"

        reasons.append(
            "Manual review is required before a decision."
        )

    # Rule 4: All configured checks passed.
    else:

        decision = "GRANT"

        reasons.append(
            "All configured demonstration checks passed."
        )

    return PermissionDecisionResult(
        request_id=request.request_id,
        flight_number=request.flight_number,
        decision=decision,
        reasons=reasons,
        advisory_only=True,
    )