from core.config import LLM_PROVIDER
from services.llm.base import LLMProvider
from services.llm.mock import MockLLMProvider


def get_llm_provider() -> LLMProvider:
    if LLM_PROVIDER == "mock":
        return MockLLMProvider()

    if LLM_PROVIDER in {"openai-compatible", "ollama", "vllm"}:
        from services.llm.openai_compatible import (
            OpenAICompatibleProvider,
        )

        return OpenAICompatibleProvider()

    raise RuntimeError(
        f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}"
    )
