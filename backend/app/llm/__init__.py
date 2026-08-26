import os

from app.llm.base import LLMProvider


def get_provider() -> LLMProvider:
    name = os.environ.get("STUDYFORGE_LLM_PROVIDER", "anthropic")
    if name == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    from app.llm.anthropic_provider import AnthropicProvider

    return AnthropicProvider()
