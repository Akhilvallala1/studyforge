"""One error shape, across every route, whatever kind of bad request produced it.

THE CLAIM THIS FILE EXISTS FOR, stated as a client would and SCOPED TO 422s: every 422
from this API carries `detail` as an object with `error` and `message`, never as a list.
No exceptions, and the sentence is worth having with no exceptions in it.

It had one for a while. main.py's NoMaterial refusal on POST /review/cards/{id}/remediation
raised HTTPException(422, NO_MATERIAL_MESSAGE) with a bare string, which made an earlier
version of this paragraph false. It was found by GREPPING every HTTPException in
backend/app rather than by probing from the outside, one round after an external sweep had
been the thing that missed it: a sweep can only report what it happened to ask for. It now
answers `no_material`, the same code the tutor already uses for the same condition, so the
claim above needs no qualifier.

THE 422 SHAPE HAS ONE DEFINITION, main.py's _unprocessable, which the tutor and planning
factories delegate to. That is what makes this claim maintainable rather than merely true
today: there is one place to change and one place to get wrong.

It is NOT true that a client now writes one parsing branch. A 404 still carries `detail`
as a bare string, "Course not found", and test_a_404_is_not_reshaped_either pins that. So
a client writes two: string for 404, object for 422. What went away is the THIRD, the
array, which was the one it could not predict, because which of object or array a 422 gave
back depended on whether the caller's bug was a wrong value or a wrong type. Claiming one
branch here would overstate a compatibility promise, which is the kind of sentence that
gets believed and then acted on.

That was not true until app/main.py grew its RequestValidationError handler. A wrong VALUE
reached a hand-rolled check and came back in that shape, while a wrong TYPE was rejected by
pydantic first and came back as a list of validation objects, and a MISSING required field
did the same. Which shape a client got depended on which kind of bug it had, which is not
something a client can predict, so it had to handle both.

WHY THIS IS ITS OWN FILE RATHER THAN MORE TESTS IN test_tutor_endpoints.py. The claim is
about the API and not about the tutor. Asserted only on one route it would be satisfied by
a per-route fix, which is the instrument that was rejected: widening annotations field by
field never retires the second parsing path, because it only takes one route nobody
thought about for the array to still be reachable. So every case below is checked on THREE
bodies owned by two different features, and the parametrization is the assertion.

THE OTHER HALF IS THAT NOTHING ELSE MOVED. A handler that reshapes errors app-wide is a
blunt instrument, and the real risk is not that it misses a case but that it catches one it
should not have. Hand-rolled refusals raise HTTPException and never reach it; the tests at
the bottom pin the exact bodies of the ones that already worked, so a future widening of
this handler that started swallowing them fails here.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app import fsrs, main, models, review
from app.db import SessionLocal


@pytest.fixture
def course_id() -> int:
    """A course to hang the deadline route off. Its contents do not matter here."""
    session = SessionLocal()
    try:
        course = models.Course(title="Error shape probe", description="")
        session.add(course)
        session.commit()
        return course.id
    finally:
        session.close()


def _detail(response):
    body = response.json()
    assert isinstance(body, dict), f"the response body is not an object: {body!r}"
    return body["detail"]


def _assert_one_shape(response, expect_field: str | None = None):
    """The whole contract, in one place, so every case below asserts the same thing."""
    assert response.status_code == 422, response.text
    detail = _detail(response)
    assert not isinstance(detail, list), (
        "detail came back as a list of validation objects, so this API has two error "
        "shapes again and every client needs two parsing paths"
    )
    assert set(detail) == {"error", "message"}
    assert isinstance(detail["error"], str) and detail["error"]
    assert isinstance(detail["message"], str) and detail["message"]
    if expect_field is not None:
        assert expect_field in detail["message"]
    return detail


# One row per request body: how to reach it, a body with a WRONG TYPE and the field that
# names, and a body MISSING a required field and the field THAT names. The two field names
# differ on the tutor row, because its wrong-type case is about concept_key and its missing
# case is about message, and a single column would have quietly asserted the wrong one.
#
# Three bodies from two features, which is the assertion rather than the setup. A per-route
# fix satisfies any single row and fails the set.
_BODIES = [
    ("tutor", "post", "/tutor/messages",
     {"concept_key": 7, "message": "m"}, "concept_key",
     {"concept_key": "k"}, "message"),
    ("deadline", "put", "/courses/{course_id}/deadline",
     {"deadline": 7}, "deadline",
     {}, "deadline"),
    ("day off", "post", "/plan/days-off",
     {"day": 7}, "day",
     {}, "day"),
]
_BODY_ARGS = ("label", "method", "url", "wrong_type", "wrong_field", "missing", "missing_field")
_BODY_IDS = [row[0] for row in _BODIES]


@pytest.mark.parametrize(_BODY_ARGS, _BODIES, ids=_BODY_IDS)
def test_a_wrong_type_answers_in_the_one_shape(
    client, course_id, label, method, url, wrong_type, wrong_field, missing, missing_field
):
    """The case the whole change started from, on three bodies rather than one."""
    response = getattr(client, method)(url.format(course_id=course_id), json=wrong_type)

    detail = _assert_one_shape(response, expect_field=wrong_field)
    assert detail["error"] == main.INVALID_REQUEST_ERROR


@pytest.mark.parametrize(_BODY_ARGS, _BODIES, ids=_BODY_IDS)
def test_a_missing_required_field_answers_in_the_one_shape(
    client, course_id, label, method, url, wrong_type, wrong_field, missing, missing_field
):
    """The case NO amount of widening annotations could have reached.

    A field can be given a wider type and validated by hand. A field that is not there at
    all is rejected by pydantic before any hand-rolled code runs, and the only way to hand
    it back in the shared shape is to catch the exception. This is the case that decided
    the instrument.
    """
    response = getattr(client, method)(url.format(course_id=course_id), json=missing)

    detail = _assert_one_shape(response, expect_field=missing_field)
    assert detail["error"] == main.INVALID_REQUEST_ERROR
    assert "required" in detail["message"].lower()


def test_a_malformed_json_body_answers_in_the_one_shape(client):
    """Not a field problem at all, and it lands in the same place."""
    response = client.post(
        "/tutor/messages",
        content=b"{not json at all",
        headers={"Content-Type": "application/json"},
    )

    detail = _assert_one_shape(response)
    assert detail["error"] == main.INVALID_REQUEST_ERROR


def test_an_unparseable_path_parameter_answers_in_the_one_shape(client):
    """A path parameter, so this is not specific to request BODIES either."""
    detail = _assert_one_shape(client.get("/courses/not-an-integer"), expect_field="course_id")

    assert detail["error"] == main.INVALID_REQUEST_ERROR
    assert detail["message"].startswith(main.INVALID_REQUEST_MESSAGE)
    assert "path.course_id" in detail["message"], "the message says WHERE, not just which name"


def test_an_unparseable_query_parameter_answers_in_the_one_shape(client):
    """And a query parameter, which is the third place a request can be malformed.

    Recorded because the scope of this handler is wider than the change that prompted it.
    It began as a fix for one field in one request body; it covers every value FastAPI
    parses, wherever it came from, because all of them arrive as the same exception. Body,
    path and query are now all pinned, so nobody has to guess how far it reaches.
    """
    detail = _assert_one_shape(client.get("/review/queue?limit=not-an-int"), expect_field="limit")

    assert detail["error"] == main.INVALID_REQUEST_ERROR
    assert "query.limit" in detail["message"]


def test_the_message_never_echoes_what_was_sent(client):
    """`input` is deliberately not in the message, and this is not a style preference.

    Pydantic's error objects carry the offending value. Reflecting a caller's own input
    back into a response body is how a reflection vector gets built by accident, and it is
    unbounded: the rejected value can be a megabyte of JSON, or a script tag that some
    client pastes into a page. The message is built from `loc` and `msg` only, both of
    which this codebase or pydantic wrote. This also REMOVES an existing surface rather
    than declining to add one: the array shape this handler replaced carried `input` on
    every error object, and on a missing field that was the caller's entire submitted body.

    THE TRAP THIS TEST FELL INTO, WRITTEN DOWN SO NOBODY REBUILDS IT. The hostile payload
    HAS TO SIT IN THE FIELD THAT FAILS. It first sat in `concept_key` while `message` was
    the wrong type, and `concept_key` is a `str`, so a 5000-character string VALIDATED
    SUCCESSFULLY and never appeared in any error object at all. The only failing field was
    `message`, whose input was the integer 7. Measured against a mutant that appends
    "(got {input!r})" to every problem: the message came back at 78 characters reading
    "body.message: Input should be a valid string (got 7)", every assertion below held, and
    ALL THIRTEEN TESTS IN THIS FILE PASSED against code that reflects input. The payload is
    now a LIST containing the hostile string, so the field it poisons is the field that
    fails: 74 characters clean, 5110 characters with the script tag present against the
    same mutant.

    The general form is worth keeping in mind for any test like this: a hostile payload in
    a field that validates is a hostile payload the code under test never touches.
    """
    hostile = "<script>alert(1)</script>" + "x" * 5000

    # A list where a string is required, so THIS is the field pydantic rejects and this is
    # the value that reaches the error object.
    response = client.post("/tutor/messages", json={"concept_key": [hostile], "message": "m"})

    detail = _assert_one_shape(response, expect_field="concept_key")
    assert hostile not in detail["message"]
    assert "<script>" not in detail["message"]
    assert len(detail["message"]) < 500, "the message grows with the input, so it echoes it"


def test_several_problems_in_one_body_are_all_named(client):
    """Two wrong fields, both named, over HTTP. What this route can actually produce.

    It used to claim to test the truncation branch and did not: the widest body on this API
    yields two validation errors, MAX_REPORTED_PROBLEMS is three, so nothing was ever
    truncated and the "and N more" suffix was never reached. The assertion it made,
    counting colons, passed on the two-problem case and would have passed on one.
    Truncation is tested directly below, where it can be reached.
    """
    response = client.post("/plan/days-off", json={"day": 7, "note": 7})

    detail = _assert_one_shape(response)
    assert "body.day" in detail["message"]
    assert "body.note" in detail["message"]
    assert "more" not in detail["message"], "two problems is under the cap, so nothing is cut"


@pytest.mark.parametrize(
    ("count", "expect_suffix"),
    [(1, False), (main.MAX_REPORTED_PROBLEMS, False), (main.MAX_REPORTED_PROBLEMS + 2, True)],
    ids=["one", "at the cap", "over the cap"],
)
def test_the_message_truncates_past_the_cap(count, expect_suffix):
    """_validation_message CALLED DIRECTLY, and the direct call is the point rather than a
    shortcut.

    NO ROUTE ON THIS API CAN PRODUCE MORE THAN THREE VALIDATION ERRORS. The widest request
    body has two fields, so the truncation branch is unreachable over HTTP today and a test
    that went through a client could only ever pretend to exercise it. The branch is still
    real: it is what stops a future body with fifteen fields returning a paragraph, and the
    caller of that future body would meet it on their first bad request.

    So this is tested where it lives. A synthetic error list is not a weaker test here, it
    is the only honest one, and if a wider body ever ships, the HTTP test above is where
    the over-the-cap case moves.
    """
    errors = [
        {"loc": ("body", f"field{index}"), "msg": "Field required"} for index in range(count)
    ]

    message = main._validation_message(errors)

    named = min(count, main.MAX_REPORTED_PROBLEMS)
    for index in range(named):
        assert f"body.field{index}" in message
    for index in range(named, count):
        assert f"body.field{index}" not in message, "a problem past the cap was still named"
    assert (f"and {count - named} more" in message) is expect_suffix


def test_the_message_survives_error_objects_that_are_missing_pieces():
    """Both fallbacks, which no route reaches either and which exist for the same reason.

    An empty `loc` becomes "body" rather than an empty string, and a missing `msg` gets a
    sentence rather than None. Pydantic always supplies both today; these are here because
    a message builder that raises inside an error handler turns a 422 into a 500, which is
    the one outcome worse than an ugly message.
    """
    assert main._validation_message([]) == main.INVALID_REQUEST_MESSAGE
    assert "body: is not valid" in main._validation_message([{"loc": (), "msg": ""}])
    assert "body: is not valid" in main._validation_message([{}])


# --------------------------------------------------------------------------
# The other half: everything that already worked is untouched
# --------------------------------------------------------------------------


def test_hand_rolled_refusals_are_unchanged_by_the_handler(client, course_id):
    """The risk this instrument carries, pinned by exact body rather than by shape.

    A handler that reshapes errors app-wide could just as easily catch a refusal that was
    already correct. These are not reachable through RequestValidationError, because every
    one of them raises HTTPException, but "it cannot happen" is the claim, and this is the
    test of it. Exact dicts, so a message edit or a code rename fails here too, which is
    right: these are the sentences clients and learners actually read.
    """
    empty = client.post("/tutor/messages", json={"concept_key": "k", "message": "   "})
    assert empty.status_code == 422
    assert _detail(empty) == {
        "error": "message_empty",
        "message": main.MESSAGE_EMPTY_MESSAGE,
    }

    bad_mode = client.post(
        "/tutor/messages", json={"concept_key": "k", "message": "m", "mode": "socratic"}
    )
    assert bad_mode.status_code == 422
    assert _detail(bad_mode) == {
        "error": "invalid_mode",
        "message": main.INVALID_MODE_MESSAGE,
    }

    bad_deadline = client.put(f"/courses/{course_id}/deadline", json={"deadline": "not-a-date"})
    assert bad_deadline.status_code == 422
    assert _detail(bad_deadline)["error"] == "deadline_malformed"

    bad_day = client.post("/plan/days-off", json={"day": "not-a-date"})
    assert bad_day.status_code == 422
    assert _detail(bad_day)["error"] == "day_malformed"


def test_a_wrong_mode_keeps_its_own_message_rather_than_the_generic_one(client):
    """The one field deliberately NOT handed to the generic handler, both ways round.

    A wrong-type mode and a wrong-value mode both reach the tutor's own check, so both get
    the sentence that names the legal values and says omitting the field is allowed. The
    generic handler could only say a string was expected. This is the field a learner's own
    button puts in flight, so it is the one worth a message written for it, and letting the
    handler swallow it would be a regression dressed as consistency.
    """
    for mode in (7, None, [], "socratic"):
        response = client.post(
            "/tutor/messages", json={"concept_key": "k", "message": "m", "mode": mode}
        )
        assert response.status_code == 422
        assert _detail(response) == {
            "error": "invalid_mode",
            "message": main.INVALID_MODE_MESSAGE,
        }, f"mode={mode!r} fell through to the generic handler"


@pytest.fixture
def card_id() -> int:
    """A real review card, RATED, FLAGGED, and with no course teaching its concept.

    Every one of those four is load bearing for some test below, and three of them are
    guards that sit IN FRONT of the code under test. A fixture that clears only the first
    produces tests that pass while asserting nothing, which is the failure this file has
    already had once.

    REAL, because the rating check sits behind the card lookup: rating an id that does not
    exist answers 404 and never reaches the rating branch, so a made-up id asserts nothing.

    FLAGGED, because POST /remediation refuses an unflagged concept with 409 not_flagged
    before it ever looks for material. Two lapses inside review.ATTENTION_WINDOW is what
    needs_attention triggers on, and that trigger is the only way in. Found by asserting
    the status: the first version of this fixture rated GOOD once and the remediation test
    came back 409, not the 422 it was written for.

    NO COURSE, which is what makes the material actually missing. A flagged concept that
    something teaches gets re-taught rather than refused.

    RATED, which the ratings above give for free, and which matters outside this file: the
    card outlives the test in the suite's shared database, and
    test_planning.py::test_no_planning_endpoint_touches_the_scheduler snapshots every
    review card and refuses to run against one with a NULL due date. Its docstring asks
    that such a card be rated at the source rather than that it narrow itself, so that is
    what this does. Found by the full suite, not by running this file alone.

    The stale-note delete is copied from test_usage_attribution._seed_struggling_concept
    and is test hygiene rather than a guard against anything the app does: SQLite hands a
    deleted row's id to the next insert, test_review.py deletes review cards between its
    own tests, and a brand new card can therefore arrive already carrying another test's
    remedial note and answer this endpoint with that note's cooldown instead.
    """
    session = SessionLocal()
    try:
        key = f"shape probe {uuid4().hex[:8]}"
        moment = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=4)
        for rating in (fsrs.AGAIN, fsrs.AGAIN, fsrs.GOOD):
            review.record_review(session, key, "Probe", rating, now=moment)
            moment += timedelta(days=1)
        session.commit()
        card = review.get_card(session, key)
        session.query(models.RemediationNote).filter(
            models.RemediationNote.card_id == card.id
        ).delete()
        session.commit()
        return card.id
    finally:
        session.close()


def test_generating_with_no_source_carries_a_code(client):
    """One of the two QA found still answering with a bare string.

    The status is asserted as well as the body, and that is not belt and braces. The
    tempting wrong fix is to let this fall through to the RequestValidationError handler,
    by making `text` and `url` a validated either-or in the model; that produces a
    perfectly well formed body with `invalid_request` in it and a 422, and a test checking
    only the shape would pass. It is the wrong answer because the sentence would stop
    naming the two fields, which is the entire content of this refusal.
    """
    response = client.post("/courses/generate", json={})

    assert response.status_code == 400, "a 422 here means the check moved into the schema"
    assert _detail(response) == {"error": "no_source", "message": main.NO_SOURCE_MESSAGE}


def test_rating_a_card_with_a_rating_nobody_uses_carries_a_code(client, card_id):
    """The other one, and the reason the fixture builds a real card.

    The message keeps naming the legal ratings, which is why this is a coded refusal
    rather than something the generic handler could produce: `invalid_request` would say
    a value was wrong and not which values are right.
    """
    response = client.post(f"/review/cards/{card_id}/rate", json={"rating": 99})

    assert response.status_code == 400, "a 404 here means the fixture's card did not exist"
    detail = _detail(response)
    assert detail == {"error": "invalid_rating", "message": main.INVALID_RATING_MESSAGE}
    for rating in fsrs.RATINGS:
        assert str(rating) in detail["message"], "the message has to name the legal ratings"


def test_the_two_coded_400s_do_not_share_a_code(client, card_id):
    """Distinct codes, which is the whole point of having a code at all.

    A fix that gave both refusals the same code, or reused `invalid_request` for both,
    would satisfy every shape assertion above and leave a client exactly where it started:
    unable to tell one refusal from another without reading the prose. Asserted across the
    two endpoints together, because neither test alone can see it.
    """
    no_source = client.post("/courses/generate", json={})
    bad_rating = client.post(f"/review/cards/{card_id}/rate", json={"rating": 99})

    codes = {_detail(no_source)["error"], _detail(bad_rating)["error"]}
    assert len(codes) == 2, f"both refusals answer with the same code: {codes}"
    assert main.INVALID_REQUEST_ERROR not in codes, (
        "a hand-rolled refusal took the generic handler's code, so a client cannot tell "
        "a refusal this endpoint chose from one the framework produced"
    )


def test_the_remediation_refusal_carries_a_code(client, card_id):
    """The 422 that used to be a bare string, and the reason it took a grep to find.

    A concept with no lesson text cannot be re-taught, and the refusal said so in prose
    with nothing to branch on. It reuses `no_material`, which the tutor already returns for
    the same condition on a different route, because one condition answering to two codes
    is the problem this whole line of work is about, one level up.

    The fixture's card is flagged, so this gets past the 409 that refuses an unflagged
    concept, and nothing teaches its concept, which is exactly the state that has no
    material. Both are asserted by the status check rather than assumed.
    """
    response = client.post(f"/review/cards/{card_id}/remediation")

    assert response.status_code == 422, response.text
    assert _detail(response) == {"error": "no_material", "message": main.NO_MATERIAL_MESSAGE}


@pytest.mark.parametrize("key", ["", "   ", "\t\n"], ids=["empty", "spaces", "whitespace"])
def test_an_empty_concept_key_is_refused_by_both_tutor_endpoints(client, key):
    """An empty key is an ABSENT concept, not an unknown one, and both routes now say so.

    THE ASSERTION IS THE AGREEMENT rather than either refusal on its own. Before this, the
    POST answered `no_material`, a true sentence about the wrong thing, and the GET
    answered 200 with an empty transcript and a blank concept_label. One request, two
    answers, and a client would have had to learn both. Checking only one endpoint would
    have left that split in place and passed.

    Whitespace is in the parametrization because normalize_concept turns it into nothing
    real, so it is the same request wearing a different hat, and a fix that special-cased
    the empty string alone would pass an empty-string-only test.
    """
    posted = client.post("/tutor/messages", json={"concept_key": key, "message": "m"})
    fetched = client.get("/tutor/conversation", params={"concept_key": key})

    expected = {"error": "concept_key_empty", "message": main.CONCEPT_KEY_EMPTY_MESSAGE}
    assert posted.status_code == 422, posted.text
    assert fetched.status_code == 422, fetched.text
    assert _detail(posted) == expected
    assert _detail(fetched) == expected


def test_a_concept_nobody_has_asked_about_is_still_described_not_refused(client):
    """The other side of that boundary, and the reason it is a boundary rather than a rule.

    A key that names something real but has no conversation behind it MUST stay a 200. The
    Today screen fans this endpoint out per concept, and a 4xx for every concept nobody has
    asked about would make a page of ordinary answers look broken. Without this, the
    obvious over-fix, refusing anything with no rows, passes every assertion above.
    """
    response = client.get("/tutor/conversation", params={"concept_key": "nobody asked this"})

    assert response.status_code == 200
    body = response.json()
    assert body["messages"] == []
    assert body["concept_label"] == "nobody asked this"


def test_a_404_still_carries_a_bare_string_detail(client):
    """What a 404 ACTUALLY returns, asserted rather than merely not-the-422-shape.

    This used to be a disjunction, "not a dict OR not those two keys", which short-circuits
    on the first clause and therefore passes against almost any body a 404 could return,
    including several that would be genuine regressions. A guard rail rather than a check.

    It is now the positive statement, and that statement is also half of this file's
    headline claim: the handler covers 422s and leaves everything else alone, so a client
    still parses a string detail here and an object detail there. If 404s are ever brought
    into the shared shape that is a good change, and this is the test that has to be
    rewritten to make it, which is the right amount of friction for a change to an error
    contract.
    """
    missing = client.get("/courses/999999")

    assert missing.status_code == 404
    assert missing.json() == {"detail": "Course not found"}
