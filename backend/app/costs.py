"""USD cost estimation for LLM calls, based on per-model token pricing."""

import os

# USD per million tokens: model_id -> (input_price, output_price)
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5": (10.00, 50.00),
}


def _lookup_pricing(model: str) -> tuple[float, float, bool]:
    """Return (input_price, output_price, approximate) for a model id.

    Tries an exact match first, then the longest PRICING key that is a prefix of
    `model` (handles date-suffixed model ids). Falls back to configurable env
    defaults, marked approximate, when nothing matches.
    """
    if model in PRICING:
        input_price, output_price = PRICING[model]
        return input_price, output_price, False

    prefix_matches = [key for key in PRICING if model.startswith(key)]
    if prefix_matches:
        best = max(prefix_matches, key=len)
        input_price, output_price = PRICING[best]
        return input_price, output_price, False

    default_in = float(os.environ.get("STUDYFORGE_PRICE_DEFAULT_IN_USD", "5.00"))
    default_out = float(os.environ.get("STUDYFORGE_PRICE_DEFAULT_OUT_USD", "25.00"))
    return default_in, default_out, True


def is_priced(model: str) -> bool:
    """Whether PRICING knows this model, rather than the env fallback standing in.

    Exists so /usage can say which half of a call's cost was the estimate: an unknown
    model id means the PRICE was guessed, which is a different sentence to the learner
    than a missing token count, and the two share one flag on the row.
    """
    return not _lookup_pricing(model)[2]


def estimate_cost(model: str, in_toks: int | None, out_toks: int | None) -> tuple[float, bool]:
    """Estimate the USD cost of a call. Returns (cost_usd, approximate).

    approximate is True when the model's pricing was not known exactly (fell back
    to the env-configured default) or when token counts had to be estimated
    (None counts are treated as 0 for the cost math, but still mark the result
    approximate).
    """
    input_price, output_price, price_approximate = _lookup_pricing(model)
    token_approximate = in_toks is None or out_toks is None
    input_tokens = in_toks or 0
    output_tokens = out_toks or 0
    cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
    return cost, price_approximate or token_approximate
