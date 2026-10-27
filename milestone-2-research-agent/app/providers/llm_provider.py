"""LLM provider adapter supporting Google Gemini and Ollama via LangChain.

Documentation & Terms Check:
-----------------------------
- Checked on: 2026-10-27
- Packages:
  - langchain-google-genai==4.4.2 (backed by google-genai SDK)
  - langchain-ollama==1.1.0
  - langchain-core==1.7.0
- Model selection & API key passing:
  - Gemini: ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL, api_key=settings.GOOGLE_API_KEY, ...)
  - Ollama: ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, ...)
- Gemini Free Tier & Privacy Terms:
  - Free tier available in Google AI Studio for light models (e.g. Flash variants); requires no credit card.
  - Rate limits strictly enforced per project (RPM, TPM, RPD). Exceeding yields HTTP 429 RESOURCE_EXHAUSTED.
  - Crucial Data Policy: Under the Free Tier, Google may use input prompts and output generations
    to train/improve Google products and services. Paid tier (with billing attached) guarantees
    content is NOT used for model training.
- Guardrails:
  - Models must NEVER be hard-coded; driven purely by settings.
  - Temperature set to 0.0 for deterministic outputs.
  - Request timeout and max retries (at most 1) applied.
"""

from __future__ import annotations

from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.config import Settings


class LLMConfigError(Exception):
    """Raised when LLM configuration is missing, incomplete, or invalid."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def is_llm_configured(settings: Settings) -> bool:
    """Check whether the active LLM provider has all required configuration parameters.

    Never makes network calls and never raises exceptions.
    """
    try:
        provider = (settings.LLM_PROVIDER or "").strip().lower()
        if provider == "gemini":
            has_key = bool(settings.GOOGLE_API_KEY and settings.GOOGLE_API_KEY.strip())
            has_model = bool(settings.GEMINI_MODEL and settings.GEMINI_MODEL.strip())
            return has_key and has_model
        elif provider == "ollama":
            has_url = bool(settings.OLLAMA_BASE_URL and settings.OLLAMA_BASE_URL.strip())
            has_model = bool(settings.OLLAMA_MODEL and settings.OLLAMA_MODEL.strip())
            return has_url and has_model
        return False
    except Exception:
        return False


def get_llm(settings: Settings) -> BaseChatModel:
    """Construct and return a configured LangChain BaseChatModel.

    Raises:
        LLMConfigError: If required configuration variables are missing or provider unsupported.
    Never makes network calls upon construction. Never logs secrets.
    """
    provider = (settings.LLM_PROVIDER or "").strip().lower()

    if provider == "gemini":
        key = (settings.GOOGLE_API_KEY or "").strip()
        model = (settings.GEMINI_MODEL or "").strip()

        if not key and not model:
            raise LLMConfigError(
                "Gemini provider requires environment variables GOOGLE_API_KEY and GEMINI_MODEL."
            )
        if not key:
            raise LLMConfigError(
                "Gemini provider requires environment variable GOOGLE_API_KEY."
            )
        if not model:
            raise LLMConfigError(
                "Gemini provider requires environment variable GEMINI_MODEL."
            )

        timeout = float(settings.REQUEST_TIMEOUT_SECONDS)
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=key,
            temperature=0.0,
            timeout=timeout,
            max_retries=1,
        )

    elif provider == "ollama":
        base_url = (settings.OLLAMA_BASE_URL or "").strip()
        model = (settings.OLLAMA_MODEL or "").strip()

        if not base_url and not model:
            raise LLMConfigError(
                "Ollama provider requires environment variables OLLAMA_BASE_URL and OLLAMA_MODEL."
            )
        if not base_url:
            raise LLMConfigError(
                "Ollama provider requires environment variable OLLAMA_BASE_URL."
            )
        if not model:
            raise LLMConfigError(
                "Ollama provider requires environment variable OLLAMA_MODEL."
            )

        timeout = float(settings.REQUEST_TIMEOUT_SECONDS)
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=0.0,
            client_kwargs={"timeout": timeout},
            max_retries=1,
        )

    else:
        raise LLMConfigError(
            f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. Must be 'gemini' or 'ollama'."
        )
