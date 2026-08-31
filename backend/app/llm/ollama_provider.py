"""Ollama provider: one local model behind the same contract as the Anthropic one.

Two things here exist because a local runtime fails differently from a hosted API.

Context window. Ollama's default context is small (4096 tokens in the builds this
was written against) and it does not complain when a prompt overruns it: it drops
the overflow, answers
from the fragment it kept, and reports success. Course generation feeds whole
documents in, so leaving num_ctx unset produces a plausible course written from the
first few pages of the source and nothing anywhere says so. num_ctx is therefore
always sent, and what Ollama reports evaluating is checked against it afterwards.

The window fills from both ends, so both are watched. num_predict is capped to what
the window has left rather than passed through at the pipeline's 64000, because a
request eight times the window invites the runner to shift the context mid-reply and
finish the lesson with the source material evicted. And the post-call check counts
the reply as well as the prompt: on material that tokenizes denser than the
character estimate assumes, the prompt fits and the ANSWER is what runs out of room.

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

# Sized to the prompts this pipeline actually sends. Measured facts and estimates are
# marked apart below, because getting that wrong is how a comment becomes a lie.
#
# The prompts, MEASURED from the constants: a lesson call is the common case and by
# far the most frequent. It sends LESSON_SYSTEM (1,578 chars) plus the one or two
# source segments the outline routed to it, and MAX_CHUNK_CHARS caps a segment at
# 8,000, so the whole prompt tops out at 17,778 chars with its labels. An outline
# call sends every chunk. A remediation note is smaller than either (MAX_LESSONS x
# MAX_LESSON_CHARS is 12,000 chars of grounding).
#
# The prompts in tokens, ESTIMATED and not measured: at 4 chars per token that
# lesson prompt is ~4,400 input tokens, and a lesson with 3-6 quiz items is guessed
# at 1,200-2,500 output. Nobody has counted either against a real tokenizer. The
# estimate is also known to be optimistic (see CHARS_PER_TOKEN), which is exactly
# why _reject_if_window_filled judges the window from Ollama's reported counts and
# never from this arithmetic. Treat the 8192 as a starting point that the runtime
# checks will correct, not as a fit anyone has verified.
#
# The hardware, MEASURED on the target card (RTX 4050 laptop, 6GB) with
# llama3.1:8b at this num_ctx, via `ollama ps`:
#
#     NAME          SIZE     PROCESSOR          CONTEXT
#     llama3.1:8b   6.2 GB   32%/68% CPU/GPU    8192
#
# So 8192 does NOT fit in 6GB: about a third of the model runs on the CPU. The
# arithmetic that got here was right about the parts it could see and wrong about
# the slack. Llama-3.1-8B's KV cache is exactly 128KB per token at f16 (32 layers x
# 8 KV heads x 128 dims x 2 for K and V x 2 bytes), so 8192 tokens is 1GB, and
# 4.1-4.7GB of Q4_K_M weights leaves under a gigabyte for compute buffers that
# evidently want more.
#
# 8192 is kept anyway, deliberately. A CPU spill is slow and correct; a smaller
# window is fast and starts failing on documents that would otherwise work, and the
# whole position of this module is that an honest slow answer beats a fast wrong
# one. The lever for someone who wants the speed back is a smaller or more heavily
# quantized model, not a smaller window: the window is what decides whether the
# model sees the material at all. .env.example says this to the user.
DEFAULT_NUM_CTX = 8192

# Estimates only, never a verdict. Deliberately generous: English prose runs nearer
# 3.5 chars per token and markdown with code fences nearer 2.5, so this undercounts
# and everything built on it errs toward staying quiet. That optimism is why the
# checks that can FAIL a call are all built on Ollama's own reported counts instead.
CHARS_PER_TOKEN = 4

# How much of the window is held back for the reply when judging whether a prompt
# fits. Without it, a prompt that filled the window and left nothing to answer with
# read as a comfortable fit, since it never touched num_ctx. 2500 is the top of an
# ESTIMATED 1,200-2,500 token range for a lesson and its quiz; nobody has measured
# what a lesson really costs to write. It only has to be roughly right, since it
# governs a warning and never a failure.
OUTPUT_RESERVE_TOKENS = 2500

# A request must ask for at least one token to be a request. Reached only when the
# prompt estimate already fills the window, which is a call that will fail its
# post-call check anyway; this just keeps the body valid until it gets there.
MIN_NUM_PREDICT = 1

_REQUEST_TIMEOUT = 600


def _token_count(value: object, field: str) -> int | None:
    """Ollama's own count for `field`, or None when what came back is not a count.

    The response body is untrusted parsed input like any other, and these numbers do
    not merely get reported: prompt_eval_count is compared against num_ctx, and both
    end up in an Integer column. A string, a list, or a float used to reach that
    comparison and leave a raw TypeError, which is exactly the escape this module
    exists to close. bool is rejected by hand because it passes isinstance(x, int).

    Unparseable becomes unknown rather than fatal. It is the same state as Ollama
    not reporting the count at all, which is already handled, and the reply text
    itself may be perfectly good. The warning is what makes it findable, and it
    matters: an unknown count means the truncation checks have nothing to judge.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        logger.warning(
            "Ollama reported %s=%r, which is not a token count. Treating it as unknown, "
            "which means the context window check cannot run on this call.",
            field,
            value,
        )
        return None
    return value


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
        body = self._post(system, prompt, self._num_predict(system, prompt, max_tokens))
        input_tokens = _token_count(body.get("prompt_eval_count"), "prompt_eval_count")
        output_tokens = _token_count(body.get("eval_count"), "eval_count")
        text = self._message_content(body, input_tokens, output_tokens)
        self._reject_if_window_filled(input_tokens, output_tokens)
        return LLMResult(text=text, input_tokens=input_tokens, output_tokens=output_tokens)

    # ----------------------------------------------------------------------
    # Transport
    # ----------------------------------------------------------------------

    def _post(self, system: str, prompt: str, num_predict: int) -> dict:
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
                    "options": {"num_predict": num_predict, "num_ctx": self.num_ctx},
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

    def _estimated_prompt_tokens(self, system: str, prompt: str) -> int:
        return (len(system) + len(prompt)) // CHARS_PER_TOKEN

    def _prompt_budget(self) -> int:
        """How much of the window a prompt may use before the warning fires.

        The window has to hold the answer as well, and judging the prompt against
        the whole of it called a prompt that left no room to reply a comfortable
        fit. Half the window stands in when num_ctx is too small to give 2,500
        away: such a window cannot run this pipeline at all, but every call
        warning about it would only bury the ones that mean something.
        """
        return max(self.num_ctx - OUTPUT_RESERVE_TOKENS, self.num_ctx // 2)

    def _num_predict(self, system: str, prompt: str, max_tokens: int) -> int:
        """What to ask for, never more than the window could possibly hold.

        max_tokens arrives as the pipeline's 64000 default, eight times the whole
        window. Asking for that against a pinned num_ctx invites context shifting:
        once the window fills, the runner keeps generating by evicting the oldest
        tokens, which are the source material, so the model writes the rest of the
        lesson with the document gone while prompt_eval_count never moves. Capping
        to what is left makes generation stop at the ceiling instead, which surfaces
        as an unterminated JSON object and a visible failure.

        The estimate used here is the optimistic one, which makes the cap an upper
        bound on the real room: it can never cut a reply shorter than the window
        would have. Denser material means the cap is simply not the binding
        constraint, and _reject_if_window_filled catches that case from the counts.
        """
        available = self.num_ctx - self._estimated_prompt_tokens(system, prompt)
        return min(max_tokens, max(available, MIN_NUM_PREDICT))

    def _warn_if_prompt_looks_too_long(self, system: str, prompt: str) -> None:
        """Say so before the call when the material plainly will not fit.

        An estimate from character counts, so it only warns, and it is measured
        against the prompt's share of the window rather than all of it. It arrives
        before minutes of local GPU time rather than after, which is its whole
        value; the checks that can fail a call are the ones with evidence.
        """
        estimated = self._estimated_prompt_tokens(system, prompt)
        budget = self._prompt_budget()
        if estimated <= budget:
            return
        logger.warning(
            "Prompt is about %d tokens against a %d token window with about %d of that "
            "meant for the reply. If it overruns, Ollama drops the overflow without "
            "saying so and %s answers from a fragment of the material; if it only "
            "crowds the reply, the answer gets cut off instead. Raise OLLAMA_NUM_CTX "
            "or use shorter material.",
            estimated,
            self.num_ctx,
            self.num_ctx - budget,
            self.model,
        )

    def _reject_if_window_filled(
        self, input_tokens: int | None, output_tokens: int | None
    ) -> None:
        """Fail the call when the context window filled up, from either end.

        Two ways in, one rule: only the ceiling counts as proof. Neither branch
        rests on the character estimate, which is what makes them hold on material
        that tokenizes denser than CHARS_PER_TOKEN assumes.

        The prompt end. prompt_eval_count cannot exceed the window, so reaching it
        means the prompt either exactly filled it, leaving nothing to answer with,
        or was cut down to fit. A course written from a fragment is worse than a
        generation that failed: it looks finished, so nobody goes looking.

        The answer end. prompt + generated reaching the window means generation ran
        into the ceiling: the reply stopped mid-object, or the runner shifted the
        context to keep going and wrote the rest with the source material evicted.
        This is the branch that catches dense material, where the prompt fits, the
        estimate has nothing to complain about, and the answer is what gets cut. On
        a 17,778-char routed lesson prompt the difference is real: at 4 chars per
        token it is 4,444 tokens with room to spare, at 2.5 it is 7,111 and the
        reply has nowhere to go, and nothing before this point can tell them apart.

        The blind spot, on both branches, and the mirror of why the estimate is not
        trusted here. Ollama reports only the tokens it newly evaluated, so a prompt
        cache hit lowers prompt_eval_count: that is what would make comparing the
        count against the estimate misfire, and it equally means a cached prefix
        could in principle carry a genuinely truncated prompt in under the ceiling.
        Small in practice, since the first oversized call in a stage raises before
        any later call can reuse its prefix.
        """
        if input_tokens is None:
            return
        if input_tokens >= self.num_ctx:
            raise LLMCallError(
                f"Ollama evaluated {input_tokens} prompt tokens against a {self.num_ctx} "
                f"token context window, so the prompt was truncated to fit and "
                f"{self.model} did not see all of the material. Raise OLLAMA_NUM_CTX "
                f"(costs VRAM) or use shorter material.",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        if output_tokens is None:
            return
        if input_tokens + output_tokens >= self.num_ctx:
            raise LLMCallError(
                f"Ollama filled its {self.num_ctx} token context window while replying "
                f"({input_tokens} prompt + {output_tokens} generated), so the answer was "
                f"either cut off at the ceiling or continued with the source material "
                f"evicted from the window. Raise OLLAMA_NUM_CTX (costs VRAM) or use "
                f"shorter material.",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
