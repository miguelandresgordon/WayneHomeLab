"""Deterministic field mapping. No generative AI. Server never-fill wins."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

NEVER_FILL_RE = re.compile(
    r"(captcha|csrf|xsrf|authenticity|password|passwd|secret|token|consent|"
    r"terms|privacy|legal|gdpr|acepto|condiciones)",
    re.I,
)
BLOCKED_TYPES = {"password", "hidden", "submit", "button", "reset", "image"}
REVIEW_TYPES = {"file", "checkbox", "radio", "radio-group"}
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Rule:
    profile_key: str
    patterns: tuple[re.Pattern[str], ...]
    autocompletes: tuple[str, ...] = ()
    source: str = "profile"
    sensitivity: str = "normal"


def _p(*raw: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(item, re.I) for item in raw)


RULES: tuple[Rule, ...] = (
    Rule("email", _p(r"\b(e-?mail|correo)\b"), ("email",), source="user"),
    Rule(
        "full_name",
        _p(r"\b(full.?name|nombre completo|your name)\b", r"^name$", r"^nombre$"),
        ("name",),
    ),
    Rule(
        "phone",
        _p(r"\b(phone|tel[eé]fono|mobile|m[oó]vil|celular)\b"),
        ("tel", "tel-national"),
    ),
    Rule(
        "location",
        _p(r"\b(location|ubicaci[oó]n|ciudad|city|address|direcci[oó]n)\b"),
        ("address-level2", "street-address"),
    ),
    Rule("linkedin_url", _p(r"linkedin"), ()),
    Rule("portfolio_url", _p(r"\b(portfolio|github|website|web personal)\b"), ("url",)),
    Rule(
        "summary",
        _p(r"\b(summary|about|sobre m[ií]|cover.?letter|motivaci[oó]n|motivation|carta)\b"),
        (),
    ),
    Rule(
        "work_mode",
        _p(r"\b(work.?mode|modalidad|remote|remoto|h[ií]brido|presencial)\b"),
        (),
        source="preference",
    ),
    Rule(
        "availability",
        _p(r"\b(availability|disponibilidad|notice|preaviso)\b"),
        (),
        source="preference",
    ),
    Rule("salary_min", _p(r"\b(salary|salario|expectativa|compensat)\b"), (), source="preference"),
    Rule("desired_role", _p(r"\b(position|puesto|rol|role|job title)\b"), (), source="preference"),
    Rule(
        "willing_to_relocate",
        _p(r"\b(relocati|reubicaci[oó]n)\b"),
        (),
        source="preference",
    ),
    Rule("willing_to_travel", _p(r"\b(travel|viaj[eo])\b"), (), source="preference"),
    Rule(
        "requires_sponsorship",
        _p(r"\b(sponsor|visado|visa|work.?auth)\b"),
        (),
        source="preference",
    ),
    Rule("resume", _p(r"\b(resume|cv|curr[ií]culum|curriculum)\b"), (), source="resume", sensitivity="document"),
)


def field_fingerprint(field: dict[str, Any]) -> str:
    signals = field.get("signals") or {}
    raw = "|".join(
        [
            str(field.get("type") or ""),
            str(signals.get("name") or ""),
            str(signals.get("id") or ""),
            str(signals.get("label") or ""),
        ]
    ).lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _combined_signals(field: dict[str, Any]) -> str:
    signals = field.get("signals") or {}
    return " ".join(
        str(signals.get(key) or "")
        for key in ("label", "name", "id", "autocomplete", "placeholder")
    )


def never_fill_reason(field: dict[str, Any]) -> str | None:
    field_type = str(field.get("type") or "").lower()
    if field_type in BLOCKED_TYPES:
        return f"blocked_type:{field_type}"
    client_reason = str(field.get("review_reason") or "")
    if client_reason.startswith("blocked_type:"):
        return client_reason
    combined = _combined_signals(field)
    if NEVER_FILL_RE.search(combined) or client_reason == "sensitive_or_legal":
        return "sensitive_or_legal"
    return None


def _match_rule(field: dict[str, Any]) -> tuple[Rule, float, str] | None:
    signals = field.get("signals") or {}
    autocomplete = str(signals.get("autocomplete") or "").lower()
    name = str(signals.get("name") or "").lower()
    field_id = str(signals.get("id") or "").lower()
    combined = _combined_signals(field)
    for rule in RULES:
        if autocomplete and autocomplete in rule.autocompletes:
            return rule, 0.95, f"autocomplete={autocomplete}"
        if name and any(pattern.fullmatch(name) or pattern.search(name) for pattern in rule.patterns):
            if any(pattern.fullmatch(name) for pattern in rule.patterns):
                return rule, 0.9, f"name={name}"
        if field_id and any(pattern.fullmatch(field_id) for pattern in rule.patterns):
            return rule, 0.9, f"id={field_id}"
        if any(pattern.search(combined) for pattern in rule.patterns):
            return rule, 0.75, f"signals:{rule.profile_key}"
    return None


def _match_reusable_answer(
    field: dict[str, Any],
    answers: list[dict[str, str]],
) -> tuple[str, str, float, str] | None:
    combined = _combined_signals(field).lower()
    for answer in answers:
        key = answer["key"].strip().lower()
        if not key:
            continue
        if re.search(rf"\b{re.escape(key)}\b", combined):
            return key, answer["text"], 0.8, f"reusable_answer:{key}"
    return None


def _select_option_value(raw: str, options: list[dict[str, Any]] | None) -> str:
    if not options:
        return raw
    lowered = raw.strip().lower()
    for option in options:
        value = str(option.get("value") or "")
        label = str(option.get("label") or "")
        if value.lower() == lowered or label.lower() == lowered:
            return value or raw
    aliases = {
        "true": ("yes", "sí", "si", "1"),
        "false": ("no", "0"),
        "remote": ("remoto",),
        "hybrid": ("híbrido", "hibrido"),
        "onsite": ("presencial",),
    }
    for canonical, extra in aliases.items():
        if lowered == canonical or lowered in extra:
            for option in options:
                value = str(option.get("value") or "")
                label = str(option.get("label") or "")
                haystack = f"{value} {label}".lower()
                if canonical in haystack or any(item in haystack for item in extra):
                    return value or raw
    return raw


def _lookup_value(rule: Rule, context: dict[str, Any]) -> str | None:
    profile = context.get("profile") or {}
    preference = context.get("preference") or {}
    if rule.source == "user":
        value = context.get("email")
        return str(value) if value else None
    if rule.source == "profile":
        value = profile.get(rule.profile_key)
        return str(value) if value else None
    if rule.source == "preference":
        if rule.profile_key == "desired_role":
            roles = preference.get("desired_roles") or []
            return str(roles[0]) if roles else None
        value = preference.get(rule.profile_key)
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None or value == "":
            return None
        return str(value)
    return None


def map_field(
    field: dict[str, Any],
    context: dict[str, Any],
    resolved_fingerprints: set[str],
) -> dict[str, Any]:
    fingerprint = field_fingerprint(field)
    field_type = str(field.get("type") or "").lower()
    is_multi = bool(field.get("multiple"))
    blocked = never_fill_reason(field)
    base = {
        "local_id": field.get("local_id"),
        "fingerprint": fingerprint,
        "element": field.get("element") or "input",
        "type": field_type,
        "signals": field.get("signals") or {},
        "required": bool(field.get("required")),
        "profile_key": None,
        "value": None,
        "doc_ref": None,
        "confidence": None,
        "explanation": "",
        "sensitivity": "normal",
        "already_resolved": fingerprint in resolved_fingerprints,
    }

    if blocked:
        return {
            **base,
            "allowed_action": "never",
            "review_reason": blocked,
            "sensitivity": "legal" if blocked == "sensitive_or_legal" else "blocked",
            "explanation": "Never-fill: campo sensible, legal o de autenticación.",
        }

    if base["already_resolved"]:
        return {
            **base,
            "allowed_action": "skip",
            "review_reason": "already_resolved",
            "explanation": "Ya rellenado en esta sesión; no se vuelve a preguntar.",
        }

    answer_match = _match_reusable_answer(field, context.get("answers") or [])
    rule_match = _match_rule(field)

    profile_key = None
    value: str | None = None
    doc_ref = None
    confidence = None
    explanation = "Sin correspondencia automática."
    sensitivity = "normal"
    source = None

    if answer_match:
        profile_key, value, confidence, explanation = answer_match
        source = "answer"
    elif rule_match:
        rule, confidence, explanation = rule_match
        profile_key = rule.profile_key
        sensitivity = rule.sensitivity
        source = rule.source
        if rule.source == "resume":
            resume = context.get("resume")
            if resume:
                doc_ref = {
                    "kind": "resume",
                    "id": resume["id"],
                    "filename": resume["original_filename"],
                }
                explanation = f"{explanation}; CV predeterminado para adjuntar a mano."
        else:
            value = _lookup_value(rule, context)
            if value is not None:
                value = _select_option_value(value, field.get("options"))

    if field_type in REVIEW_TYPES or is_multi:
        reason = "manual_file_review" if field_type == "file" else "manual_choice_review"
        if is_multi:
            reason = "multi_select_review"
        return {
            **base,
            "profile_key": profile_key,
            "value": None if field_type == "file" else value,
            "doc_ref": doc_ref,
            "confidence": confidence,
            "explanation": explanation or "Revisión manual: elección o adjunto.",
            "sensitivity": "document" if field_type == "file" else sensitivity,
            "allowed_action": "review",
            "review_reason": reason,
        }

    if source == "resume" or doc_ref is not None:
        return {
            **base,
            "profile_key": profile_key,
            "doc_ref": doc_ref,
            "confidence": confidence,
            "explanation": explanation,
            "sensitivity": "document",
            "allowed_action": "review",
            "review_reason": "manual_file_review",
        }

    if value and confidence is not None and confidence >= 0.7:
        return {
            **base,
            "profile_key": profile_key,
            "value": value,
            "confidence": confidence,
            "explanation": explanation,
            "sensitivity": sensitivity,
            "allowed_action": "fill",
            "review_reason": None,
        }

    return {
        **base,
        "profile_key": profile_key,
        "value": value,
        "confidence": confidence,
        "explanation": explanation if profile_key else "Sin correspondencia automática.",
        "sensitivity": sensitivity,
        "allowed_action": "review",
        "review_reason": "low_confidence" if profile_key else "unmapped",
    }


def map_inventory(
    fields: list[dict[str, Any]],
    context: dict[str, Any],
    resolved_fingerprints: set[str],
) -> list[dict[str, Any]]:
    return [map_field(field, context, resolved_fingerprints) for field in fields]
