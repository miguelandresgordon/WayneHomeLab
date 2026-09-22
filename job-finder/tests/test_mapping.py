"""Deterministic mapping and never-fill rules."""

from app.services.mapping import map_field, map_inventory, never_fill_reason

CONTEXT = {
    "email": "ana@local.test",
    "profile": {
        "full_name": "Ana Ejemplo",
        "phone": "600000000",
        "location": "Madrid",
        "linkedin_url": "https://linkedin.com/in/ana",
        "portfolio_url": None,
        "summary": "Ingeniera de datos.",
    },
    "preference": {"work_mode": "remote", "desired_roles": ["Data Engineer"]},
    "resume": {"id": 1, "original_filename": "cv.pdf"},
    "answers": [{"key": "motivacion", "text": "Quiero el puesto."}],
}


def test_never_fill_legal_and_password() -> None:
    assert never_fill_reason({"type": "password", "signals": {"name": "x"}}) == "blocked_type:password"
    reason = never_fill_reason(
        {
            "type": "checkbox",
            "signals": {"label": "Acepto las condiciones", "name": "accept_terms"},
        }
    )
    assert reason == "sensitive_or_legal"


def test_maps_name_email_and_work_mode() -> None:
    mapped = map_inventory(
        [
            {
                "local_id": "field-0",
                "type": "text",
                "element": "input",
                "signals": {"label": "Nombre completo", "name": "full_name", "autocomplete": "name"},
                "required": True,
            },
            {
                "local_id": "field-1",
                "type": "email",
                "element": "input",
                "signals": {"label": "Correo", "name": "email", "autocomplete": "email"},
            },
            {
                "local_id": "field-2",
                "type": "select",
                "element": "select",
                "signals": {"label": "Modalidad", "name": "work_mode"},
                "options": [
                    {"value": "remote", "label": "Remoto"},
                    {"value": "hybrid", "label": "Híbrido"},
                ],
            },
        ],
        CONTEXT,
        set(),
    )
    by_id = {item["local_id"]: item for item in mapped}
    assert by_id["field-0"]["allowed_action"] == "fill"
    assert by_id["field-0"]["value"] == "Ana Ejemplo"
    assert by_id["field-1"]["value"] == "ana@local.test"
    assert by_id["field-2"]["value"] == "remote"
    assert by_id["field-2"]["allowed_action"] == "fill"


def test_resume_and_legal_are_not_fill() -> None:
    resume = map_field(
        {
            "local_id": "field-3",
            "type": "file",
            "signals": {"label": "Currículum", "name": "resume"},
            "review_reason": "manual_file_review",
        },
        CONTEXT,
        set(),
    )
    assert resume["allowed_action"] == "review"
    assert resume["doc_ref"]["filename"] == "cv.pdf"
    assert resume["value"] is None

    legal = map_field(
        {
            "local_id": "field-4",
            "type": "checkbox",
            "signals": {"label": "Acepto las condiciones", "name": "accept_terms"},
            "review_reason": "sensitive_or_legal",
        },
        CONTEXT,
        set(),
    )
    assert legal["allowed_action"] == "never"


def test_already_resolved_is_skipped() -> None:
    field = {
        "local_id": "field-0",
        "type": "text",
        "signals": {"label": "Nombre completo", "name": "full_name", "autocomplete": "name"},
    }
    first = map_field(field, CONTEXT, set())
    again = map_field(field, CONTEXT, {first["fingerprint"]})
    assert again["allowed_action"] == "skip"
    assert again["already_resolved"] is True
