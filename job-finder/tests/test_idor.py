"""User A cannot read user B."""

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    login,
)


def test_user_cannot_read_other_user(client) -> None:
    login_a = login(client, USER_A_EMAIL, USER_A_PASSWORD)
    id_a = login_a.json()["id"]
    client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": client.cookies.get("jf_csrf")},
    )

    login_b = login(client, USER_B_EMAIL, USER_B_PASSWORD)
    id_b = login_b.json()["id"]
    assert id_a != id_b

    forbidden = client.get(f"/api/v1/users/{id_a}")
    assert forbidden.status_code == 403

    own = client.get(f"/api/v1/users/{id_b}")
    assert own.status_code == 200
    assert own.json()["email"] == USER_B_EMAIL
    assert own.json()["email"] != USER_A_EMAIL

    me = client.get("/api/v1/me")
    assert me.json()["id"] == id_b
