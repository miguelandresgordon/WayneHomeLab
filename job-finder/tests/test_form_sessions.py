"""Form sessions: analyze/fill-result, IDOR, origin change, resolved fields."""

from tests.conftest import (
    USER_A_EMAIL,
    USER_A_PASSWORD,
    USER_B_EMAIL,
    USER_B_PASSWORD,
    csrf_headers,
    login,
)

INVENTORY = {
    "schema_version": 1,
    "page": {"origin": "http://127.0.0.1:8765", "path": "/application-form.html", "title": "Candidatura"},
    "fields": [
        {
            "local_id": "field-0",
            "element": "input",
            "type": "text",
            "signals": {"label": "Nombre completo", "name": "full_name", "autocomplete": "name", "id": "", "placeholder": ""},
            "required": True,
        },
        {
            "local_id": "field-1",
            "element": "input",
            "type": "email",
            "signals": {"label": "Correo", "name": "email", "autocomplete": "email", "id": "", "placeholder": ""},
        },
        {
            "local_id": "field-2",
            "element": "select",
            "type": "select",
            "signals": {"label": "Modalidad", "name": "work_mode", "id": "", "autocomplete": "", "placeholder": ""},
            "options": [
                {"value": "remote", "label": "Remoto"},
                {"value": "hybrid", "label": "Híbrido"},
            ],
        },
        {
            "local_id": "field-3",
            "element": "textarea",
            "type": "textarea",
            "signals": {"label": "Motivación", "name": "motivation", "id": "", "autocomplete": "", "placeholder": ""},
        },
        {
            "local_id": "field-4",
            "element": "input",
            "type": "file",
            "signals": {"label": "Currículum", "name": "resume", "id": "", "autocomplete": "", "placeholder": ""},
            "review_reason": "manual_file_review",
        },
        {
            "local_id": "field-5",
            "element": "input",
            "type": "checkbox",
            "signals": {"label": "Acepto las condiciones", "name": "accept_terms", "id": "", "autocomplete": "", "placeholder": ""},
            "review_reason": "sensitive_or_legal",
        },
        {
            "local_id": "field-6",
            "element": "input",
            "type": "password",
            "signals": {"label": "Contraseña", "name": "password", "id": "", "autocomplete": "", "placeholder": ""},
        },
    ],
    "blocked_frames": 0,
}


def _bearer(client) -> str:
    login(client, USER_A_EMAIL, USER_A_PASSWORD)
    client.put(
        "/api/v1/profile",
        json={"full_name": "Ana Ejemplo", "phone": "600000000", "location": "Madrid", "summary": "Ingeniera de datos."},
        headers=csrf_headers(client),
    )
    profile = client.post(
        "/api/v1/search-profiles",
        json={"name": "Data", "is_default": True, "is_active": True},
        headers=csrf_headers(client),
    ).json()
    client.put(
        f"/api/v1/search-profiles/{profile['id']}/preferences",
        json={"desired_roles": ["Data Engineer"], "locations": ["Madrid"], "work_mode": "remote"},
        headers=csrf_headers(client),
    )
    token = client.post(
        "/api/v1/auth/extension-tokens",
        json={"name": "Safari"},
        headers=csrf_headers(client),
    ).json()["token"]
    return token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_analyze_fill_and_never_fill_with_bearer(client) -> None:
    token = _bearer(client)
    session = client.post(
        "/api/v1/form-sessions",
        json={"origin": "http://127.0.0.1:8765", "tab_key": "tab-1", "apply_url": "http://127.0.0.1:8765/application-form.html"},
        headers=_auth(token),
    )
    assert session.status_code == 200
    session_id = session.json()["id"]
    analyzed = client.post(
        f"/api/v1/form-sessions/{session_id}/analyze",
        json=INVENTORY,
        headers=_auth(token),
    )
    assert analyzed.status_code == 200
    mappings = {item["local_id"]: item for item in analyzed.json()["mappings"]}
    assert mappings["field-0"]["allowed_action"] == "fill"
    assert mappings["field-0"]["value"] == "Ana Ejemplo"
    assert mappings["field-1"]["value"] == USER_A_EMAIL
    assert mappings["field-2"]["value"] == "remote"
    assert mappings["field-5"]["allowed_action"] == "never"
    assert mappings["field-6"]["allowed_action"] == "never"
    assert mappings["field-4"]["allowed_action"] == "review"

    filled = client.post(
        f"/api/v1/form-sessions/{session_id}/fill-result",
        json={"results": [{"local_id": "field-0", "ok": True}, {"local_id": "field-5", "ok": True}]},
        headers=_auth(token),
    )
    assert filled.status_code == 200
    by_id = {item["local_id"]: item for item in filled.json()["results"]}
    assert by_id["field-0"]["fill_status"] == "applied"
    assert by_id["field-5"]["fill_status"] == "never"

    completed = client.post(
        f"/api/v1/form-sessions/{session_id}/complete",
        headers=_auth(token),
    )
    assert completed.json()["application_status"] == "applied"


