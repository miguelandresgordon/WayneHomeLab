"""Profile GET/PUT, CSRF enforcement, and per-user isolation."""

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    csrf_headers,
    login,
)


def test_profile_defaults_to_empty(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    assert response.json()["full_name"] is None


def test_profile_put_and_get(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    response = client.put(
        "/api/v1/profile",
        json={"full_name": "Ana Ejemplo", "location": "Madrid"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana Ejemplo"

    fetched = client.get("/api/v1/profile")
    assert fetched.json()["location"] == "Madrid"


def test_profile_requires_csrf(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    response = client.put("/api/v1/profile", json={"full_name": "Sin CSRF"})
    assert response.status_code == 403


def test_profile_is_isolated_per_user(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    client.put(
        "/api/v1/profile",
        json={"full_name": "Usuaria A"},
        headers=csrf_headers(client),
    )
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))

    login(client, USER_B_EMAIL, USER_B_PASSWORD)
    response = client.get("/api/v1/profile")
    assert response.json()["full_name"] is None
