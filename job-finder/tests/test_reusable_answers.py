"""Reusable answers CRUD and per-user isolation."""

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    csrf_headers,
    login,
)


def test_create_list_update_delete_answer(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    created = client.post(
        "/api/v1/reusable-answers",
        json={"key": "why_this_company", "text": "Porque..."},
        headers=csrf_headers(client),
    )
    assert created.status_code == 201
    answer_id = created.json()["id"]
    assert created.json()["locale"] == "es"

    listed = client.get("/api/v1/reusable-answers")
    assert len(listed.json()) == 1

    updated = client.put(
        f"/api/v1/reusable-answers/{answer_id}",
        json={"key": "why_this_company", "text": "Nueva respuesta"},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["text"] == "Nueva respuesta"

    deleted = client.delete(f"/api/v1/reusable-answers/{answer_id}", headers=csrf_headers(client))
    assert deleted.status_code == 204
    assert client.get("/api/v1/reusable-answers").json() == []


def test_duplicate_key_locale_rejected(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    client.post("/api/v1/reusable-answers", json={"key": "salary", "text": "40k"}, headers=csrf_headers(client))
    dup = client.post(
        "/api/v1/reusable-answers", json={"key": "salary", "text": "otra"}, headers=csrf_headers(client)
    )
    assert dup.status_code == 409


def test_update_cannot_duplicate_key_locale(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    first = client.post(
        "/api/v1/reusable-answers",
        json={"key": "motivation", "text": "Motivación"},
        headers=csrf_headers(client),
    ).json()
    client.post(
        "/api/v1/reusable-answers",
        json={"key": "salary", "text": "40k"},
        headers=csrf_headers(client),
    )

    duplicate = client.put(
        f"/api/v1/reusable-answers/{first['id']}",
        json={"key": "salary", "text": "Motivación"},
        headers=csrf_headers(client),
    )
    assert duplicate.status_code == 409


def test_reusable_answer_isolated_per_user(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    answer = client.post(
        "/api/v1/reusable-answers",
        json={"key": "why_this_company", "text": "Porque..."},
        headers=csrf_headers(client),
    ).json()
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))

    login(client, USER_B_EMAIL, USER_B_PASSWORD)
    forbidden = client.put(
        f"/api/v1/reusable-answers/{answer['id']}",
        json={"key": "x", "text": "y"},
        headers=csrf_headers(client),
    )
    assert forbidden.status_code == 404

    forbidden_delete = client.delete(f"/api/v1/reusable-answers/{answer['id']}", headers=csrf_headers(client))
    assert forbidden_delete.status_code == 404
