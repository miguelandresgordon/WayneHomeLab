"""Tests for wake word Mariano configuration artifacts (TDD validation suite)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
WAKE_WORD_DIR = REPO_ROOT / "infrastructure" / "voice" / "wake-word"
HA_DIR = REPO_ROOT / "home-assistant"

REQUIRED_SCRIPTS = [
    "setup_trainer_macos.sh",
    "serve_model.sh",
    "copy_model_from_trainer.sh",
    "deploy_ha_voice_config.sh",
    "flash_capture_firmware.sh",
    "flash_mariano_firmware.sh",
    "download_piper_voices_es.sh",
    "configure_ha_mariano.sh",
    "run_capture_workflow.sh",
    "train_mariano_local.sh",
    "pad_personal_samples.py",
]

MARIANO_JSON_REQUIRED_KEYS = {
    "type",
    "wake_word",
    "model",
    "version",
    "micro",
}

MARIANO_MICRO_REQUIRED_KEYS = {
    "probability_cutoff",
    "sliding_window_size",
    "feature_step_size",
    "tensor_arena_size",
    "minimum_esphome_version",
}

TV_AUTOMATION_IDS = {
    "satellite1_mute_tv_playing",
    "satellite1_unmute_tv_stopped",
}


@pytest.fixture
def automations() -> list[dict]:
    path = HA_DIR / "includes" / "automations.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def _load_ha_configuration() -> dict:
    """Parse configuration.yaml ignoring HA-specific tags (!include, !secret)."""
    path = HA_DIR / "configuration.yaml"
    text = path.read_text(encoding="utf-8")

    class HAYamlLoader(yaml.SafeLoader):
        pass

    def _include_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
        return loader.construct_scalar(node)  # type: ignore[arg-type]

    def _secret_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> str:
        return "secret-placeholder"

    HAYamlLoader.add_constructor("!include", _include_constructor)
    HAYamlLoader.add_constructor("!include_dir_merge_named", _include_constructor)
    HAYamlLoader.add_constructor("!secret", _secret_constructor)

    data = yaml.load(text, Loader=HAYamlLoader)
    assert isinstance(data, dict)
    return data


@pytest.fixture
def configuration() -> dict:
    return _load_ha_configuration()


class TestScriptsExist:
    @pytest.mark.parametrize("script_name", REQUIRED_SCRIPTS)
    def test_script_exists_and_executable(self, script_name: str) -> None:
        script = WAKE_WORD_DIR / script_name
        assert script.is_file(), f"Missing script: {script_name}"
        assert script.stat().st_mode & 0o111, f"Script not executable: {script_name}"


class TestMarianoJsonExample:
    def test_example_manifest_schema(self) -> None:
        example = WAKE_WORD_DIR / "models" / "mariano.json.example"
        data = json.loads(example.read_text(encoding="utf-8"))

        assert data["type"] == "micro"
        assert data["wake_word"] == "mariano"
        assert data["model"] == "mariano.tflite"
        assert data["version"] == 2
        assert "es" in data.get("trained_languages", [])

        missing = MARIANO_JSON_REQUIRED_KEYS - set(data.keys())
        assert not missing, f"Missing top-level keys: {missing}"

        micro = data["micro"]
        missing_micro = MARIANO_MICRO_REQUIRED_KEYS - set(micro.keys())
        assert not missing_micro, f"Missing micro keys: {missing_micro}"

        assert 0.0 < micro["probability_cutoff"] <= 1.0
        assert micro["sliding_window_size"] >= 1


class TestSatellite1Overlay:
    def test_overlay_references_mariano_model(self) -> None:
        overlay = (WAKE_WORD_DIR / "satellite1_mariano_overlay.yaml").read_text(
            encoding="utf-8"
        )
        assert "id: mariano" in overlay
        assert "probability_cutoff:" in overlay
        assert "mariano.json" in overlay
        assert "noise_suppression_level:" in overlay
        assert "auto_gain:" in overlay


class TestHomeAssistantAutomations:
    def test_tv_mute_automations_present(self, automations: list[dict]) -> None:
        ids = {a.get("id") for a in automations}
        missing = TV_AUTOMATION_IDS - ids
        assert not missing, f"Missing automation ids: {missing}"

    def test_tv_mute_targets_satellite1(self, automations: list[dict]) -> None:
        by_id = {a["id"]: a for a in automations}
        mute = by_id["satellite1_mute_tv_playing"]
        action = mute["action"][0]
        assert action["service"] == "switch.turn_on"
        assert "switch.satellite1_c7ffe4_mute" in action["target"]["entity_id"]

    def test_tv_automations_reference_media_players(self, automations: list[dict]) -> None:
        by_id = {a["id"]: a for a in automations}
        for auto_id in TV_AUTOMATION_IDS:
            trigger = by_id[auto_id]["trigger"][0]
            entities = trigger["entity_id"]
            assert "media_player.sony_bravia_4k" in entities
            assert "media_player.google_tv_streamer" in entities

    def test_modo_noche_desactivar_respects_tv_state(self, automations: list[dict]) -> None:
        by_id = {a["id"]: a for a in automations}
        desactivar = by_id["modo_noche_desactivar"]
        conditions = desactivar.get("condition", [])
        assert conditions, "modo_noche_desactivar must check TV state before unmute"
        template = conditions[0].get("value_template", "")
        assert "sony_bravia_4k" in template
        assert "google_tv_streamer" in template


class TestHomeAssistantConfiguration:
    def test_assist_pipeline_debug_enabled(self, configuration: dict) -> None:
        assist = configuration.get("assist_pipeline", {})
        assert assist.get("debug_recording_dir") == "/share/assist_pipeline"

    def test_spanish_locale(self, configuration: dict) -> None:
        ha = configuration.get("homeassistant", {})
        assert ha.get("country") == "ES"


class TestDocumentation:
    def test_runbook_exists_and_covers_workflow(self) -> None:
        doc = (REPO_ROOT / "docs" / "wake-word-mariano.md").read_text(encoding="utf-8")
        for section in (
            "Entrenar el modelo",
            "Captura de muestras",
            "probability_cutoff",
            "debug_recording_dir",
            "Automatizaciones TV",
        ):
            assert section in doc, f"Runbook missing section: {section}"


class TestGitignore:
    def test_tflite_not_committed(self) -> None:
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "mariano.json" in gitignore or "*.tflite" in gitignore
        assert ".tflite" in gitignore


class TestVoiceAssistChecklist:
    def test_voice_assist_yaml_exists(self) -> None:
        path = HA_DIR / "includes" / "voice_assist.yaml"
        text = path.read_text(encoding="utf-8")
        assert "openai_whisper_cloud" in text
        assert "whisper-large-v3-turbo" in text
        assert "Mariano" in text
        assert "probability_cutoff" in text


class TestCaptureWorkflow:
    def test_run_capture_workflow_check_exits_zero(self) -> None:
        import subprocess

        result = subprocess.run(
            [str(WAKE_WORD_DIR / "run_capture_workflow.sh"), "check"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        assert "personal_samples" in result.stdout


class TestPiperVoicesDownload:
    def test_spanish_voices_present_in_trainer(self) -> None:
        trainer_voices = (
            Path.home()
            / "Proyectos"
            / "microWakeWord-Trainer-AppleSilicon"
            / "piper-sample-generator"
            / "voices"
        )
        if not trainer_voices.exists():
            pytest.skip("Trainer voices dir not present on this machine")
        es_voices = list(trainer_voices.glob("es_*.onnx"))
        assert len(es_voices) >= 1, "At least one Spanish Piper voice required for training"


class TestTrainedModelWhenPresent:
    """Optional integration checks once training completes."""

    def test_trained_artifacts_if_copied(self) -> None:
        models_dir = WAKE_WORD_DIR / "models"
        json_path = models_dir / "mariano.json"
        tflite_path = models_dir / "mariano.tflite"

        if not json_path.exists():
            pytest.skip("mariano.json not yet copied from trainer")

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["wake_word"] == "mariano"
        assert tflite_path.is_file(), "mariano.tflite must accompany mariano.json"
        assert tflite_path.stat().st_size > 1000, "tflite file looks too small"
