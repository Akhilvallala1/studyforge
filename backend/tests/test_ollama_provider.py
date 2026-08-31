"""Unit tests for the Ollama provider: context window, truncation, error wrapping.

Every call here goes through a stubbed httpx.post. Nothing in this file touches a
running Ollama, and the suite must keep passing on a machine that has never had one.
"""

import logging

import httpx
import pytest

from app.llm.base import LLMCallError, LLMResult
from app.llm.ollama_provider import (
    CHARS_PER_TOKEN,
    DEFAULT_NUM_CTX,
    OUTPUT_RESERVE_TOKENS,
    OllamaProvider,
)

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


def _routed_lesson_prompt_chars() -> int:
    """The biggest prompt the common case sends: system plus two whole segments."""
    from app.generation import LESSON_SYSTEM
    from app.ingest import MAX_CHUNK_CHARS

    return len(LESSON_SYSTEM) + 2 * MAX_CHUNK_CHARS + 200


def test_default_num_ctx_fits_a_routed_lesson_call():
    """The default is chosen against the pipeline's real prompts, not a round number.

    A lesson call sends up to two 8,000-char segments plus the system prompt, which
    is ~4,400 input tokens, and the lesson it writes back runs to a couple of
    thousand more. Anything at or below Ollama's own 4096 default cannot hold that.

    Both sides of this are ESTIMATED tokens, so it guards the constants growing
    (raising MAX_CHUNK_CHARS past ~10,500 turns it red) and not the estimate being
    wrong. The checks that catch a wrong estimate are the reported-count ones below.
    """
    estimated_input = _routed_lesson_prompt_chars() // CHARS_PER_TOKEN
    assert DEFAULT_NUM_CTX > 4096
    # Room left over for the reply, not just for the prompt.
    assert DEFAULT_NUM_CTX - estimated_input >= OUTPUT_RESERVE_TOKENS


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


def test_prompt_one_token_below_the_window_is_not_flagged(monkeypatch):
    """The boundary, isolated: eval_count 0 so only the prompt end is under test."""
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=511, eval_count=0)),
    )
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
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=5, eval_count=0)),
    )
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


def test_prompt_that_fits_but_crowds_the_reply_still_warns(monkeypatch, caplog):
    """The reserve's whole point.

    24,000 chars estimates to 6,000 tokens, which fits an 8,192 window with room to
    spare by the old rule and leaves 2,192 for a lesson that needs up to 2,500.
    Judged against the window alone this read as comfortable.
    """
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=5)))
    provider = OllamaProvider(num_ctx=8192)
    estimated = (len("sys") + 24_000) // CHARS_PER_TOKEN
    assert estimated < provider.num_ctx, "the prompt does fit the window"

    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        provider.generate("sys", "x" * 24_000)
    assert "meant for the reply" in caplog.text


def test_prompt_budget_never_goes_negative_on_a_tiny_window(monkeypatch, caplog):
    """A window smaller than the reserve must not make every call warn."""
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=5)))
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        OllamaProvider(num_ctx=1024).generate("sys", "x" * 400)
    assert caplog.text == ""


# --------------------------------------------------------------------------
# num_predict: never ask for more than the window can hold
# --------------------------------------------------------------------------


def test_num_predict_is_capped_to_what_the_window_has_left(monkeypatch):
    """The pipeline's 64000 default is eight times the window.

    Asking for it against a pinned num_ctx invites the runner to shift the context
    mid-reply, evicting the source material while the model keeps writing, with
    prompt_eval_count none the wiser.
    """
    sent = _stub_post(monkeypatch, _response(json=_chat_body()))
    provider = OllamaProvider(num_ctx=8192)
    provider.generate("sys", "x" * 4000, max_tokens=64000)

    expected = 8192 - (len("sys") + 4000) // CHARS_PER_TOKEN
    assert sent[0]["json"]["options"]["num_predict"] == expected
    assert expected < 64000


def test_num_predict_never_exceeds_what_the_caller_asked_for(monkeypatch):
    """Remediation passes 4000 on purpose; the cap must not hand it more."""
    sent = _stub_post(monkeypatch, _response(json=_chat_body()))
    OllamaProvider(num_ctx=8192).generate("sys", "short", max_tokens=4000)
    assert sent[0]["json"]["options"]["num_predict"] == 4000


def test_num_predict_stays_positive_when_the_prompt_fills_the_window(monkeypatch):
    """A doomed call still has to be a valid request; the counts fail it afterwards."""
    sent = _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=1)))
    OllamaProvider(num_ctx=100).generate("sys", "x" * 40_000)
    assert sent[0]["json"]["options"]["num_predict"] >= 1


