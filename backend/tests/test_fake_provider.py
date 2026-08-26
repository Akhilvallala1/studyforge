"""End-to-end course generation through the API with STUDYFORGE_LLM_PROVIDER=fake."""

from app.llm import get_provider
from app.llm.fake_provider import HOSTILE_LESSON_TITLE, FakeProvider


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
