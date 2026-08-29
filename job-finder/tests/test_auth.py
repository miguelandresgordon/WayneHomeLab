"""Login, CSRF, logout, and rate limiting."""

from tests.conftest import USER_A_EMAIL, USER_A_PASSWORD, login


def test_login_requires_csrf(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": USER_A_EMAIL, "password": USER_A_PASSWORD},
    )
    assert response.status_code == 403


def test_login_rejects_bad_password(client) -> None:
    response = login(client, USER_A_EMAIL, "wrong-password")
    assert response.status_code == 401
    assert client.get("/api/v1/me").status_code == 401


def test_login_and_me(client) -> None:
    response = login(client, USER_A_EMAIL, USER_A_PASSWORD)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == USER_A_EMAIL
    me = client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == USER_A_EMAIL
    assert "password" not in me.json()
    assert "password_hash" not in me.json()


def test_logout_revokes_session(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    csrf = client.cookies.get("jf_csrf")
    response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert client.get("/api/v1/me").status_code == 401


def test_html_login_and_home(client) -> None:
    page = client.get("/login")
    assert page.status_code == 200
    assert 'name="csrf_token"' in page.text
    assert "disabled" not in page.text
    csrf = client.cookies.get("jf_csrf")
    posted = client.post(
        "/login",
        data={"email": USER_A_EMAIL, "password": USER_A_PASSWORD, "csrf_token": csrf},
        follow_redirects=False,
    )
    assert posted.status_code == 303
    home = client.get("/")
    assert home.status_code == 200
    assert USER_A_EMAIL in home.text
    assert 'id="profile-form"' in home.text
    assert 'id="search-profile-form"' in home.text
    assert 'id="search-profile-list"' in home.text
    assert 'id="resume-form"' in home.text
    assert 'id="resume-list"' in home.text
    assert 'id="answer-form"' in home.text
    assert 'id="answer-list"' in home.text
    assert 'src="/static/dashboard.js?v=3"' in home.text


def test_html_login_rejects_bad_csrf(client) -> None:
    client.get("/login")
    posted = client.post(
        "/login",
        data={"email": USER_A_EMAIL, "password": USER_A_PASSWORD, "csrf_token": "nope"},
        follow_redirects=False,
    )
    assert posted.status_code == 303
    assert "error=csrf" in posted.headers["location"]


def test_unauthenticated_me(client) -> None:
    assert client.get("/api/v1/me").status_code == 401
