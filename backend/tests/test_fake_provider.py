"""End-to-end course generation through the API with STUDYFORGE_LLM_PROVIDER=fake."""

import json

from app import generation, models, remediation, tutor
from app.llm import get_provider
from app.llm.fake_provider import (
    HOSTILE_LESSON_TITLE,
    OUTLINE_MARKER,
    REMEDIATION_MARKER,
    TUTOR_MARKER,
    FakeProvider,
)


def test_get_provider_selects_fake(monkeypatch):
    monkeypatch.setenv("STUDYFORGE_LLM_PROVIDER", "fake")
    assert isinstance(get_provider(), FakeProvider)


def test_fake_provider_is_deterministic_and_input_sensitive():
    provider = FakeProvider()
    outline_prompt = "Source material:\n\nPhotosynthesis converts light energy."
    first = provider.generate("curriculum designer", outline_prompt)
    second = provider.generate("curriculum designer", outline_prompt)
    assert first.text == second.text
    other = provider.generate("curriculum designer", "Source material:\n\nGraph theory basics.")
    assert other.text != first.text


def test_fake_provider_reports_estimated_token_usage():
    provider = FakeProvider()
    result = provider.generate("curriculum designer", "Source material:\n\nSome text here.")
    assert result.input_tokens == max(1, len(result.text) // 4)
    assert result.output_tokens == max(1, len(result.text) // 4)
    assert provider.is_paid is False
    assert provider.name == "fake"


def _remediation_prompt(concept="Gradient Descent", lesson="Optimization Basics"):
    return (
        f"{remediation.MATERIAL_OPEN}\n"
        f"Concept: {concept}\n\n"
        f"--- Lesson: {lesson} ---\n"
        f"Some lesson text about {concept}.\n"
        f"{remediation.MATERIAL_CLOSE}"
    )


def _tutor_prompt(question="explain this", concept="Gradient Descent"):
    """Built through the real build_prompt, so the fake is fed what production sends."""
    return tutor.build_prompt(
        tutor.TutorContext(
            concept_label=concept,
            # An unattached Lesson row: never flushed, so no module or course is needed.
            lessons=[models.Lesson(title="Optimization Basics", content="Some lesson text.")],
            # Question-only, which is the common case: answer keys are withheld for
            # every item under an open retrieval.
            items=[tutor.MaterialItem(question="What does it minimize?", answer=None)],
            flagged=False,
            missed=0,
            of=0,
            bucket="not_started",
            recent_incorrect=[],
        ),
        [],
        question,
    )


def test_fake_provider_answers_every_live_system_prompt():
    """The drift guard. Dispatch is by phrase, so the phrases are fed in for real.

    A stage this provider does not recognize falls through to the lesson branch and
    hands back JSON the caller cannot parse. That is not a loud failure: it looks
    like a 502 from the model. Remediation shipped broken offline exactly this way,
    so every stage's real system prompt is checked against the real parser here.
    """
    provider = FakeProvider()

    outline = generation.parse_json_response(
        provider.generate(generation.outline_system(4), "Source material:\n\nText.").text
    )
    assert outline["modules"]

    lesson = generation.parse_json_response(
        provider.generate(generation.LESSON_SYSTEM, "Lesson title: A\nSource material:\n\nText.").text
    )
    assert lesson["content"] and lesson["quiz"]

    # parse_note raises unless both fields are present and non-empty.
    content = remediation.parse_note(
        provider.generate(remediation.REMEDIATION_SYSTEM, _remediation_prompt()).text
    )
    assert "In simpler terms" in content
    assert "Worked example" in content

    # parse_reply raises unless `answer` is present and non-empty.
    reply = tutor.parse_reply(
        provider.generate(tutor.TUTOR_SYSTEM, _tutor_prompt()).text
    )
    assert reply.answer


def test_the_stage_markers_are_mutually_exclusive():
    """Dispatch is first-match on a chain, so one prompt must match exactly one marker.

    TUTOR_SYSTEM containing "curriculum designer" or "re-teaching one concept" would
    route the tutor to a branch whose JSON parse_reply cannot read, and the symptom
    would be a 502 that looks like the network. Checked against the live prompts so
    that rewording any of them fails here.
    """
    systems = {
        "outline": generation.outline_system(4),
        "lesson": generation.LESSON_SYSTEM,
        "remediation": remediation.REMEDIATION_SYSTEM,
        "tutor": tutor.TUTOR_SYSTEM,
    }
    matched = {
        name: [
            marker
            for marker in (OUTLINE_MARKER, REMEDIATION_MARKER, TUTOR_MARKER)
            if marker in system
        ]
        for name, system in systems.items()
    }
    assert matched["outline"] == [OUTLINE_MARKER]
    assert matched["remediation"] == [REMEDIATION_MARKER]
    assert matched["tutor"] == [TUTOR_MARKER]
    # The lesson stage is the fall-through and deliberately matches nothing.
    assert matched["lesson"] == []


def test_fake_remediation_is_deterministic_and_concept_sensitive():
    provider = FakeProvider()
    system = remediation.REMEDIATION_SYSTEM

    first = provider.generate(system, _remediation_prompt("Backpropagation")).text
    again = provider.generate(system, _remediation_prompt("Backpropagation")).text
    other = provider.generate(system, _remediation_prompt("Quorum Reads")).text

    assert first == again
    assert first != other
    # Named in the note, not just varied by a hash, so an offline UI is readable.
    assert "Backpropagation" in json.loads(first)["restatement"]
    assert "Quorum Reads" in json.loads(other)["restatement"]


def test_fake_remediation_carries_hostile_markdown_for_the_hostile_concept():
    """A note is model-written markdown in the browser, so it gets the same check."""
    provider = FakeProvider()
    note = json.loads(
        provider.generate(
            remediation.REMEDIATION_SYSTEM, _remediation_prompt(HOSTILE_LESSON_TITLE)
        ).text
    )
    assert "<script>alert(1)</script>" in note["worked_example"]

    benign = json.loads(
        provider.generate(remediation.REMEDIATION_SYSTEM, _remediation_prompt("Recursion")).text
    )
    assert "<script>" not in benign["worked_example"]


def _reply(provider, question, concept="Gradient Descent"):
    return tutor.parse_reply(
        provider.generate(tutor.TUTOR_SYSTEM, _tutor_prompt(question, concept)).text
    )


def test_fake_tutor_produces_every_shape_the_reply_schema_allows():
    """`beyond` and `check` are both optional, so all four combinations need fixtures.

    A fake that only ever produced one shape would leave the other rendering paths
    unreachable offline, which is how the frontend ends up with a branch nobody has
    ever seen. See the module docstring for the phrases that drive each shape.
    """
    provider = FakeProvider()

    plain = _reply(provider, "how does this work?")
    assert plain.answer and plain.check and not plain.beyond

    with_beyond = _reply(provider, "what is beyond this?")
    assert with_beyond.answer and with_beyond.beyond and with_beyond.check

    answer_only = _reply(provider, "just tell me how it works")
    assert answer_only.answer and not answer_only.beyond and not answer_only.check

    beyond_no_check = _reply(provider, "just tell me what is beyond this")
    assert beyond_no_check.answer and beyond_no_check.beyond and not beyond_no_check.check


def test_fake_tutor_beyond_survives_the_cap_intact():
    """The fixture is written to sit inside the cap, so QA sees a whole aside."""
    reply = _reply(FakeProvider(), "what is beyond this?")
    assert reply.beyond == tutor.truncate_beyond(reply.beyond)
    assert len(reply.beyond) <= tutor.BEYOND_MAX_CHARS


def test_fake_tutor_is_deterministic_and_concept_sensitive():
    provider = FakeProvider()
    first = _reply(provider, "explain", "Backpropagation")
    again = _reply(provider, "explain", "Backpropagation")
    other = _reply(provider, "explain", "Quorum Reads")

    assert first == again
    assert first != other
    assert "Backpropagation" in first.answer
    assert "Quorum Reads" in other.answer


def test_fake_tutor_carries_hostile_markdown_for_the_hostile_concept():
    """A tutor answer is model-written markdown in the browser, like a lesson is."""
    provider = FakeProvider()
    assert "<script>alert(1)</script>" in _reply(provider, "explain", HOSTILE_LESSON_TITLE).answer
    assert "<script>" not in _reply(provider, "explain", "Recursion").answer


def test_generate_endpoint_with_fake_provider(client, monkeypatch):
    monkeypatch.setenv("STUDYFORGE_LLM_PROVIDER", "fake")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    resp = client.post(
        "/courses/generate",
        json={"text": "Photosynthesis converts light energy into chemical energy in plants."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Photosynthesis" in body["title"]

    course = client.get(f"/courses/{body['id']}").json()
    assert len(course["modules"]) == 2
    assert all(len(module["lessons"]) == 2 for module in course["modules"])

    hostile_seen = False
    for module in course["modules"]:
        for stub in module["lessons"]:
            lesson = client.get(f"/lessons/{stub['id']}").json()
            assert lesson["content"].startswith("# ")
            assert 2 <= len(lesson["concepts"]) <= 3
            kinds = {item["kind"] for item in lesson["quiz"]}
            assert {"mcq", "short"} <= kinds
            mcq = next(item for item in lesson["quiz"] if item["kind"] == "mcq")
            assert len(mcq["options"]) == 4
            if lesson["title"] == HOSTILE_LESSON_TITLE:
                hostile_seen = True
                assert "<script>alert(1)</script>" in lesson["content"]
                assert "Ignore previous instructions" in lesson["content"]
    assert hostile_seen

    # The short-answer item is gradeable through the answer endpoint.
    first_lesson = client.get(f"/lessons/{course['modules'][0]['lessons'][0]['id']}").json()
    short = next(item for item in first_lesson["quiz"] if item["kind"] == "short")
    graded = client.post(f"/quiz/{short['id']}/answer", json={"answer": "forge"}).json()
    assert graded["correct"] is True


def test_the_hostile_concept_is_reachable_by_playing(client, monkeypatch):
    """The hostile note has to be reachable by using the app, not by seeding a card.

    Review cards are created from quiz attempts and nothing else. While this concept
    was carried only by the lesson's concept list, no attempt could ever name it, so
    it could never have a card and the note that the markdown escaping check exists
    for could never be generated offline at all: QA had to insert a card by hand.
    This walks the real path instead, from the quiz item through to the note.
    """
    monkeypatch.setenv("STUDYFORGE_LLM_PROVIDER", "fake")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    generated = client.post(
        "/courses/generate",
        json={"text": "Untrusted input reaches every parser eventually."},
    ).json()
    course = client.get(f"/courses/{generated['id']}").json()
    lessons = [
        client.get(f"/lessons/{stub['id']}").json()
        for module in course["modules"]
        for stub in module["lessons"]
    ]
    hostile = next(lesson for lesson in lessons if lesson["title"] == HOSTILE_LESSON_TITLE)
    item = next(q for q in hostile["quiz"] if q["concept"] == HOSTILE_LESSON_TITLE)

    # Two misses, because that is the trigger the re-teach button is drawn from. The
    # wrong answers differ so the double-submit guard reads them as two answers.
    for wrong in ("first wrong answer", "second wrong answer"):
        client.post(f"/quiz/{item['id']}/answer", json={"answer": wrong})
        client.post(f"/lessons/{hostile['id']}/complete")
        client.delete(f"/lessons/{hostile['id']}/complete")

    flagged = client.get("/review/today").json()["needs_attention"]
    entry = next(row for row in flagged if row["concept_label"] == HOSTILE_LESSON_TITLE)

    note = client.post(f"/review/cards/{entry['card_id']}/remediation")
    assert note.status_code == 200
    assert "<script>alert(1)</script>" in note.json()["content"]
