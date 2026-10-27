from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.agents.planning_agent import run_planning_agent
from app.rule_engine.engine import evaluate_operational_rules
from app.rule_engine.schemas import OperationalInput

class AirportWorkflowState(TypedDict):
    workflow_id: str
    airport: str
    disruption: str
    affected_flights: list[str]
    planning_result: dict
    rule_results: list[dict]
    status: str


def planning_node(state: AirportWorkflowState) -> dict:
    """Execute the Planning Agent."""

    result = run_planning_agent(
        workflow_id=state["workflow_id"],
        airport=state["airport"],
        disruption=state["disruption"],
        affected_flights=state["affected_flights"],
    )

    return {
        "planning_result": result.model_dump(),
        "status": "planning_completed_pending_review",
    }

def rule_engine_node(state: AirportWorkflowState) -> dict:
    """Evaluate operational rules for affected flights."""

    airport = state["airport"].strip().upper()
    disruption = state["disruption"].lower()

    rule_results = []

    for flight in state["affected_flights"]:
        operational_input = OperationalInput(
            airport_code=airport,
            flight_number=flight,
            delay_minutes=0,
            rainfall_mm=10.0 if "rain" in disruption else 0.0,
            runway_available=True,
        )

        result = evaluate_operational_rules(operational_input)

        rule_results.append(result.model_dump())

    return {
        "rule_results": rule_results,
        "status": "planning_and_rules_completed_pending_review",
    }

def build_airport_workflow():
    graph = StateGraph(AirportWorkflowState)

    graph.add_node("planning_agent", planning_node)
    graph.add_node("rule_engine", rule_engine_node)

    graph.add_edge(START, "planning_agent")
    graph.add_edge("planning_agent", "rule_engine")
    graph.add_edge("rule_engine", END)

    return graph.compile()