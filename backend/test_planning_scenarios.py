from app.agents.workflow import build_airport_workflow
from app.agents.schemas import PlanningResult


def run_scenario(workflow_id, airport, disruption, affected_flights):
    print("\n" + "=" * 60)
    print("Testing scenario:", workflow_id)
    print("=" * 60)

    workflow = build_airport_workflow()

    initial_state = {
        "workflow_id": workflow_id,
        "airport": airport,
        "disruption": disruption,
        "affected_flights": affected_flights,
        "planning_result": {},
        "status": "planning_started",
    }

    try:
        result = workflow.invoke(initial_state)

        validated_result = PlanningResult.model_validate(
            result["planning_result"]
        )

        print("Validation: SUCCESS")
        print("Airport:", validated_result.airport)
        print("Disruption:", disruption)
        print("Planning objective:", validated_result.planning_objective)

        print("\nResearch requirements:")
        for item in validated_result.research_requirements:
            print("-", item)

        print("\nProposed steps:")
        for index, step in enumerate(
            validated_result.proposed_steps, start=1
        ):
            print(f"{index}. {step}")

        print("\nWorkflow status:", result["status"])

    except Exception as error:
        print("Scenario failed:", type(error).__name__, error)


if __name__ == "__main__":
    run_scenario(
        "WF-101",
        "HYD",
        "Heavy rainfall may affect runway conditions and flight operations.",
        ["AI501", "AI502"],
    )

    run_scenario(
        "WF-102",
        "HYD",
        "A possible runway closure requires investigation of flight delays.",
        ["AI601", "AI602"],
    )

    run_scenario(
        "WF-103",
        "HYD",
        "A shortage of ground handling staff may affect aircraft turnaround.",
        ["AI701", "AI702"],
    )