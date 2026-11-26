"""F4: speaker-id add-on wired for real + enrollment tooling for alicia/miguel."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HA = REPO / "home-assistant"
SPK = REPO / "infrastructure" / "voice" / "speaker-id"
sys.path.insert(0, str(SPK))


def _pkg() -> dict:
    return yaml.safe_load((HA / "packages" / "speaker_id.yaml").read_text(encoding="utf-8"))


def _automation() -> dict:
    autos = _pkg()["automation"]
    assert len(autos) == 1
    return autos[0]


def test_triggered_by_folder_watcher_on_closed_wav() -> None:
    a = _automation()
    trig = a["triggers"][0]
    assert trig["trigger"] == "event"
    assert trig["event_type"] == "folder_watcher"
    assert trig["event_data"]["event_type"] == "closed"
    blob = yaml.dump(a)
    assert ".wav" in blob


def test_calls_identify_and_updates_current_speaker_and_fires_event() -> None:
    blob = yaml.dump(_automation(), allow_unicode=True)
    assert "rest_command.identify_speaker" in blob
    assert "response_variable" in blob
    assert "input_text.set_value" in blob and "input_text.current_speaker" in blob
    assert "event: speaker_identified" in blob or "event: speaker_identified\n" in blob
    for key in ("person", "score", "is_known", "path"):
        assert key in blob


def test_queued_and_never_breaks_the_pipeline() -> None:
    a = _automation()
    assert a["mode"] in {"queued", "parallel"}
    assert "continue_on_error: true" in yaml.dump(a)


def test_no_per_speaker_behaviour_added() -> None:
    # Only identification; no notifications or speaker-specific actions.
    blob = yaml.dump(_pkg(), allow_unicode=True)
    assert "notify." not in blob


def test_collect_satellite_samples_picks_new_wavs_only(tmp_path: Path) -> None:
    import collect_satellite_samples as css

    root = tmp_path / "pipe"
    for i, t in enumerate((100, 200, 300)):
        d = root / f"run{i}"
        d.mkdir(parents=True)
        f = d / "01_stt-stt.groqcloud_whisper.wav"
        f.write_bytes(b"RIFF" + b"\0" * 40000)
        os.utime(f, (t, t))
    picked = css.select_wavs(root, since=150, limit=10)
    assert [p.parent.name for p in picked] == ["run1", "run2"]


def test_enroll_script_chains_collect_train_validate_deploy_reload() -> None:
    text = (SPK / "enroll_speaker.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    order = ["collect_satellite_samples.py", "train_profiles.py", "validate_profiles.py", "deploy_to_haos.sh", "/reload"]
    pos = [text.index(x) for x in order]
    assert pos == sorted(pos)


def test_enrollment_script_lists_real_daily_commands() -> None:
    guion = (SPK / "guion_enrolado.md").read_text(encoding="utf-8")
    for needle in ("alicia", "miguel", "Pon la SER", "Enciende la lámpara", "Apaga la tele"):
        assert needle.lower() in guion.lower(), needle
