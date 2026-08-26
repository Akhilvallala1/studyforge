import os

import httpx

from app.llm.base import LLMResult


class OllamaProvider:
    name = "ollama"
    is_paid = False

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> LLMResult:
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=600,
        )
        response.raise_for_status()
        body = response.json()
        text = body["message"]["content"]
        return LLMResult(
            text=text,
            input_tokens=body.get("prompt_eval_count"),
            output_tokens=body.get("eval_count"),
        )
