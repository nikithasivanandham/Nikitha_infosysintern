import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.workflow import WorkflowCreate, WorkflowResponse
from app.agents.workflow import build_airport_workflow


router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
)


@router.post(
    "/",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_workflow(
    request: WorkflowCreate,
    current_user: dict = Depends(get_current_user),
):
    # Validate the input required by the Planning Agent.
    input_data = request.input_data

    required_fields = [
        "airport",
        "disruption",
        "affected_flights",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in input_data
    ]

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Missing required planning inputs.",
                "missing_fields": missing_fields,
            },
        )

    if not isinstance(input_data["airport"], str):
        raise HTTPException(
            status_code=422,
            detail="airport must be a string.",
        )

    if not isinstance(input_data["disruption"], str):
        raise HTTPException(
            status_code=422,
            detail="disruption must be a string.",
        )

    if (
        not isinstance(input_data["affected_flights"], list)
        or not input_data["affected_flights"]
        or not all(
            isinstance(flight, str) and flight.strip()
            for flight in input_data["affected_flights"]
        )
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "affected_flights must be a non-empty "
                "list of non-empty strings."
            ),
        )

    workflow_id = str(uuid.uuid4())
    user_id = current_user["user_id"]

    connection = get_db_connection()

    try:
        # Save the workflow before invoking Gemini.
        connection.execute(
            """
            INSERT INTO workflows (
                workflow_id,
                workflow_type,
                status,
                requested_by,
                input_data,
                decision,
                planning_result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workflow_id,
                request.workflow_type,
                "pending",
                user_id,
                json.dumps(input_data),
                None,
                None,
            ),
        )

        connection.commit()

        # Invoke the existing LangGraph workflow.
        initial_state = {
            "workflow_id": workflow_id,
            "airport": input_data["airport"],
            "disruption": input_data["disruption"],
            "affected_flights": input_data["affected_flights"],
            "planning_result": {},
            "status": "pending",
        }

        try:
            workflow = build_airport_workflow()
            result = workflow.invoke(initial_state)

        except Exception:
            connection.execute(
                """
                UPDATE workflows
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE workflow_id = ?
                  AND requested_by = ?
                """,
                (
                    "failed",
                    workflow_id,
                    user_id,
                ),
            )

            connection.commit()

            # Log the full exception server-side.
            from app.logger import logger

            logger.exception(
                "Planning workflow execution failed: %s",
                workflow_id,
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": (
                        "The planning workflow could not "
                        "complete. Check the server logs."
                    ),
                    "workflow_id": workflow_id,
                    "status": "failed",
                },
            )

        planning_result = result.get("planning_result")

        if not isinstance(planning_result, dict) or not planning_result:
            connection.execute(
                """
                UPDATE workflows
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE workflow_id = ?
                  AND requested_by = ?
                """,
                (
                    "failed",
                    workflow_id,
                    user_id,
                ),
            )

            connection.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "message": (
                        "The Planning Agent returned "
                        "no valid planning result."
                    ),
                    "workflow_id": workflow_id,
                    "status": "failed",
                },
            )

        # Store the planning result separately from the decision.
        final_status = result.get(
            "status",
            "planning_completed_pending_review",
        )

        connection.execute(
            """
            UPDATE workflows
            SET status = ?,
                planning_result = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE workflow_id = ?
              AND requested_by = ?
            """,
            (
                final_status,
                json.dumps(planning_result),
                workflow_id,
                user_id,
            ),
        )

        connection.commit()

        return WorkflowResponse(
            workflow_id=workflow_id,
            workflow_type=request.workflow_type,
            status=final_status,
            requested_by=user_id,
            input_data=input_data,
            decision=None,
            planning_result=planning_result,
        )

    finally:
        connection.close()


@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT *
            FROM workflows
            WHERE workflow_id = ?
              AND requested_by = ?
            """,
            (
                workflow_id,
                current_user["user_id"],
            ),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        workflow = dict(row)

        workflow["input_data"] = json.loads(
            workflow["input_data"]
        )

        if workflow.get("planning_result"):
            workflow["planning_result"] = json.loads(
                workflow["planning_result"]
            )
        else:
            workflow["planning_result"] = None

        return workflow

    finally:
        connection.close()


@router.get("/{workflow_id}/status")
def get_workflow_status(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT workflow_id, status, decision
            FROM workflows
            WHERE workflow_id = ?
              AND requested_by = ?
            """,
            (
                workflow_id,
                current_user["user_id"],
            ),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found",
            )

        return {
            "workflow_id": row["workflow_id"],
            "status": row["status"],
            "decision": row["decision"],
        }

    finally:
        connection.close()