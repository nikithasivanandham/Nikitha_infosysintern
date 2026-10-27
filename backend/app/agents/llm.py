import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def get_llm():
    model_name = os.getenv("GEMINI_MODEL")
    api_key = os.getenv("GOOGLE_API_KEY")

    if not model_name:
        raise ValueError("GEMINI_MODEL is missing from .env")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY is missing from .env")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
        max_retries=2,
        timeout=120,
    )