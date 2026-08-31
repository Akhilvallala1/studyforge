"""Ollama provider: one local model behind the same contract as the Anthropic one.

Two things here exist because a local runtime fails differently from a hosted API.

Context window. Ollama's default context is small (4096 tokens in current builds)
and it does not complain when a prompt overruns it: it drops the overflow, answers
from the fragment it kept, and reports success. Course generation feeds whole
documents in, so leaving num_ctx unset produces a plausible course written from the
first few pages of the source and nothing anywhere says so. num_ctx is therefore
always sent, and what Ollama reports evaluating is checked against it afterwards.

Errors. The Anthropic provider raises LLMCallError carrying whatever tokens the
failed call consumed, which is what lets MeteredLLM record it. This one used to let
raw httpx exceptions out, so a local setup's ordinary failures (Ollama not running,
model not pulled) escaped unmetered. Every failure now leaves as LLMCallError.
"""

import logging
import os

import httpx

from app.llm.base import LLMCallError, LLMResult

logger = logging.getLogger("studyforge.llm.ollama")

# Sized to the prompts this pipeline actually sends, against 6GB of VRAM.
#
# The prompts: a lesson call is the common case and by far the most frequent. It
# sends LESSON_SYSTEM (~1,600 chars) plus the one or two source segments the outline
# routed to it, and MAX_CHUNK_CHARS caps a segment at 8,000 chars, so the material
# tops out near 16,100 chars with its labels. At roughly 4 chars per token that is
# ~4,400 input tokens, and a lesson with 3-6 quiz items runs ~1,200-2,500 output
# tokens: about 7,000 all in, which fits. An outline call sends every chunk, so it
# fits up to about three chunks (~24,000 chars, very roughly ten pages); past that
# the checks below say so rather than letting it pass. A remediation note is smaller
# than either (MAX_LESSONS x MAX_LESSON_CHARS is 12,000 chars of grounding).
#
# The hardware: on a 6GB card a 7-8B model at Q4_K_M is 4.1-4.7GB of weights.
# Llama-3.1-8B holds 128KB of KV cache per token at f16 (32 layers x 8 KV heads x
# 128 dims x 2 for K and V x 2 bytes), so 8192 tokens costs exactly 1GB. Weights
# plus cache plus compute buffers lands just under the 6GB line. Doubling this to
# 16384 adds another gigabyte, spills the model onto the CPU, and turns a twelve
# lesson course into something that races the 600s timeout on every call.
#
# Raise it with OLLAMA_NUM_CTX if you have the VRAM, or if a long document makes the
# checks below start complaining.
DEFAULT_NUM_CTX = 8192

# Used only to warn, before a call, that the material looks too big for the window.
# Deliberately generous: English prose runs nearer 3.5 chars per token, so this
# undercounts and the warning errs toward staying quiet rather than crying wolf.
CHARS_PER_TOKEN = 4

_REQUEST_TIMEOUT = 600


def _num_ctx_from_env() -> int:
    """OLLAMA_NUM_CTX, or the default if it is unset or not a positive integer.

    A bad value falls back loudly instead of raising: a typo in .env should not stop
    the server from starting, but it must not quietly become Ollama's 4096 either.
    """
    raw = os.environ.get("OLLAMA_NUM_CTX")
    if raw is None or not raw.strip():
        return DEFAULT_NUM_CTX
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        logger.warning(
            "OLLAMA_NUM_CTX=%r is not a positive integer; using %d instead",
            raw,
            DEFAULT_NUM_CTX,
        )
        return DEFAULT_NUM_CTX
    return value


