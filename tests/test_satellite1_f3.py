"""F3: Satellite1 firmware (OTA #1) + HA meeting mode + playback-aware sensitivity."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HA = REPO / "home-assistant"
WW = REPO / "infrastructure" / "voice" / "wake-word"
FW = WW / "esphome" / "satellite1-c7ffe4.yaml"
PINNED = "9814bf5"  # staging commit the running firmware was built from (2026-09-10)


class _Loader(yaml.SafeLoader):
    pass


for tag in ("!secret", "!lambda", "!extend", "!include"):
    _Loader.add_constructor(tag, lambda l, n: l.construct_scalar(n))


def _fw() -> dict:
    return yaml.load(FW.read_text(encoding="utf-8"), Loader=_Loader)


# --------------------------- firmware --------------------------------------
def test_firmware_pinned_to_running_commit_not_moving_staging() -> None:
    pkg = _fw()["packages"]["FutureProofHomes.Satellite1"]
    assert str(pkg["ref"]).startswith(PINNED), pkg["ref"]
    assert "refresh" not in pkg or str(pkg["refresh"]) in {"0s", "never"}


def test_ltr_als_log_spam_silenced() -> None:
    assert _fw()["logger"]["logs"]["ltr_als_ps"] == "ERROR"


def test_mic_level_sensor_exposed() -> None:
    text = FW.read_text(encoding="utf-8")
    assert "id: !extend sat1_mics" in text and "on_data:" in text
    sensors = _fw()["sensor"]
    lvl = next(s for s in sensors if s.get("id") == "mic_level")
    assert lvl["unit_of_measurement"] == "dBFS"
    assert lvl["update_interval"] == "2s"


def test_wake_word_switch_keeps_microphone_running() -> None:
    sw = next(s for s in _fw()["switch"] if s.get("id") == "wake_word_enabled")
    blob = yaml.dump(sw)
    assert "micro_wake_word.disable_model" in blob and "micro_wake_word.enable_model" in blob
    assert "micro_wake_word.stop" not in blob  # stopping mww would stop the mic level too
    assert sw["restore_mode"] == "RESTORE_DEFAULT_ON"


def test_firmware_validator_passes() -> None:
    res = subprocess.run([sys.executable, str(WW / "validate_satellite1_firmware.py")], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_last_good_firmware_yaml_kept() -> None:
    last_good = WW / "esphome" / "satellite1-c7ffe4.last-good.yaml"
    assert last_good.is_file()
    assert "ref: &repo_ref staging" in last_good.read_text(encoding="utf-8")


# --------------------------- meeting mode -----------------------------------
def _pkg(name: str) -> dict:
    return yaml.safe_load((HA / "packages" / name).read_text(encoding="utf-8"))


def _auto(pkg: dict, aid: str) -> dict:
    return next(a for a in pkg["automation"] if a["id"] == aid)


def test_meeting_mode_helpers() -> None:
    p = _pkg("modo_reunion.yaml")
    assert "modo_reunion" in p["input_boolean"]
    assert p["timer"]["modo_reunion"]["duration"] == "02:00:00"


def test_meeting_on_disables_wake_word_starts_timer_and_led() -> None:
    blob = yaml.dump(_auto(_pkg("modo_reunion.yaml"), "modo_reunion_on"), allow_unicode=True)
    assert "switch.satellite1_c7ffe4_wake_word_activo" in blob and "switch.turn_off" in blob
    assert "timer.start" in blob
    assert "light.satellite1_c7ffe4_led_ring" in blob


def test_meeting_off_restores_wake_word() -> None:
    blob = yaml.dump(_auto(_pkg("modo_reunion.yaml"), "modo_reunion_off"), allow_unicode=True)
    assert "switch.turn_on" in blob and "switch.satellite1_c7ffe4_wake_word_activo" in blob
    assert "timer.cancel" in blob


def test_exits_by_timer_button_and_silence() -> None:
    p = _pkg("modo_reunion.yaml")
    assert "timer.finished" in yaml.dump(_auto(p, "modo_reunion_fin_temporizador"))
    btn = yaml.dump(_auto(p, "modo_reunion_boton"))
    assert "event.satellite1_c7ffe4_action_button_press" in btn and "double_press" in btn
    sil = yaml.dump(_auto(p, "modo_reunion_silencio"))
    assert "sensor.satellite1_c7ffe4_mic_level" in sil and "below" in sil and "00:10:00" in sil


def test_auto_entry_has_hysteresis_and_tv_guard() -> None:
    a = _auto(_pkg("modo_reunion.yaml"), "modo_reunion_auto")
    blob = yaml.dump(a, allow_unicode=True)
    assert "sensor.satellite1_c7ffe4_mic_level" in blob and "above" in blob
    assert "for:" in blob  # sustained, not a spike
    for tv in ("media_player.tv_ga_2", "media_player.bravia_kd_43xf8596"):
        assert tv in blob
    # not while the Satellite itself is playing radio/music
    assert "media_player.satellite1" in blob
    entry = [t for t in a["triggers"] if "above" in t][0]["above"]
    exit_ = [t for t in _auto(_pkg("modo_reunion.yaml"), "modo_reunion_silencio")["triggers"] if "below" in t][0]["below"]
    assert entry - exit_ >= 10  # dB hysteresis


def test_meeting_voice_phrases() -> None:
    sys.path.insert(0, str(REPO / "tests" / "assist"))
    from conftest import load_custom_intents
    from hassil import recognize_best

    intents = load_custom_intents()
    for text, intent in [
        ("activa el modo reunión", "ModoReunionOn"),
        ("modo reunión", "ModoReunionOn"),
        ("desactiva el modo reunión", "ModoReunionOff"),
        ("quita el modo reunión", "ModoReunionOff"),
    ]:
        r = recognize_best(text, intents, language="es")
        assert r is not None and r.intent.name == intent, text


# --------------------------- playback-aware sensitivity ---------------------
def test_sensitivity_follows_tv_and_own_playback() -> None:
    autos = yaml.safe_load((HA / "includes" / "automations.yaml").read_text(encoding="utf-8"))
    a = next(x for x in autos if x["id"] == "satellite1_tv_wake_word_sensitivity")
    blob = yaml.dump(a, allow_unicode=True)
    for e in ("media_player.satellite1", "media_player.satellite1_c7ffe4_media_player"):
        assert e in blob
    assert "Very sensitive" in blob and "Slightly sensitive" in blob and "Moderately sensitive" in blob
