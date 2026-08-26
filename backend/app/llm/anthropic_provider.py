import os

import anthropic

from app.llm.base import LLMCallError, LLMResult


class AnthropicProvider:
    name = "anthropic"
    is_paid = True

    def __init__(self, model: str | None = None):
        # Credentials resolve from ANTHROPIC_API_KEY or an `ant auth login` profile.
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("STUDYFORGE_MODEL", "claude-opus-5")

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> LLMResult:
        # Course generation produces long outputs - stream to avoid HTTP timeouts.
        # Thinking is adaptive by default on claude-opus-5; no thinking param needed.
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
        input_tokens = getattr(response.usage, "input_tokens", None)
        output_tokens = getattr(response.usage, "output_tokens", None)
        if response.stop_reason == "refusal":
            detail = response.stop_details.explanation if response.stop_details else ""
            raise LLMCallError(
                f"Model refused the request: {detail}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens)
