from typing import Any

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    workflow_type: str = Field(
        min_length=1,
        max_length=100,
    )

    input_data: dict[str, Any] = Field(
        default_factory=dict,
    )


class WorkflowResponse(BaseModel):
    workflow_id: str

    workflow_type: str

    status: str

    requested_by: str

    input_data: dict[str, Any]

    decision: str | None = None

    planning_result: dict[str, Any] | None = None

    rule_results: list[dict[str, Any]] = Field(default_factory=list)