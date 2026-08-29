"""Search profiles: CRUD, single default, preferences, isolated per user."""

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    csrf_headers,
    login,
)


def test_create_list_update_delete_search_profile(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    created = client.post(
        "/api/v1/search-profiles",
        json={"name": "Backend EU", "is_default": True, "is_active": True},
        headers=csrf_headers(client),
    )
    assert created.status_code == 201
    profile_id = created.json()["id"]

    listed = client.get("/api/v1/search-profiles")
    assert len(listed.json()) == 1
    assert listed.json()[0]["is_default"] is True

    updated = client.put(
        f"/api/v1/search-profiles/{profile_id}",
        json={"name": "Backend EU remoto", "is_default": True, "is_active": True},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Backend EU remoto"

    deleted = client.delete(f"/api/v1/search-profiles/{profile_id}", headers=csrf_headers(client))
    assert deleted.status_code == 204
    assert client.get("/api/v1/search-profiles").json() == []


def test_duplicate_name_rejected(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    client.post("/api/v1/search-profiles", json={"name": "Backend"}, headers=csrf_headers(client))
    dup = client.post("/api/v1/search-profiles", json={"name": "Backend"}, headers=csrf_headers(client))
    assert dup.status_code == 409


def test_only_one_default_per_user(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    first = client.post(
        "/api/v1/search-profiles", json={"name": "A", "is_default": True}, headers=csrf_headers(client)
    ).json()
    second = client.post(
        "/api/v1/search-profiles", json={"name": "B", "is_default": True}, headers=csrf_headers(client)
    ).json()

    listed = {p["id"]: p["is_default"] for p in client.get("/api/v1/search-profiles").json()}
    assert listed[first["id"]] is False
    assert listed[second["id"]] is True


def test_preferences_roundtrip(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    profile = client.post(
        "/api/v1/search-profiles", json={"name": "Backend"}, headers=csrf_headers(client)
    ).json()

    put = client.put(
        f"/api/v1/search-profiles/{profile['id']}/preferences",
        json={
            "desired_roles": ["Backend Engineer", "Platform Engineer"],
            "locations": ["Madrid", "Remoto"],
            "work_mode": "remote",
            "salary_min": 40000,
            "salary_currency": "EUR",
            "requires_sponsorship": False,
        },
        headers=csrf_headers(client),
    )
    assert put.status_code == 200
    assert put.json()["desired_roles"] == ["Backend Engineer", "Platform Engineer"]

    fetched = client.get(f"/api/v1/search-profiles/{profile['id']}")
    assert fetched.json()["preferences"]["locations"] == ["Madrid", "Remoto"]


def test_partial_preferences_update_preserves_unsent_fields(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    profile = client.post(
        "/api/v1/search-profiles", json={"name": "Backend"}, headers=csrf_headers(client)
    ).json()

    client.put(
        f"/api/v1/search-profiles/{profile['id']}/preferences",
        json={
            "desired_roles": ["Backend Engineer"],
            "requires_sponsorship": True,
            "salary_max": 90000,
            "willing_to_relocate": True,
        },
        headers=csrf_headers(client),
    )

    partial = client.put(
        f"/api/v1/search-profiles/{profile['id']}/preferences",
        json={
            "desired_roles": ["Platform Engineer"],
            "locations": ["Remoto"],
            "work_mode": "remote",
            "salary_min": 40000,
            "salary_currency": "EUR",
        },
        headers=csrf_headers(client),
    )
    assert partial.status_code == 200

    prefs = client.get(f"/api/v1/search-profiles/{profile['id']}").json()["preferences"]
    assert prefs["desired_roles"] == ["Platform Engineer"]
    assert prefs["locations"] == ["Remoto"]
    assert prefs["salary_min"] == 40000
    assert prefs["salary_max"] == 90000
    assert prefs["requires_sponsorship"] is True
    assert prefs["willing_to_relocate"] is True


def test_search_profile_isolated_per_user(client) -> None:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    profile = client.post(
        "/api/v1/search-profiles", json={"name": "Solo A"}, headers=csrf_headers(client)
    ).json()
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))

    login(client, USER_B_EMAIL, USER_B_PASSWORD)
    forbidden = client.get(f"/api/v1/search-profiles/{profile['id']}")
    assert forbidden.status_code == 404

    forbidden_delete = client.delete(f"/api/v1/search-profiles/{profile['id']}", headers=csrf_headers(client))
    assert forbidden_delete.status_code == 404
