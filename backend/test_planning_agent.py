from app.agents.planning_agent import run_planning_agent


def main():
    result = run_planning_agent(
        workflow_id="WF-001",
        airport="HYD",
        disruption=(
            "Heavy rainfall has been reported. "
            "Potential flight delays need investigation."
        ),
        affected_flights=["AI501", "AI502"],
    )

    print("\n--- PLANNING AGENT RESULT ---")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()