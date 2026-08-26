from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMCallError(RuntimeError):
    """Raised when a provider call fails, possibly after consuming tokens (e.g. a refusal)."""

    def __init__(
        self,
        message: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ):
        super().__init__(message)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class LLMProvider(Protocol):
    name: str  # "anthropic" | "ollama" | "fake"
    model: str
    is_paid: bool  # True only for the anthropic provider

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> LLMResult:
        """Return the model's text response (plus token usage if reported) for a single
        system+user exchange."""
        ...
