import os

from app.llm.base import LLMProvider


def get_provider() -> LLMProvider:
    name = os.environ.get("STUDYFORGE_LLM_PROVIDER", "anthropic")
    if name == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    if name == "fake":
        from app.llm.fake_provider import FakeProvider

        return FakeProvider()
    from app.llm.anthropic_provider import AnthropicProvider

    return AnthropicProvider()
