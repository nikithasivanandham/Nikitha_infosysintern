from pathlib import Path

from dotenv import load_dotenv

# Load the project .env file before importing the LLM configuration.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

from app.agents.llm import get_llm


def main():
    print("Testing LangChain Gemini integration...", flush=True)

    try:
        llm = get_llm()

        print("Configured model:", llm.model, flush=True)
        print("Sending a short request...", flush=True)

        response = llm.invoke(
            "Reply with exactly: Gemini connection successful."
        )

        print("SUCCESS", flush=True)
        print("Gemini response:", response.content, flush=True)

    except Exception as error:
        print("FAILED", flush=True)
        print("Error type:", type(error).__name__, flush=True)
        print("Error details:", str(error), flush=True)


if __name__ == "__main__":
    main()