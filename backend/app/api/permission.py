import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.permissions import require_roles
from app.schemas.approval import PermissionReviewRequest
from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.database.audit import log_audit_event
from app.schemas.permission import (
    PermissionRequestCreate,
    PermissionRequestResponse,
)


router = APIRouter(
    prefix="/permissions",
    tags=["Pilot Permissions"],
)


@router.post(
    "/requests",
    response_model=PermissionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_permission_request(
    request: PermissionRequestCreate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "pilot":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pilots can submit permission requests",
        )

    request_id = str(uuid.uuid4())

    connection = get_db_connection()

    try:
        connection.execute(
            """
            INSERT INTO permission_requests (
                request_id,
                pilot_user_id,
                flight_number,
                requested_action,
                reason
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                request_id,
                current_user["user_id"],
                request.flight_number,
                request.requested_action,
                request.reason,
            ),
        )

        connection.commit()
        log_audit_event(
            user_id=current_user["user_id"],
            action="PERMISSION_REQUEST_CREATED",
            resource_type="permission_request",
            resource_id=request_id,
            details={
                "flight_number": request.flight_number,
                "requested_action": request.requested_action,
                "status": "pending",
            },
        )

        return PermissionRequestResponse(
            request_id=request_id,
            pilot_user_id=current_user["user_id"],
            flight_number=request.flight_number,
            requested_action=request.requested_action,
            reason=request.reason,
            status="pending",
        )

    finally:
        connection.close()


@router.get("/requests")
def get_my_permission_requests(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "pilot":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only pilots can access this endpoint",
        )

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                request_id,
                pilot_user_id,
                flight_number,
                requested_action,
                reason,
                status,
                created_at
            FROM permission_requests
            WHERE pilot_user_id = ?
            ORDER BY created_at DESC
            """,
            (current_user["user_id"],),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()

@router.patch("/requests/{request_id}/review")
def review_permission_request(
    request_id: str,
    review: PermissionReviewRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT request_id, status
            FROM permission_requests
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Permission request not found",
            )

        if row["status"] != "pending":
            raise HTTPException(
                status_code=409,
                detail="This permission request has already been reviewed",
            )

        connection.execute(
            """
            UPDATE permission_requests
            SET status = ?,
                reviewed_by = ?,
                review_comment = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE request_id = ?
              AND status = 'pending'
            """,
            (
                review.decision,
                current_user["user_id"],
                review.review_comment,
                request_id,
            ),
        )

        connection.commit()

        log_audit_event(
            user_id=current_user["user_id"],
            action=(
                "PERMISSION_REQUEST_APPROVED"
                if review.decision == "approved"
                else "PERMISSION_REQUEST_REJECTED"
            ),
            resource_type="permission_request",
            resource_id=request_id,
            details={
                "decision": review.decision,
                "review_comment": review.review_comment,
            },
        )

        return {
            "request_id": request_id,
            "status": review.decision,
            "reviewed_by": current_user["user_id"],
            "review_comment": review.review_comment,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()