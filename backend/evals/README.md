# Generation eval

Measures whether a generated course is actually any good, against the real
provider. Everything it reports is mechanically checkable from the source text and
the generated JSON: no model-as-judge, no scores that cannot be re-derived by hand.

## What it measures

| Metric | Question it answers |
|---|---|
| Grounding | Can each quiz answer be found in, or fairly inferred from, the source document? |
| Answerability | Can each answer be found in its *own lesson's* content, as `LESSON_SYSTEM` promises? |
| Concept coverage | Do extracted concepts span the document, or cluster in the opening chunks? |
| Parse reliability | Did each response parse as strict JSON first try, or need fence-stripping or prose-trimming? |
| Structure | Lesson/quiz/option counts, empty fields, duplicate questions and options, MCQ answers missing from their own options. |
| Cost and latency | Per stage and per course, from the app's own metering. |

Grounding and answerability score an answer by **best window recall**: the largest
fraction of the answer's content words that appear inside a single local window of
the reference text. Scattered words across a long document are coincidence, not
support, so global vocabulary overlap is reported alongside it but never used as
the headline number. Tiers are `exact` (verbatim), `strong` (>= 0.80), `partial`
(>= 0.50), `unsupported`. Trivial answers ("True", "All of the above") are counted
and excluded from the denominator instead of inflating it.

## Running it

The runner refuses to start against the developer database, or with a paid
provider and no hard spend cap. That is deliberate.

```bash
cd backend
export STUDYFORGE_DB=/tmp/eval.sqlite3      # never the real studyforge.sqlite3
export STUDYFORGE_COST_LIMIT_USD=3.00       # hard cap, enforced in app/metering.py
export STUDYFORGE_COST_ALERT_USD=1.00

python -m evals.run_eval --dry-run          # ingest + cost projection, no model calls
python -m evals.run_eval --label baseline   # the real thing
```

Note that `generate_course` re-sends the entire document with every lesson call,
so cost scales with lessons x whole document. `--dry-run` projects this before you
commit to it; check the projection against your cap.

Outputs land in `evals/output/`:

- `course-<source>.md`: the full generated course, every lesson and every quiz
  answer, for a human to read and judge.
- `report-<label>.md`: the metrics, with every grounding failure quoted.
- `results-<label>.json`: machine-readable bundle, the input to `--compare`.
- `usage-<label>.json`: the app's own `GET /usage` totals.

## Comparing before and after a prompt change

Each bundle records a fingerprint of `OUTLINE_SYSTEM` and `LESSON_SYSTEM`, so a
comparison can tell you the prompts changed and not just the scores.

```bash
python -m evals.run_eval --label after --source pep8-url
python -m evals.run_eval --compare output/results-baseline.json output/results-after.json --label promptv2
```

## Sources

- `pep8-url`: PEP 8, fetched live through `app.ingest.extract_url`, so the eval
  sees the same crude tag-stripped text the app feeds the model.
- `prose-text`: a public-domain excerpt of Darwin's *Origin of Species* ch. IV,
  in `evals/data/`, as a shorter-material contrast.

Add one by extending `available_sources()` in `run_eval.py`.

## Tests

`tests/test_evals.py` covers the matcher and every metric with synthetic courses,
and asserts the preflight guard refuses an unsafe run. It never calls a provider,
so it runs in the normal `python -m pytest tests` suite.
