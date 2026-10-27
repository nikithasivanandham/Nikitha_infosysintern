from app.agents.llm import get_llm
from app.agents.prompts import PLANNING_AGENT_PROMPT
from app.agents.schemas import PlanningResult


def run_planning_agent(
    workflow_id: str,
    airport: str,
    disruption: str,
    affected_flights: list[str],
) -> PlanningResult:

    if not workflow_id.strip():
        raise ValueError("Workflow ID cannot be empty.")

    airport = airport.strip().upper()

    if not 3 <= len(airport) <= 4:
        raise ValueError("Airport code must contain 3 or 4 characters.")

    if not disruption.strip():
        raise ValueError("Disruption description cannot be empty.")

    if not affected_flights:
        raise ValueError("At least one affected flight must be provided.")

    llm = get_llm()

    structured_llm = llm.with_structured_output(PlanningResult)

    planning_chain = PLANNING_AGENT_PROMPT | structured_llm

    result = planning_chain.invoke(
        {
            "workflow_id": workflow_id,
            "airport": airport,
            "disruption": disruption,
            "affected_flights": ", ".join(affected_flights),
        }
    )

    if not isinstance(result, PlanningResult):
        raise TypeError("Planning Agent did not return a valid PlanningResult.")

    return result