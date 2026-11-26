"""wayne_default: complete flat dark theme (X/Revolut + docs/design-refs) with local fonts."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HA = REPO / "home-assistant"
THEME_FILE = HA / "themes" / "wayne_default.yaml"
WWW = HA / "www" / "wayne"


def _theme() -> dict:
    data = yaml.safe_load(THEME_FILE.read_text(encoding="utf-8"))
    assert list(data) == ["wayne_default"]
    return data["wayne_default"]


def _hex_luma(value: str) -> float:
    h = value.strip().lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_theme_is_complete() -> None:
    t = _theme()
    required = {
        "primary-background-color", "secondary-background-color", "card-background-color",
        "primary-text-color", "secondary-text-color", "primary-color", "accent-color",
        "divider-color", "ha-card-border-radius", "ha-card-border-width", "ha-card-border-color",
        "ha-card-box-shadow", "app-header-background-color", "sidebar-background-color",
        "success-color", "warning-color", "error-color", "state-icon-color",
        "ha-font-family-body", "code-font-family",
    }
    missing = required - set(t)
    assert not missing, sorted(missing)
    assert len(t) >= 40


def test_near_black_background_and_flat_cards() -> None:
    t = _theme()
    assert _hex_luma(t["primary-background-color"]) < 12
    assert re.fullmatch(r"[0-2]px", str(t["ha-card-border-radius"]))
    assert str(t["ha-card-border-width"]) == "1px"
    assert str(t["ha-card-box-shadow"]) == "none"


def test_no_gradients_glows_or_pills() -> None:
    blob = THEME_FILE.read_text(encoding="utf-8").lower()
    assert "gradient" not in blob
    assert "blur" not in blob
    for k, v in _theme().items():
        if "radius" in k:
            assert int(re.sub(r"[^0-9]", "", str(v)) or 0) <= 4, (k, v)


def test_status_colours_are_green_amber_red() -> None:
    t = _theme()
    assert t["success-color"].lower() != t["error-color"].lower()
    for key in ("success-color", "warning-color", "error-color", "primary-color"):
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", t[key]), key


def test_fonts_are_local_with_license() -> None:
    fonts = list((WWW / "fonts").glob("*.woff2"))
    assert len(fonts) >= 3
    assert (WWW / "fonts" / "OFL.txt").is_file()
    loader = (WWW / "wayne-fonts.js").read_text(encoding="utf-8")
    assert "http://" not in loader and "https://" not in loader
    for f in fonts:
        assert f"/local/wayne/fonts/{f.name}" in loader, f.name


def test_theme_uses_the_local_fonts() -> None:
    t = _theme()
    assert "JetBrains Mono" in t["code-font-family"]
    assert "Inter" in t["ha-font-family-body"] or "JetBrains Mono" in t["ha-font-family-body"]


def test_font_loader_registered_globally() -> None:
    conf = (HA / "configuration.haos.yaml").read_text(encoding="utf-8")
    assert "extra_module_url" in conf
    assert "/local/wayne/wayne-fonts.js" in conf