class OllamaProvider:
    name = "ollama"
    is_paid = False

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        num_ctx: int | None = None,
    ):
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.1")
        self.num_ctx = num_ctx if num_ctx is not None else _num_ctx_from_env()

    def generate(self, system: str, prompt: str, max_tokens: int = 64000) -> LLMResult:
        self._warn_if_prompt_looks_too_long(system, prompt)
        body = self._post(system, prompt, max_tokens)
        input_tokens = body.get("prompt_eval_count")
        output_tokens = body.get("eval_count")
        text = self._message_content(body, input_tokens, output_tokens)
        self._reject_if_window_filled(input_tokens, output_tokens)
        return LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens)

    # ----------------------------------------------------------------------
    # Transport
    # ----------------------------------------------------------------------

    def _post(self, system: str, prompt: str, max_tokens: int) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"num_predict": max_tokens, "num_ctx": self.num_ctx},
                },
                timeout=_REQUEST_TIMEOUT,
            )
        except httpx.TimeoutException as exc:
            raise LLMCallError(
                f"Ollama at {self.base_url} did not answer within {_REQUEST_TIMEOUT}s. "
                f"A large model on a small GPU can take this long; try a smaller model "
                f"or shorter material."
            ) from exc
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            # Connection refused is the one everyone hits first: `ollama serve` is
            # not running, or OLLAMA_BASE_URL points somewhere else.
            raise LLMCallError(
                f"Could not reach Ollama at {self.base_url} ({type(exc).__name__}: {exc}). "
                f"Check that Ollama is running and OLLAMA_BASE_URL is right."
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMCallError(self._status_message(response)) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMCallError(
                f"Ollama returned a body that is not JSON: {response.text[:200]!r}"
            ) from exc
        if not isinstance(body, dict):
            raise LLMCallError(f"Ollama returned {type(body).__name__}, not a JSON object")
        return body

    def _status_message(self, response: httpx.Response) -> str:
        """What to tell the caller about an error status, including Ollama's own text."""
        detail = response.text[:200]
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            detail = payload["error"]
        if response.status_code == 404:
            # Ollama 404s both an unknown model and an unknown route, and the body
            # says which. Naming the pull is worth it: it is the fix nine times out
            # of ten and the message is the only place a self-hoster sees it.
            return (
                f"Ollama has no model {self.model!r} (HTTP 404: {detail}). "
                f"Run `ollama pull {self.model}` first."
            )
        return f"Ollama call failed with HTTP {response.status_code}: {detail}"

    def _message_content(
        self, body: dict, input_tokens: int | None, output_tokens: int | None
    ) -> str:
        message = body.get("message")
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str):
            # Tokens carried through even here: the model ran, so the call happened,
            # and a metered row with counts is more honest than no row at all.
            raise LLMCallError(
                f"Ollama's reply had no message content (keys: {sorted(body)})",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        return text

    # ----------------------------------------------------------------------
    # Truncation
    # ----------------------------------------------------------------------

    def _warn_if_prompt_looks_too_long(self, system: str, prompt: str) -> None:
        """Say so before the call when the material plainly will not fit.

        An estimate from character counts, so it only warns. It is here because it
        is the one signal that survives Ollama truncating to somewhere below the
        ceiling, which _reject_if_window_filled cannot see, and because it arrives
        before minutes of local GPU time rather than after.
        """
        estimated = (len(system) + len(prompt)) // CHARS_PER_TOKEN
        if estimated <= self.num_ctx:
            return
        logger.warning(
            "Prompt is about %d tokens against OLLAMA_NUM_CTX=%d: Ollama will silently "
            "drop whatever does not fit, and %s will answer from a fragment of the "
            "material. Raise OLLAMA_NUM_CTX or use shorter material.",
            estimated,
            self.num_ctx,
            self.model,
        )

    def _reject_if_window_filled(
        self, input_tokens: int | None, output_tokens: int | None
    ) -> None:
        """Fail the call when Ollama evaluated a prompt right up to the window.

        prompt_eval_count cannot exceed the context window, so reaching it means the
        prompt either exactly filled it, leaving no room to answer, or was cut down
        to fit. Either way the reply is not about the material that was sent, and a
        course written from a fragment is worse than a generation that failed: it
        looks finished, so nobody goes looking.

        Only the ceiling counts as proof. Comparing against the character estimate
        instead would misfire on a prompt cache hit, where Ollama reports only the
        tokens it newly evaluated and the count is legitimately small.
        """
        if input_tokens is None or input_tokens < self.num_ctx:
            return
        raise LLMCallError(
            f"Ollama evaluated {input_tokens} prompt tokens against a {self.num_ctx} token "
            f"context window, so the prompt was truncated to fit and {self.model} did not "
            f"see all of the material. Raise OLLAMA_NUM_CTX (costs VRAM) or use shorter "
            f"material.",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
