import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# Load the project's .env file explicitly.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

api_key = os.getenv("GOOGLE_API_KEY")
model_name = os.getenv("GEMINI_MODEL")

if not api_key:
    raise ValueError("GOOGLE_API_KEY is missing from .env")

if not model_name:
    raise ValueError("GEMINI_MODEL is missing from .env")

print(f"Testing model: {model_name}")
print("Sending a short request directly to Gemini...")

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model=model_name,
        contents="Reply with exactly: Gemini direct test successful.",
    )
    print("SUCCESS")
    print(response.text)

except Exception as exc:
    print("FAILED")
    print("Error type:", type(exc).__name__)
    print("Error details:", exc)

finally:
    client.close()