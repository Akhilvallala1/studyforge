import os

import anthropic


class AnthropicProvider:
    def __init__(self, model: str | None = None):
        # Credentials resolve from ANTHROPIC_API_KEY or an `ant auth login` profile.
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("STUDYFORGE_MODEL", "claude-opus-5")

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> str:
        # Course generation produces long outputs — stream to avoid HTTP timeouts.
        # Thinking is adaptive by default on claude-opus-5; no thinking param needed.
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "refusal":
            detail = response.stop_details.explanation if response.stop_details else ""
            raise RuntimeError(f"Model refused the request: {detail}")
        return "".join(block.text for block in response.content if block.type == "text")