def test_form_session_idor(client) -> None:
    token_a = _bearer(client)
    session_id = client.post(
        "/api/v1/form-sessions",
        json={"origin": "http://127.0.0.1:8765", "tab_key": "tab-idor"},
        headers=_auth(token_a),
    ).json()["id"]
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    login(client, USER_B_EMAIL, USER_B_PASSWORD)
    token_b = client.post(
        "/api/v1/auth/extension-tokens",
        json={"name": "Safari B"},
        headers=csrf_headers(client),
    ).json()["token"]
    assert client.get(f"/api/v1/form-sessions/{session_id}", headers=_auth(token_b)).status_code == 404
    assert client.post(
        f"/api/v1/form-sessions/{session_id}/analyze",
        json=INVENTORY,
        headers=_auth(token_b),
    ).status_code == 404


def test_origin_change_requires_new_session(client) -> None:
    token = _bearer(client)
    session_id = client.post(
        "/api/v1/form-sessions",
        json={"origin": "http://portal-a.test", "tab_key": "tab-nav"},
        headers=_auth(token),
    ).json()["id"]
    inventory = {
        **INVENTORY,
        "page": {"origin": "http://portal-b.test", "path": "/apply", "title": "Otro ATS"},
    }
    changed = client.post(
        f"/api/v1/form-sessions/{session_id}/analyze",
        json=inventory,
        headers=_auth(token),
    )
    assert changed.status_code == 409
    assert changed.json()["detail"] == "origin_changed"

    reused = client.post(
        "/api/v1/form-sessions",
        json={"origin": "http://portal-a.test", "tab_key": "tab-nav"},
        headers=_auth(token),
    )
    assert reused.json()["id"] == session_id
    assert reused.json()["created"] is False

    fresh = client.post(
        "/api/v1/form-sessions",
        json={"origin": "http://portal-b.test", "tab_key": "tab-nav"},
        headers=_auth(token),
    )
    assert fresh.json()["id"] != session_id
    assert fresh.json()["created"] is True


def test_resolved_fields_are_not_asked_again(client) -> None:
    token = _bearer(client)
    session_id = client.post(
        "/api/v1/form-sessions",
        json={"origin": "http://127.0.0.1:8765", "tab_key": "tab-multi"},
        headers=_auth(token),
    ).json()["id"]
    first = client.post(
        f"/api/v1/form-sessions/{session_id}/analyze",
        json=INVENTORY,
        headers=_auth(token),
    ).json()
    client.post(
        f"/api/v1/form-sessions/{session_id}/fill-result",
        json={"results": [{"local_id": "field-0", "ok": True}]},
        headers=_auth(token),
    )
    second_page = {
        **INVENTORY,
        "page": {"origin": "http://127.0.0.1:8765", "path": "/application-form.html?step=2", "title": "Paso 2"},
    }
    second = client.post(
        f"/api/v1/form-sessions/{session_id}/analyze",
        json=second_page,
        headers=_auth(token),
    )
    assert second.status_code == 200
    mappings = {item["local_id"]: item for item in second.json()["mappings"]}
    assert mappings["field-0"]["allowed_action"] == "skip"
    assert mappings["field-0"]["already_resolved"] is True
    assert first["page_id"] != second.json()["page_id"]
