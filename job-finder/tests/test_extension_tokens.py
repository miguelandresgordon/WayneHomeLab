"""Extension API tokens: web-only minting, bearer auth, revoke."""

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    csrf_headers,
    login,
)


def _create_token(client, name: str = "Safari"):
    return client.post(
        "/api/v1/auth/extension-tokens",
        json={"name": name},
        headers=csrf_headers(client),
    )


def test_extension_token_requires_web_session_and_csrf(client) -> None:
    assert client.post("/api/v1/auth/extension-tokens", json={"name": "Safari"}).status_code == 401
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    assert client.post("/api/v1/auth/extension-tokens", json={"name": "Safari"}).status_code == 403
    created = _create_token(client)
    assert created.status_code == 201
    assert created.json()["token"]
    listed = client.get("/api/v1/auth/extension-tokens")
    assert listed.status_code == 200
    assert "token" not in listed.json()["tokens"][0]


def test_bearer_token_authenticates_and_revocation_works(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    created = _create_token(client)
    raw = created.json()["token"]
    token_id = created.json()["id"]
    headers = {"Authorization": f"Bearer {raw}"}
    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == USER_A_EMAIL

    forbidden = client.post(
        "/api/v1/auth/extension-tokens",
        json={"name": "Nope"},
        headers=headers,
    )
    assert forbidden.status_code == 403

    revoked = client.delete(
        f"/api/v1/auth/extension-tokens/{token_id}",
        headers=csrf_headers(client),
    )
    assert revoked.status_code == 200
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_extension_token_idor(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    token_a = _create_token(client).json()
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    login(client, USER_B_EMAIL, USER_B_PASSWORD)
    listed = client.get("/api/v1/auth/extension-tokens")
    assert listed.json()["tokens"] == []
    deleted = client.delete(
        f"/api/v1/auth/extension-tokens/{token_a['id']}",
        headers=csrf_headers(client),
    )
    assert deleted.status_code == 404
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token_a['token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == USER_A_EMAIL
