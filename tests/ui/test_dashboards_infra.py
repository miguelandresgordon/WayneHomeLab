"""F5 shared UI infra: 3 YAML dashboards in the sidebar + pinned local apexcharts."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
HA = REPO / "home-assistant"


class _L(yaml.SafeLoader):
    pass


for _t in ("!include", "!include_dir_named", "!include_dir_merge_named", "!secret"):
    _L.add_constructor(_t, lambda l, n: l.construct_scalar(n))


def _conf() -> dict:
    return yaml.load((HA / "configuration.haos.yaml").read_text(encoding="utf-8"), Loader=_L)


def test_three_yaml_dashboards_with_sidebar_icons() -> None:
    dashes = _conf()["lovelace"]["dashboards"]
    assert set(dashes) == {"wayne-casa", "wayne-tiempo", "wayne-mariano"}
    for key, d in dashes.items():
        assert d["mode"] == "yaml"
        assert d["show_in_sidebar"] is True
        assert d["icon"].startswith("mdi:")
        assert (HA / d["filename"]).is_file(), d["filename"]
        assert d.get("require_admin", False) is False  # Alicia (no admin) must see them


def test_dashboards_use_the_theme() -> None:
    for f in (HA / "dashboards").glob("*.yaml"):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        for view in data["views"]:
            assert view.get("theme") == "wayne_default", f.name


def test_apexcharts_pinned_and_loaded_locally() -> None:
    sh = (REPO / "infrastructure" / "ha" / "fetch_frontend_vendor.sh").read_text(encoding="utf-8")
    assert "v2.2.3" in sh
    assert "c2b3c" in sh or "sha256" in sh.lower()
    assert "shasum -a 256" in sh or "sha256sum" in sh
    conf = (HA / "configuration.haos.yaml").read_text(encoding="utf-8")
    assert "/local/wayne/vendor/apexcharts-card.js" in conf
    gi = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "home-assistant/www/wayne/vendor/" in gi
