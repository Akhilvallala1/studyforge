from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> str:
        """Return the model's text response for a single system+user exchange."""
        ...
