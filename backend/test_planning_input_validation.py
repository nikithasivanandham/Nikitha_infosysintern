from app.agents.planning_agent import run_planning_agent


def main():
    print("--- PLANNING AGENT INPUT VALIDATION ---")

    test_cases = [
        {
            "name": "Empty workflow ID",
            "workflow_id": "",
            "airport": "HYD",
            "disruption": "Heavy rainfall",
            "affected_flights": ["AI501"],
        },
        {
            "name": "Invalid airport code length",
            "workflow_id": "WF-201",
            "airport": "HY",
            "disruption": "Heavy rainfall",
            "affected_flights": ["AI501"],
        },
        {
            "name": "Empty disruption",
            "workflow_id": "WF-202",
            "airport": "HYD",
            "disruption": "",
            "affected_flights": ["AI501"],
        },
        {
            "name": "No affected flights",
            "workflow_id": "WF-203",
            "airport": "HYD",
            "disruption": "Heavy rainfall",
            "affected_flights": [],
        },
    ]

    for test in test_cases:
        print("\nTest:", test["name"])

        try:
            run_planning_agent(
                workflow_id=test["workflow_id"],
                airport=test["airport"],
                disruption=test["disruption"],
                affected_flights=test["affected_flights"],
            )

            print("FAILED: Invalid input was accepted.")

        except ValueError as error:
            print("PASSED:", error)

        except Exception as error:
            print(
                "UNEXPECTED ERROR:",
                type(error).__name__,
                error,
            )


if __name__ == "__main__":
    main()