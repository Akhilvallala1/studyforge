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
| Segment fallback | How often the outline routed a lesson to nothing usable, so the lesson took the whole corpus instead of its own segments. |

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
python -m evals.run_eval --label my-run     # the real thing
```

Note that `generate_course` re-sends the entire document with every lesson call,
so cost scales with lessons x whole document. `--dry-run` projects this before you
commit to it; check the projection against your cap.

Outputs land in `evals/output/`:

- `course-<label>-<source>.md`: the full generated course, every lesson and every
  quiz answer, for a human to read and judge.
- `report-<label>.md`: the metrics, with every grounding failure quoted.
- `results-<label>.json`: machine-readable bundle, the input to `--compare`.
- `usage-<label>.json`: the app's own `GET /usage` totals.

Rerunning a label replaces all four: a label is the run's name. Naming one is how
you say that is what you meant, so `--label` has no default you can fall into: with
no `--label`, a run that would overwrite existing files refuses to start and tells
you what it was about to destroy. Pass `--force` if you meant it. `--dry-run` never
writes anything, so it is never refused.

The three older `course-<source>.md` files, with no label in the name, predate
that. Course files used to be named by source alone while everything else carried
the label, so every run overwrote the previous run's course for that source and
those three are whichever run happened to go last. They were last written by the
prompt trials (commit 8d491cc), and which variant produced them is not recoverable.
Read them as samples of the format, not as any particular run's output.

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
- `multi-darwin-pep8`: the multi-source corpus. Darwin's full excerpt plus the first
  3,000 characters of PEP 8, as two separate documents.

Add one by extending `available_sources()` in `run_eval.py`. A source whose corpus is
several documents also needs an entry in `MULTI_SOURCE_KEYS` beside it, which is what
carries the document boundaries into generation.

## The multi-source arm

`multi-darwin-pep8` exists to measure one configuration: several documents, with
segment routing switched on. Two things about it are chosen rather than incidental.

**The documents are unrelated on purpose.** The failure the source-aware outline prompt
exists to prevent is a model reading two documents as one continuous work, and two
excerpts of the same book cannot exhibit it, because a lesson bridging them would be
correct. Darwin and a Python style guide share no vocabulary, structure or subject, so a
lesson that reads across the seam is visibly wrong.

**The sizes are chosen for the chunk arithmetic.** Routing switches on at
`SEGMENT_ROUTING_MIN_CHUNKS` (3) and chunks hold up to 8,000 characters, so two short
documents make two chunks and stay *unrouted*. Darwin's full text is 2 chunks and the
PEP 8 excerpt is 1, giving exactly 3: the smallest corpus that is both genuinely
multi-source and routed.

Note that a multi-source corpus is chunked **per document**, not over the concatenation,
so a chunk always has one owner to tag it with. This gives a different count from
`chunk_text` over the joined text, and the printed count is the one generation uses.

### Running the A/B

`--no-source-tags` withholds the document tags, which reproduces the pre-feature prompt
exactly rather than approximately: `label_segments` and `outline_system` both branch on
whether the corpus names more than one document, so the untagged arm is byte for byte
what shipped before multi-source existed. It is the BEFORE arm.

```bash
python -m evals.run_eval --label multi-tagged-1   --source multi-darwin-pep8
python -m evals.run_eval --label multi-untagged-1 --source multi-darwin-pep8 --no-source-tags
python -m evals.trials evals/output --group multi-tagged --group multi-untagged
```

Run each arm several times. `evals/trials.py` refuses to name a winner whose lead is
inside the spread between two runs of the same prompt, and one run of each arm cannot
tell you what that spread is.

## Tests

`tests/test_evals.py` covers the matcher and every metric with synthetic courses,
and asserts the preflight guard refuses an unsafe run. It never calls a provider,
so it runs in the normal `python -m pytest tests` suite.
