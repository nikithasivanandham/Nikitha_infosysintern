from pydantic import ValidationError
from app.agents.schemas import PlanningResult
from app.agents.workflow import build_airport_workflow

def main():
    workflow = build_airport_workflow()
    initial_state = {
        "workflow_id": "WF-003",
        "airport": "HYD",
        "disruption": (
            "Heavy rainfall has been reported. "
            "Potential flight delays need investigation."
        ),
        "affected_flights": ["AI501", "AI502"],
        "planning_result": {},
        "status": "planning_started",
    }

    print("\n--- VALIDATING PLANNING AGENT OUTPUT ---")

    try:
        result = workflow.invoke(initial_state)

        validated_result = PlanningResult.model_validate(
            result["planning_result"]
        )

        print("Validation successful!")
        print("Workflow ID:", validated_result.workflow_id)
        print("Airport:", validated_result.airport)
        print("Planning objective:", validated_result.planning_objective)

        print(
            "Research requirements:",
            len(validated_result.research_requirements),
        )
        print(
            "Analysis requirements:",
            len(validated_result.analysis_requirements),
        )
        print(
            "Resource requirements:",
            len(validated_result.resource_requirements),
        )
        print(
            "Proposed steps:",
            len(validated_result.proposed_steps),
        )

        print("Agent status:", validated_result.status)
        print("Workflow status:", result["status"])

    except ValidationError as error:
        print("Validation failed:")
        print(error)

    except Exception as error:
        print("Workflow execution failed:")
        print(type(error).__name__, error)

if __name__ == "__main__":
    main()
