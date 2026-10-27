from pprint import pprint

from app.agents.workflow import build_airport_workflow


def main():
    print("\n=== PLANNING AGENT + RULE ENGINE TEST ===", flush=True)

    initial_state = {
        "workflow_id": "WF-RULE-001",
        "airport": "HYD",
        "disruption": "Heavy rainfall affecting airport operations",
        "affected_flights": ["AI501", "AI502"],
        "planning_result": {},
        "rule_results": [],
        "status": "started",
    }

    print("\nStarting airport workflow...", flush=True)

    workflow = build_airport_workflow()

    try:
        result = workflow.invoke(initial_state)

        print("\n=== WORKFLOW EXECUTION COMPLETED ===", flush=True)

        print("\nWorkflow status:", result.get("status"))

        print("\nPlanning Agent result:")
        pprint(result.get("planning_result"))

        print("\nRule Engine results:")
        pprint(result.get("rule_results"))

        assert result.get("planning_result"), (
            "Planning Agent did not produce a result."
        )

        assert len(result.get("rule_results", [])) == 2, (
            "Expected Rule Engine results for both affected flights."
        )

        print(
            "\nSUCCESS: Planning Agent and Rule Engine executed.",
            flush=True,
        )

    except Exception as error:
        print("\nWORKFLOW EXECUTION FAILED", flush=True)
        print("Error type:", type(error).__name__, flush=True)
        print("Error details:", str(error), flush=True)
        raise


if __name__ == "__main__":
    main()