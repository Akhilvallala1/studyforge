"""Unit tests for the Ollama provider: context window, truncation, error wrapping.

Every call here goes through a stubbed httpx.post. Nothing in this file touches a
running Ollama, and the suite must keep passing on a machine that has never had one.
"""

import logging

import httpx
import pytest

from app.llm.base import LLMCallError, LLMResult
from app.llm.ollama_provider import DEFAULT_NUM_CTX, OllamaProvider

OLLAMA_LOGGER = "studyforge.llm.ollama"


def _response(status: int = 200, *, json=None, text: str | None = None) -> httpx.Response:
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    if text is not None:
        return httpx.Response(status, text=text, request=request)
    return httpx.Response(status, json=json, request=request)


def _chat_body(content: str = "hello", prompt_eval_count=10, eval_count=5) -> dict:
    return {
        "message": {"role": "assistant", "content": content},
        "prompt_eval_count": prompt_eval_count,
        "eval_count": eval_count,
        "done": True,
    }


def _stub_post(monkeypatch, response=None, raises: Exception | None = None) -> list[dict]:
    """Replace httpx.post, recording every request payload it is handed."""
    sent: list[dict] = []

    def fake_post(url, *, json, timeout):
        sent.append({"url": url, "json": json, "timeout": timeout})
        if raises is not None:
            raise raises
        return response

    monkeypatch.setattr(httpx, "post", fake_post)
    return sent


@pytest.fixture(autouse=True)
def _clean_ollama_env(monkeypatch):
    """backend/.env is loaded on import, so pin the settings these tests reason about."""
    monkeypatch.delenv("OLLAMA_NUM_CTX", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)


# --------------------------------------------------------------------------
# The context window is sent at all
# --------------------------------------------------------------------------


def test_num_ctx_is_sent_alongside_num_predict(monkeypatch):
    """The defect this file exists for: without num_ctx Ollama uses its own small
    default and silently drops whatever a course-sized prompt does not fit into it."""
    sent = _stub_post(monkeypatch, _response(json=_chat_body()))
    OllamaProvider().generate("system", "prompt", max_tokens=1234)

    options = sent[0]["json"]["options"]
    assert options["num_ctx"] == DEFAULT_NUM_CTX
    assert options["num_predict"] == 1234


def test_default_num_ctx_fits_a_routed_lesson_call():
    """The default is chosen against the pipeline's real prompts, not a round number.

    A lesson call sends up to two 8,000-char segments plus the system prompt, which
    is ~4,400 input tokens, and the lesson it writes back runs to a couple of
    thousand more. Anything at or below Ollama's own 4096 default cannot hold that.
    """
    from app.generation import LESSON_SYSTEM
    from app.ingest import MAX_CHUNK_CHARS
    from app.llm.ollama_provider import CHARS_PER_TOKEN

    biggest_lesson_prompt = len(LESSON_SYSTEM) + 2 * MAX_CHUNK_CHARS + 200
    estimated_input = biggest_lesson_prompt // CHARS_PER_TOKEN
    assert DEFAULT_NUM_CTX > 4096
    # Room left over for the reply, not just for the prompt.
    assert DEFAULT_NUM_CTX - estimated_input >= 2500


def test_num_ctx_reads_the_env_var(monkeypatch):
    monkeypatch.setenv("OLLAMA_NUM_CTX", "16384")
    sent = _stub_post(monkeypatch, _response(json=_chat_body()))
    provider = OllamaProvider()
    assert provider.num_ctx == 16384
    provider.generate("system", "prompt")
    assert sent[0]["json"]["options"]["num_ctx"] == 16384


def test_constructor_num_ctx_beats_the_env_var(monkeypatch):
    monkeypatch.setenv("OLLAMA_NUM_CTX", "16384")
    assert OllamaProvider(num_ctx=2048).num_ctx == 2048


@pytest.mark.parametrize("bad", ["nonsense", "0", "-1", "8k"])
def test_unusable_num_ctx_falls_back_loudly(monkeypatch, caplog, bad):
    monkeypatch.setenv("OLLAMA_NUM_CTX", bad)
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        provider = OllamaProvider()
    assert provider.num_ctx == DEFAULT_NUM_CTX
    assert "OLLAMA_NUM_CTX" in caplog.text


def test_blank_num_ctx_falls_back_quietly(monkeypatch, caplog):
    monkeypatch.setenv("OLLAMA_NUM_CTX", "   ")
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        assert OllamaProvider().num_ctx == DEFAULT_NUM_CTX
    assert caplog.text == ""


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------


def test_generate_returns_text_and_reported_tokens(monkeypatch):
    _stub_post(
        monkeypatch,
        _response(json=_chat_body("the lesson", prompt_eval_count=900, eval_count=300)),
    )
    result = OllamaProvider().generate("system", "prompt")
    assert isinstance(result, LLMResult)
    assert result.text == "the lesson"
    assert result.input_tokens == 900
    assert result.output_tokens == 300


def test_provider_identity(monkeypatch):
    provider = OllamaProvider()
    assert provider.name == "ollama"
    assert provider.is_paid is False
    assert provider.model == "llama3.1"
    assert provider.base_url == "http://localhost:11434"


# --------------------------------------------------------------------------
# Silent truncation, made loud
# --------------------------------------------------------------------------


@pytest.mark.parametrize("evaluated", [512, 513, 4096])
def test_prompt_filling_the_window_raises(monkeypatch, evaluated):
    """prompt_eval_count cannot exceed num_ctx, so reaching it means the prompt was
    cut down to fit. The model answered from a fragment and said nothing about it."""
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=evaluated)))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider(num_ctx=512).generate("sys", "short prompt")
    assert "truncated" in str(caught.value)
    assert "OLLAMA_NUM_CTX" in str(caught.value)


