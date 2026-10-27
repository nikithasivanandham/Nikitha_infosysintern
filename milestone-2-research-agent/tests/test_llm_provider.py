import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from app.config import Settings
from app.providers.llm_provider import LLMConfigError, get_llm, is_llm_configured


def test_gemini_configured_constructs_chat_model():
    fake_key = "AIzaSyFakeSecretKey12345"
    s = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY=fake_key,
        GEMINI_MODEL="gemini-1.5-flash",
        REQUEST_TIMEOUT_SECONDS=25,
    )

    llm = get_llm(s)
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model == "gemini-1.5-flash"
    assert llm.temperature == 0.0
    assert llm.max_retries == 1


def test_gemini_missing_key_raises_config_error():
    fake_key = "AIzaSyFakeSecretKey12345"
    s = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY="",
        GEMINI_MODEL="gemini-1.5-flash",
    )

    with pytest.raises(LLMConfigError) as exc_info:
        get_llm(s)
    msg = str(exc_info.value)
    assert "GOOGLE_API_KEY" in msg
    assert fake_key not in msg


def test_gemini_missing_model_raises_config_error():
    s = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY="valid-looking-key",
        GEMINI_MODEL="",
    )

    with pytest.raises(LLMConfigError) as exc_info:
        get_llm(s)
    msg = str(exc_info.value)
    assert "GEMINI_MODEL" in msg


def test_ollama_configured_constructs_chat_model():
    s = Settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="llama3",
        REQUEST_TIMEOUT_SECONDS=20,
    )

    llm = get_llm(s)
    assert isinstance(llm, ChatOllama)
    assert llm.model == "llama3"
    assert llm.base_url == "http://localhost:11434"
    assert llm.temperature == 0.0


def test_ollama_missing_parameters_raises_config_error():
    s1 = Settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="",
        OLLAMA_MODEL="llama3",
    )
    with pytest.raises(LLMConfigError) as exc1:
        get_llm(s1)
    assert "OLLAMA_BASE_URL" in str(exc1.value)

    s2 = Settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="",
    )
    with pytest.raises(LLMConfigError) as exc2:
        get_llm(s2)
    assert "OLLAMA_MODEL" in str(exc2.value)


def test_unsupported_provider_raises_config_error():
    s = Settings(LLM_PROVIDER="gemini")
    object.__setattr__(s, "LLM_PROVIDER", "anthropic")

    with pytest.raises(LLMConfigError) as exc_info:
        get_llm(s)
    assert "Unsupported LLM_PROVIDER" in str(exc_info.value)


def test_is_llm_configured():
    # Valid gemini
    s_gemini = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY="some-key",
        GEMINI_MODEL="gemini-1.5-flash",
    )
    assert is_llm_configured(s_gemini) is True

    # Incomplete gemini
    s_gemini_nokey = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY="",
        GEMINI_MODEL="gemini-1.5-flash",
    )
    assert is_llm_configured(s_gemini_nokey) is False

    # Valid ollama
    s_ollama = Settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="llama3",
    )
    assert is_llm_configured(s_ollama) is True

    # Incomplete ollama
    s_ollama_nomodel = Settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="",
    )
    assert is_llm_configured(s_ollama_nomodel) is False

    # Invalid provider
    s_invalid = Settings(LLM_PROVIDER="gemini")
    object.__setattr__(s_invalid, "LLM_PROVIDER", "unsupported")
    assert is_llm_configured(s_invalid) is False


def test_error_messages_never_leak_fake_secret_key():
    fake_secret = "AIzaSySuperSecretKeyXYZ"
    s = Settings(
        LLM_PROVIDER="gemini",
        GOOGLE_API_KEY=fake_secret,
        GEMINI_MODEL="",  # will trigger model error
    )
    with pytest.raises(LLMConfigError) as exc_info:
        get_llm(s)

    error_msg = str(exc_info.value)
    assert fake_secret not in error_msg
