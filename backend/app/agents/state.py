from typing import TypedDict


class PlanningAgentState(TypedDict):
    workflow_id: str
    airport: str
    disruption: str
    affected_flights: list[str]
    planning_objective: str
    research_requirements: list[str]
    analysis_requirements: list[str]
    resource_requirements: list[str]
    proposed_steps: list[str]
    status: str