def test_truncation_error_carries_tokens_so_the_call_is_still_metered(monkeypatch):
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=512, eval_count=77)),
    )
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider(num_ctx=512).generate("sys", "short prompt")
    assert caught.value.input_tokens == 512
    assert caught.value.output_tokens == 77


def test_prompt_below_the_window_is_not_flagged(monkeypatch):
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=511)))
    result = OllamaProvider(num_ctx=512).generate("sys", "short prompt")
    assert result.text == "hello"


def test_missing_prompt_eval_count_cannot_be_judged(monkeypatch):
    """Nothing to compare against, so the call stands rather than failing on a guess."""
    body = _chat_body()
    del body["prompt_eval_count"]
    _stub_post(monkeypatch, _response(json=body))
    result = OllamaProvider(num_ctx=512).generate("sys", "short prompt")
    assert result.input_tokens is None


def test_oversized_prompt_warns_before_the_call(monkeypatch, caplog):
    """The estimate catches what the ceiling check cannot: a truncation that lands
    below num_ctx. It warns rather than raising, since it is only an estimate."""
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=5)))
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        result = OllamaProvider(num_ctx=10).generate("sys", "x" * 400)
    assert "OLLAMA_NUM_CTX" in caplog.text
    assert "fragment" in caplog.text
    # A warning, not a failure.
    assert result.text == "hello"


def test_prompt_that_fits_does_not_warn(monkeypatch, caplog):
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=5)))
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        OllamaProvider(num_ctx=8192).generate("sys", "x" * 400)
    assert caplog.text == ""


# --------------------------------------------------------------------------
# Failures a local setup really hits, all wrapped as LLMCallError
# --------------------------------------------------------------------------


def test_ollama_not_running_is_wrapped(monkeypatch):
    _stub_post(monkeypatch, raises=httpx.ConnectError("[WinError 10061] refused"))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    message = str(caught.value)
    assert "http://localhost:11434" in message
    assert "running" in message


def test_timeout_is_wrapped(monkeypatch):
    _stub_post(monkeypatch, raises=httpx.ReadTimeout("timed out"))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    assert "did not answer" in str(caught.value)


def test_model_not_pulled_names_the_pull_command(monkeypatch):
    _stub_post(monkeypatch, _response(404, json={"error": 'model "llama3.1" not found'}))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    assert "ollama pull llama3.1" in str(caught.value)


def test_server_error_is_wrapped_with_ollamas_own_message(monkeypatch):
    _stub_post(monkeypatch, _response(500, json={"error": "out of memory"}))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    assert "500" in str(caught.value)
    assert "out of memory" in str(caught.value)


def test_error_status_without_a_json_body_is_still_wrapped(monkeypatch):
    _stub_post(monkeypatch, _response(502, text="<html>bad gateway</html>"))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    assert "502" in str(caught.value)


def test_body_that_is_not_json_is_wrapped(monkeypatch):
    _stub_post(monkeypatch, _response(200, text="not json at all"))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    assert "not JSON" in str(caught.value)


def test_body_that_is_not_an_object_is_wrapped(monkeypatch):
    _stub_post(monkeypatch, _response(200, json=["nope"]))
    with pytest.raises(LLMCallError):
        OllamaProvider().generate("sys", "prompt")


def test_body_without_message_content_is_wrapped_and_keeps_tokens(monkeypatch):
    _stub_post(monkeypatch, _response(200, json={"prompt_eval_count": 40, "eval_count": 0}))
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider().generate("sys", "prompt")
    assert caught.value.input_tokens == 40
    assert caught.value.output_tokens == 0


def test_message_content_of_the_wrong_type_is_wrapped(monkeypatch):
    _stub_post(monkeypatch, _response(200, json={"message": {"content": None}}))
    with pytest.raises(LLMCallError):
        OllamaProvider().generate("sys", "prompt")


def test_no_raw_httpx_error_escapes_the_provider(monkeypatch):
    """The contract, stated once over every transport failure mode a local box hits.

    Callers reason about LLMCallError. A raw httpx exception skipped MeteredLLM's
    except clause entirely, so a failed local call left no llm_calls row at all.
    """
    for failure in (
        httpx.ConnectError("refused"),
        httpx.ConnectTimeout("connect timed out"),
        httpx.ReadTimeout("read timed out"),
        httpx.RemoteProtocolError("server disconnected"),
        httpx.InvalidURL("not a url"),
    ):
        _stub_post(monkeypatch, raises=failure)
        with pytest.raises(LLMCallError):
            OllamaProvider().generate("sys", "prompt")


def test_failed_ollama_call_is_metered(client, monkeypatch):
    """The point of the wrapping: MeteredLLM only records what raises LLMCallError.

    Takes the client fixture so init_db() has run and llm_calls exists.
    """
    from app import models
    from app.db import SessionLocal
    from app.metering import MeteredLLM

    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=512, eval_count=8)))
    meter = MeteredLLM(OllamaProvider(num_ctx=512), run_id="ollama-truncation-run")
    with pytest.raises(LLMCallError):
        meter.generate("outline", "sys", "short prompt")

    session = SessionLocal()
    try:
        row = (
            session.query(models.LlmCall)
            .filter(models.LlmCall.run_id == "ollama-truncation-run")
            .one()
        )
        assert row.provider == "ollama"
        assert row.input_tokens == 512
        assert row.output_tokens == 8
        assert row.estimated_cost_usd == 0.0
    finally:
        session.close()
