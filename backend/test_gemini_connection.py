from app.agents.llm import get_llm


def main():
    llm = get_llm()

    response = llm.invoke(
        "Reply with exactly: Planning Agent Gemini connection successful."
    )

    print("Gemini response:")
    print(response.content)


if __name__ == "__main__":
    main()