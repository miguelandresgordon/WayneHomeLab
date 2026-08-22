"""Tests for keep-personal cleanup and Windows/AMD CPU trainer path."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
WAKE_WORD_DIR = REPO_ROOT / "infrastructure" / "voice" / "wake-word"
DOCS = REPO_ROOT / "docs" / "wake-word-mariano.md"
AGENTS = REPO_ROOT / "AGENTS.md"

REQUIRED_POSIX_SCRIPTS = [
    "export_personal_samples.sh",
    "free_trainer_disk.sh",
    "setup_trainer_nvidia.sh",
    "train_mariano_nvidia.sh",
    "copy_model_from_trainer.sh",
]

REQUIRED_WINDOWS_SCRIPTS = [
    "setup_trainer_windows.ps1",
    "train_mariano_windows.ps1",
    "probe_trainer_windows.ps1",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestRequiredTrainerScripts:
    @pytest.mark.parametrize("script_name", REQUIRED_POSIX_SCRIPTS)
    def test_posix_script_exists_and_executable(self, script_name: str) -> None:
        script = WAKE_WORD_DIR / script_name
        assert script.is_file(), f"Missing script: {script_name}"
        assert script.stat().st_mode & 0o111, f"Script not executable: {script_name}"

    @pytest.mark.parametrize("script_name", REQUIRED_WINDOWS_SCRIPTS)
    def test_windows_script_exists(self, script_name: str) -> None:
        script = WAKE_WORD_DIR / script_name
        assert script.is_file(), f"Missing Windows script: {script_name}"


class TestCpuTrainerPath:
    def test_nvidia_setup_help_mentions_cpu(self) -> None:
        text = _read(WAKE_WORD_DIR / "setup_trainer_nvidia.sh")
        assert "--cpu" in text
        assert "--gpus all" in text

    def test_nvidia_train_accepts_cpu_flag(self) -> None:
        text = _read(WAKE_WORD_DIR / "train_mariano_nvidia.sh")
        assert "--cpu" in text

    def test_windows_setup_has_cpu_switch_and_amd_guard(self) -> None:
        text = _read(WAKE_WORD_DIR / "setup_trainer_windows.ps1")
        assert "[switch]$Cpu" in text
        assert "--gpus all" in text
        assert "Radeon" in text or "AMD" in text
        assert "6750" in text or "CUDA" in text

    def test_windows_train_passes_cpu_switch(self) -> None:
        text = _read(WAKE_WORD_DIR / "train_mariano_windows.ps1")
        assert "[switch]$Cpu" in text
        assert "-Cpu" in text

    def test_probe_script_detects_gpu_and_ram(self) -> None:
        text = _read(WAKE_WORD_DIR / "probe_trainer_windows.ps1")
        assert "Win32_VideoController" in text
        assert "nvidia-smi" in text
        assert "cpu" in text.lower()
        assert "Radeon" in text or "AMD" in text


class TestCopyModelLooksAtWindowsDataDir:
    def test_copy_model_includes_mww_data_candidate(self) -> None:
        text = _read(WAKE_WORD_DIR / "copy_model_from_trainer.sh")
        assert "mww-data" in text
        assert "MWW_NVIDIA_DATA_DIR" in text or "MWW_TRAINER_DATA_DIR" in text


class TestKeepPersonalCleanup:
    def test_free_trainer_disk_keep_personal_lists_generated_dirs(self) -> None:
        text = _read(WAKE_WORD_DIR / "free_trainer_disk.sh")
        for name in (
            "generated_samples",
            "generated_augmented_features",
            "personal_augmented_features",
            "piper-sample-generator",
            "tts-envs",
            "negative_datasets",
        ):
            assert name in text, f"keep-personal should delete {name}"
        assert "personal_samples" in text
        assert "--keep-personal" in text


class TestRunbookAndAgentsHardware:
    def test_runbook_documents_amd_cpu_path(self) -> None:
        text = _read(DOCS)
        assert "RX 6750 XT" in text
        assert "-Cpu" in text or "--cpu" in text
        assert "CUDA" in text
        assert "personal_samples" in text
        assert "probe_trainer_windows.ps1" in text

    def test_agents_documents_training_pc(self) -> None:
        text = _read(AGENTS)
        assert "RX 6750 XT" in text
        assert "Windows 11" in text
        assert "setup_trainer_windows.ps1" in text
        assert "free_trainer_disk.sh --keep-personal" in text
        assert "CUDA" in text
