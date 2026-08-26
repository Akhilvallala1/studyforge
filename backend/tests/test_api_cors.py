def test_preflight_returns_cors_headers(client):
    response = client.options(
        "/courses/generate",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_provider_failure_returns_502(client, failing_provider):
    response = client.post("/courses/generate", json={"text": "some source material"})
    assert response.status_code == 502
    assert response.json() == {"detail": "Course generation failed: provider exploded"}