# --------------------------------------------------------------------------
# The answer end of the window
# --------------------------------------------------------------------------


def test_reply_that_runs_into_the_ceiling_raises(monkeypatch):
    """Dense material: the prompt fits, so nothing before the call complains, and
    the reply is what runs out of room.

    A 17,778-char routed lesson prompt is 4,444 tokens at 4 chars per token and
    7,111 at 2.5, which is ordinary for markdown with code fences. At 2.5 the prompt
    still fits an 8,192 window, prompt_eval_count lands well under the ceiling, and
    the lesson gets cut off mid-object instead.
    """
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=7111, eval_count=1081)),
    )
    with pytest.raises(LLMCallError) as caught:
        OllamaProvider(num_ctx=8192).generate("sys", "short prompt")
    assert "while replying" in str(caught.value)
    assert caught.value.input_tokens == 7111
    assert caught.value.output_tokens == 1081


def test_the_case_that_passed_silently_before(monkeypatch):
    """Verified live against a real Ollama: prompt_eval_count 8000 against a 8192
    window produced no error and no warning and handed back truncated text.

    8000 is under the ceiling, so the prompt-end check cannot see it, and the
    prompt is far too short for the character estimate to complain. Only counting
    the reply as well catches it.
    """
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=8000, eval_count=192)),
    )
    with pytest.raises(LLMCallError):
        OllamaProvider(num_ctx=8192).generate("sys", "short prompt")


def test_reply_with_a_token_to_spare_does_not_raise(monkeypatch):
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=7111, eval_count=1080)),
    )
    result = OllamaProvider(num_ctx=8192).generate("sys", "short prompt")
    assert result.text == "hello"


def test_missing_eval_count_cannot_judge_the_reply(monkeypatch):
    body = _chat_body(prompt_eval_count=8000)
    del body["eval_count"]
    _stub_post(monkeypatch, _response(json=body))
    result = OllamaProvider(num_ctx=8192).generate("sys", "short prompt")
    assert result.output_tokens is None


# --------------------------------------------------------------------------
# The reported counts are untrusted input like the rest of the body
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bogus", ["512", [512], {"n": 512}, 511.5, True, -1])
def test_a_count_that_is_not_a_count_becomes_unknown(monkeypatch, caplog, bogus):
    """These used to reach `input_tokens < self.num_ctx` and leave a raw TypeError,
    which MeteredLLM does not catch, so the failed call wrote no row at all.

    Unknown rather than fatal: it is the same state as Ollama not reporting the
    count, and the reply text may be perfectly good. The warning is what makes it
    findable, since an unknown count means the window checks cannot run.
    """
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count=bogus)))
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        result = OllamaProvider(num_ctx=512).generate("sys", "short prompt")
    assert result.input_tokens is None
    assert result.text == "hello"
    assert "prompt_eval_count" in caplog.text


def test_a_string_count_at_the_ceiling_does_not_raise_typeerror(monkeypatch):
    """The exact reproduction: "512" against num_ctx 512 hit the comparison."""
    _stub_post(monkeypatch, _response(json=_chat_body(prompt_eval_count="512")))
    result = OllamaProvider(num_ctx=512).generate("sys", "short prompt")
    assert result.input_tokens is None


def test_a_bogus_eval_count_cannot_break_the_reply_check(monkeypatch, caplog):
    """The sum check adds the two counts, so eval_count needs the same guard."""
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=100, eval_count="200")),
    )
    with caplog.at_level(logging.WARNING, logger=OLLAMA_LOGGER):
        result = OllamaProvider(num_ctx=8192).generate("sys", "short prompt")
    assert result.input_tokens == 100
    assert result.output_tokens is None
    assert "eval_count" in caplog.text


def test_a_float_count_never_reaches_the_integer_column(monkeypatch):
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=511.5, eval_count=2.5)),
    )
    result = OllamaProvider(num_ctx=8192).generate("sys", "short prompt")
    assert result.input_tokens is None
    assert result.output_tokens is None


def test_zero_is_a_real_count_and_survives(monkeypatch):
    """0 is falsy but perfectly valid: a call that generated nothing."""
    _stub_post(
        monkeypatch,
        _response(json=_chat_body(prompt_eval_count=0, eval_count=0)),
    )
    result = OllamaProvider(num_ctx=8192).generate("sys", "short prompt")
    assert result.input_tokens == 0
    assert result.output_tokens == 0


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
