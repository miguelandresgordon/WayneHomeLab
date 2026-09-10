"""Tests for wake word Mariano configuration artifacts (TDD validation suite)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
WAKE_WORD_DIR = REPO_ROOT / "infrastructure" / "voice" / "wake-word"
HA_DIR = REPO_ROOT / "home-assistant"
sys.path.insert(0, str(WAKE_WORD_DIR))
sys.path.insert(0, str(WAKE_WORD_DIR))

REQUIRED_SCRIPTS = [
    "setup_trainer_macos.sh",
    "serve_model.sh",
    "copy_model_from_trainer.sh",
    "deploy_ha_voice_config.sh",
    "flash_capture_firmware.sh",
    "flash_mariano_firmware.sh",
    "download_piper_voices_es.sh",
    "configure_ha_mariano.sh",
    "configure_ha_voice_nlu.sh",
    "run_capture_workflow.sh",
    "train_mariano_local.sh",
    "pad_personal_samples.py",
    "validate_satellite1_firmware.py",
    "sync_satellite1_api_secret.sh",
    "pack_satellite1_usb.sh",
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

class TestHomeAssistantAutomations:
    def test_automations_yaml_is_empty(self, automations: list[dict]) -> None:
        assert automations == []

    def test_no_automatic_satellite1_or_lifestyle_ids(self) -> None:
        text = (HA_DIR / "includes" / "automations.yaml").read_text(encoding="utf-8")
        for needle in (
            "satellite1_mute_tv_playing",
            "satellite1_unmute_tv_stopped",
            "satellite1_tv_strict_sensitivity",
            "satellite1_wake_word_mariano",
            "satellite1_action_button",
            "speaker_id_on_command",
            "modo_noche_activar",
            "cine_tv_ga_on",
        ):
            assert needle not in text, f"Automation {needle} must not remain in YAML"


@pytest.fixture
def automations() -> list[dict]:
    path = HA_DIR / "includes" / "automations.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def _load_yaml_with_ha_tags(path: Path) -> dict:
    """Parse HA YAML ignoring tags (!include, !secret)."""
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


def _load_ha_configuration() -> dict:
    """Parse configuration.yaml ignoring HA-specific tags (!include, !secret)."""
    return _load_yaml_with_ha_tags(HA_DIR / "configuration.yaml")


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
        assert "id(mariano)" in overlay
        assert "probability_cutoff:" in overlay
        assert "mariano.esphome.json" in overlay
        assert "noise_suppression_level:" in overlay
        assert "auto_gain:" in overlay
        assert "voice_assistant:" in overlay
        assert "esphome.satellite1_stt_end" in overlay
        assert "set_probability_cutoff(250)" in overlay
        va_block = overlay.split("voice_assistant:", 1)[1].split("select:", 1)[0]
        assert "id: !extend" not in va_block
        assert "id: va" in va_block


class TestHomeAssistantConfiguration:
    def test_assist_pipeline_debug_enabled(self, configuration: dict) -> None:
        assist = configuration.get("assist_pipeline", {})
        assert assist.get("debug_recording_dir") == "/share/assist_pipeline"

    def test_spanish_locale(self, configuration: dict) -> None:
        ha = configuration.get("homeassistant", {})
        assert ha.get("country") == "ES"

    def test_uses_includes_subdir_and_modern_template(self, configuration: dict) -> None:
        assert configuration.get("template") == "includes/sensors.yaml"
        assert configuration.get("intent_script") == "includes/intent_scripts.yaml"
        assert configuration.get("script") == "includes/scripts.yaml"
        assert "http" not in configuration


class TestHaosConfiguration:
    """configuration.haos.yaml is what deploy scripts copy to /config/configuration.yaml."""

    def test_haos_includes_layout_matches_repo(self) -> None:
        path = HA_DIR / "configuration.haos.yaml"
        text = path.read_text(encoding="utf-8")
        data = _load_yaml_with_ha_tags(path)
        assert data.get("template") == "includes/sensors.yaml"
        assert data.get("intent_script") == "includes/intent_scripts.yaml"
        assert data.get("automation") == "includes/automations.yaml"
        assert "http" not in data
        assert "!include automations.yaml" not in text
        assert "includes/sensors.yaml" in text
        assert "includes/intent_scripts.yaml" in text

    def test_haos_assist_logger_info(self) -> None:
        text = (HA_DIR / "configuration.haos.yaml").read_text(encoding="utf-8")
        assert "homeassistant.components.assist_pipeline: info" in text
        assert "homeassistant.components.conversation: info" in text

    def test_deploy_script_copies_includes_subdir(self) -> None:
        script = (
            REPO_ROOT
            / "infrastructure"
            / "voice"
            / "speaker-id"
            / "deploy_speaker_id_ha_config.sh"
        )
        text = script.read_text(encoding="utf-8")
        assert "sensors.yaml" in text
        assert "intent_scripts.yaml" in text
        assert "${HA_CONFIG}/includes/${f}" in text
        assert "${HA_CONFIG}/automations.yaml" not in text

    def test_deploy_ha_voice_copies_custom_sentences(self) -> None:
        script = WAKE_WORD_DIR / "deploy_ha_voice_config.sh"
        text = script.read_text(encoding="utf-8")
        assert "custom_sentences/es" in text
        assert "luces.yaml" in text or "*.yaml" in text
        assert "configure_ha_voice_nlu.sh" in text


class TestVoiceNlu:
    def test_luces_sentences_pin_intents(self) -> None:
        path = HA_DIR / "custom_sentences" / "es" / "luces.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        intents = data["intents"]
        for name in ("EnciendeLaLampara", "ApagaLaLampara", "ToggleLaLampara"):
            assert name in intents
            sentences = intents[name]["data"][0]["sentences"]
            blob = " ".join(sentences)
            assert "lámpara" in blob or "lampara" in blob
            assert "dormitorio" not in blob

    def test_intent_scripts_pin_xiaomi_lamp(self) -> None:
        data = yaml.safe_load(
            (HA_DIR / "includes" / "intent_scripts.yaml").read_text(encoding="utf-8")
        )
        for name in ("EnciendeLaLampara", "ApagaLaLampara", "ToggleLaLampara"):
            blob = yaml.dump(data[name])
            assert "light.yeelink_mono6_6409_light" in blob
            assert "scene.lampara_apagada" not in blob

    def test_scene_renamed_salon_off(self) -> None:
        scenes = yaml.safe_load((HA_DIR / "includes" / "scenes.yaml").read_text(encoding="utf-8"))
        by_id = {s["id"]: s for s in scenes}
        assert by_id["lampara_apagada"]["name"] == "Salón off"
        assert by_id["lampara_apagada"]["name"] != "Lámpara apagada"

    def test_last_stt_text_helper(self) -> None:
        data = yaml.safe_load((HA_DIR / "includes" / "input_text.yaml").read_text(encoding="utf-8"))
        assert "last_stt_text" in data
        assert data["last_stt_text"]["max"] == 255

    def test_purge_keeps_24h_or_30_files(self) -> None:
        text = (HA_DIR / "includes" / "shell_commands.yaml").read_text(encoding="utf-8")
        assert "1440" in text
        assert "30" in text
        assert "-mmin +15" not in text

    def test_no_lifestyle_scripts(self) -> None:
        scripts = yaml.safe_load((HA_DIR / "includes" / "scripts.yaml").read_text(encoding="utf-8"))
        forbidden = {
            "buenas_noches",
            "buenos_dias",
            "relajado",
            "cine",
            "salir_cine",
            "me_voy",
            "he_llegado",
        }
        assert not (set(scripts) & forbidden), f"Unexpected lifestyle scripts: {set(scripts) & forbidden}"
        for keep in ("poner_radio", "parar_radio", "apagar_tele", "encender_tele"):
            assert keep in scripts

    def test_esphome_yaml_extends_mariano_lambda(self) -> None:
        text = (WAKE_WORD_DIR / "esphome" / "satellite1-c7ffe4.yaml").read_text(encoding="utf-8")
        assert "id(mariano)" in text
        assert "voice_assistant:" in text
        assert "esphome.satellite1_stt_end" in text
        assert "id: !extend va" not in text
        assert "id: va" in text
        assert "key: !secret api_encryption_key" in text
        assert "REPLACE_BY_32_BIT_RANDOM_KEY" not in text
        example = (WAKE_WORD_DIR / "esphome" / "secrets.yaml.example").read_text(encoding="utf-8")
        assert "api_encryption_key:" in example

    def test_firmware_validator_accepts_repo_yaml(self) -> None:
        from validate_satellite1_firmware import validate_firmware_yaml

        for rel in (
            WAKE_WORD_DIR / "esphome" / "satellite1-c7ffe4.yaml",
            WAKE_WORD_DIR / "satellite1_mariano_overlay.yaml",
        ):
            errors = validate_firmware_yaml(rel)
            assert not errors, errors

    def test_firmware_validator_rejects_extend_on_voice_assistant(self, tmp_path) -> None:
        from validate_satellite1_firmware import validate_firmware_yaml

        bad = tmp_path / "bad.yaml"
        bad.write_text(
            (WAKE_WORD_DIR / "esphome" / "satellite1-c7ffe4.yaml")
            .read_text(encoding="utf-8")
            .replace("  id: va\n", "  id: !extend va\n", 1),
            encoding="utf-8",
        )
        errors = validate_firmware_yaml(bad)
        assert any("!extend" in e for e in errors)


class TestDocumentation:
    def test_runbook_exists_and_covers_workflow(self) -> None:
        doc = (REPO_ROOT / "docs" / "wake-word-mariano.md").read_text(encoding="utf-8")
        for section in (
            "Entrenar el modelo",
            "Captura de muestras",
            "probability_cutoff",
            "debug_recording_dir",
            "Automatizaciones HA",
            "mute_microphones",
            "whisper-large-v3",
            "RequiresEncryptionAPIError",
            "Bootloader too old",
        ):
            assert section in doc, f"Runbook missing section: {section}"


class TestGitignore:
    def test_tflite_not_committed(self) -> None:
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "mariano.json" in gitignore or "*.tflite" in gitignore
        assert ".tflite" in gitignore
        assert "infrastructure/voice/wake-word/esphome/secrets.yaml" in gitignore


class TestVoiceAssistChecklist:
    def test_voice_assist_yaml_exists(self) -> None:
        path = HA_DIR / "includes" / "voice_assist.yaml"
        text = path.read_text(encoding="utf-8")
        assert "openai_whisper_cloud" in text
        assert "whisper-large-v3" in text
        assert "whisper-large-v3-turbo" not in text
        assert "Mariano" in text
        assert "probability_cutoff" in text
        assert "relaxed" in text
        assert "mute_microphones" in text
        assert "luces.yaml" in text


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
        assert data["wake_word"].casefold() == "mariano"
        assert tflite_path.is_file(), "mariano.tflite must accompany mariano.json"
        assert tflite_path.stat().st_size > 1000, "tflite file looks too small"
