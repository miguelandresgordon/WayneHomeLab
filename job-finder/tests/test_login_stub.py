"""HTML login page."""


def test_root_redirects_to_login(client) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_login_form_renders(client) -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Job Finder" in response.text
    assert 'name="csrf_token"' in response.text
    assert "Entrar" in response.text
