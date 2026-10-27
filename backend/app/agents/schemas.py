from pydantic import BaseModel, Field


class PlanningResult(BaseModel):
    workflow_id: str

    airport: str = Field(
        min_length=3,
        max_length=4,
        description="Airport IATA code",
    )

    planning_objective: str = Field(
        min_length=1,
        description="Main objective of the planning workflow",
    )

    research_requirements: list[str] = Field(
        min_length=1,
        description="Information that must be collected",
    )

    analysis_requirements: list[str] = Field(
        min_length=1,
        description="Issues that must be analysed",
    )

    resource_requirements: list[str] = Field(
        min_length=1,
        description="Resources whose availability must be checked",
    )

    proposed_steps: list[str] = Field(
        min_length=1,
        description="Ordered steps for investigating the disruption",
    )

    status: str = "planning_completed_pending_review"