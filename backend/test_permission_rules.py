from pydantic import ValidationError

from app.rule_engine.permission_rules import (
    PermissionRequestInput,
    evaluate_permission_request,
)


def main():

    print("\n=== PERMISSION DECISION TESTS ===")

    # --------------------------------------------------
    # Test 1: All configured checks pass
    # --------------------------------------------------

    request1 = PermissionRequestInput(
        request_id="REQ-001",
        user_id="pilot001",
        flight_number="AI501",
        requested_action="gate_access",
        identity_verified=True,
        permission_valid=True,
        operational_block=False,
        requires_manual_review=False,
    )

    result1 = evaluate_permission_request(request1)

    assert result1.decision == "GRANT"
    assert result1.advisory_only is True

    print("Test 1 passed: Valid request recommends GRANT.")

    # --------------------------------------------------
    # Test 2: Identity verification is incomplete
    # --------------------------------------------------

    request2 = PermissionRequestInput(
        request_id="REQ-002",
        user_id="pilot002",
        flight_number="AI502",
        requested_action="gate_access",
        identity_verified=False,
        permission_valid=True,
        operational_block=False,
        requires_manual_review=False,
    )

    result2 = evaluate_permission_request(request2)

    assert result2.decision == "HOLD"

    print("Test 2 passed: Unverified identity recommends HOLD.")

    # --------------------------------------------------
    # Test 3: Permission validity is not established
    # --------------------------------------------------

    request3 = PermissionRequestInput(
        request_id="REQ-003",
        user_id="pilot003",
        flight_number="AI503",
        requested_action="gate_access",
        identity_verified=True,
        permission_valid=False,
        operational_block=False,
        requires_manual_review=False,
    )

    result3 = evaluate_permission_request(request3)

    assert result3.decision == "HOLD"

    print(
        "Test 3 passed: Unestablished permission validity "
        "recommends HOLD."
    )

    # --------------------------------------------------
    # Test 4: An operational block exists
    # --------------------------------------------------

    request4 = PermissionRequestInput(
        request_id="REQ-004",
        user_id="pilot004",
        flight_number="AI504",
        requested_action="gate_access",
        identity_verified=True,
        permission_valid=True,
        operational_block=True,
        requires_manual_review=False,
    )

    result4 = evaluate_permission_request(request4)

    assert result4.decision == "DELAY"

    print("Test 4 passed: Operational block recommends DELAY.")

    # --------------------------------------------------
    # Test 5: Manual review is required
    # --------------------------------------------------

    request5 = PermissionRequestInput(
        request_id="REQ-005",
        user_id="pilot005",
        flight_number="AI505",
        requested_action="gate_access",
        identity_verified=True,
        permission_valid=True,
        operational_block=False,
        requires_manual_review=True,
    )

    result5 = evaluate_permission_request(request5)

    assert result5.decision == "HOLD"

    print("Test 5 passed: Manual review recommends HOLD.")

    # --------------------------------------------------
    # Test 6: Operational block takes priority
    # --------------------------------------------------

    request6 = PermissionRequestInput(
        request_id="REQ-006",
        user_id="pilot006",
        flight_number="AI506",
        requested_action="gate_access",
        identity_verified=False,
        permission_valid=False,
        operational_block=True,
        requires_manual_review=True,
    )

    result6 = evaluate_permission_request(request6)

    assert result6.decision == "DELAY"

    print("Test 6 passed: Operational block takes priority.")

    # --------------------------------------------------
    # Test 7: Missing required request_id
    # --------------------------------------------------

    try:

        PermissionRequestInput(
            # request_id deliberately omitted
            user_id="pilot007",
            flight_number="AI507",
            requested_action="gate_access",
            identity_verified=True,
            permission_valid=True,
            operational_block=False,
        )

        raise AssertionError(
            "Missing request_id should have been rejected."
        )

    except ValidationError as exc:

        missing_fields = {
            error["loc"][0]
            for error in exc.errors()
        }

        assert "request_id" in missing_fields

        print(
            "Test 7 passed: Missing required request_id rejected."
        )

    # --------------------------------------------------
    # Display a valid decision result
    # --------------------------------------------------

    print("\nExample permission decision result:")

    print(result1.model_dump())

    print("\nAll seven permission decision tests passed.")


if __name__ == "__main__":
    main()