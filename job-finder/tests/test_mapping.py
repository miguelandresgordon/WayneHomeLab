"""Deterministic mapping and never-fill rules."""

from app.services.mapping import (
    field_fingerprint,
    map_field,
    map_inventory,
    never_fill_reason,
    split_full_name,
)

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


def test_split_full_name_on_first_space() -> None:
    assert split_full_name("Ana Ejemplo") == ("Ana", "Ejemplo")
    assert split_full_name("Ana María López") == ("Ana", "María López")
    assert split_full_name("Ana") == ("Ana", None)
    assert split_full_name("  ") == (None, None)


def test_maps_first_and_last_name_from_full_name() -> None:
    mapped = map_inventory(
        [
            {
                "local_id": "first",
                "type": "text",
                "element": "input",
                "signals": {
                    "label": "Nombre",
                    "name": "first_name",
                    "autocomplete": "given-name",
                    "id": "",
                    "placeholder": "",
                },
            },
            {
                "local_id": "last",
                "type": "text",
                "element": "input",
                "signals": {
                    "label": "Apellidos",
                    "name": "last_name",
                    "autocomplete": "family-name",
                    "id": "",
                    "placeholder": "",
                },
            },
            {
                "local_id": "full",
                "type": "text",
                "element": "input",
                "signals": {
                    "label": "Nombre completo",
                    "name": "full_name",
                    "autocomplete": "name",
                    "id": "",
                    "placeholder": "",
                },
            },
        ],
        CONTEXT,
        set(),
    )
    by_id = {item["local_id"]: item for item in mapped}
    assert by_id["first"]["allowed_action"] == "fill"
    assert by_id["first"]["profile_key"] == "first_name"
    assert by_id["first"]["value"] == "Ana"
    assert by_id["last"]["allowed_action"] == "fill"
    assert by_id["last"]["profile_key"] == "last_name"
    assert by_id["last"]["value"] == "Ejemplo"
    assert by_id["full"]["allowed_action"] == "fill"
    assert by_id["full"]["profile_key"] == "full_name"
    assert by_id["full"]["value"] == "Ana Ejemplo"


def test_nombre_label_maps_to_first_name_not_full_name() -> None:
    first = map_field(
        {
            "local_id": "n",
            "type": "text",
            "signals": {"label": "Nombre", "name": "", "autocomplete": ""},
        },
        CONTEXT,
        set(),
    )
    assert first["profile_key"] == "first_name"
    assert first["value"] == "Ana"
    assert first["allowed_action"] == "fill"


def test_last_name_unmapped_when_full_name_is_single_token() -> None:
    context = {
        **CONTEXT,
        "profile": {**CONTEXT["profile"], "full_name": "Ana"},
    }
    last = map_field(
        {
            "local_id": "last",
            "type": "text",
            "signals": {"label": "Apellidos", "name": "last_name", "autocomplete": "family-name"},
        },
        context,
        set(),
    )
    assert last["profile_key"] == "last_name"
    assert last["value"] is None
    assert last["allowed_action"] == "review"


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
    assert again["explanation"] == "Ya rellenado en esta sesión; no se vuelve a preguntar."


def test_section_changes_fingerprint_and_blocks_profile_rules() -> None:
    education = {
        "local_id": "edu-city",
        "type": "text",
        "has_value": False,
        "signals": {"label": "City", "name": "educationcity", "section": "Education", "entry": "1"},
    }
    experience = {
        "local_id": "work-city",
        "type": "text",
        "signals": {"label": "City", "name": "educationcity", "section": "Work Experience", "entry": "1"},
    }
    assert field_fingerprint(education) != field_fingerprint(experience)

    mapped = map_field(education, CONTEXT, set())
    assert mapped["profile_key"] is None
    assert mapped["allowed_action"] == "review"
    assert mapped["review_reason"] == "unmapped"
    assert mapped["value"] is None


def test_existing_form_value_is_review_not_empty_profile_fill() -> None:
    mapped = map_field(
        {
            "local_id": "edu-description",
            "type": "textarea",
            "has_value": True,
            "signals": {"label": "Description", "name": "description", "section": "Education"},
        },
        CONTEXT,
        set(),
    )
    assert mapped["allowed_action"] == "review"
    assert mapped["review_reason"] == "already_filled"
    assert mapped["value"] is None
    assert mapped["has_value"] is True
    assert mapped["explanation"] == "El formulario ya tiene un valor; no se sobrescribe."
