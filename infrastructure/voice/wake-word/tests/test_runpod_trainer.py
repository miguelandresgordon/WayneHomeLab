"""Tests for RunPod GPU Pod trainer path (Mariano)."""

from __future__ import annotations

import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
WAKE_WORD_DIR = REPO_ROOT / "infrastructure" / "voice" / "wake-word"
DOCS = REPO_ROOT / "docs" / "wake-word-mariano.md"
AGENTS = REPO_ROOT / "AGENTS.md"

SETUP = WAKE_WORD_DIR / "setup_trainer_runpod.sh"
TRAIN = WAKE_WORD_DIR / "train_mariano_runpod.sh"
TEARDOWN = WAKE_WORD_DIR / "teardown_runpod_trainer.sh"
COPY_MODEL = WAKE_WORD_DIR / "copy_model_from_trainer.sh"
RUNPOD_GUIDE = REPO_ROOT / "docs" / "runpod-train-mariano.md"
RUNPOD_MOBILE_GUIDE = REPO_ROOT / "docs" / "runpod-train-mariano-movil.md"

RUNPOD_SCRIPTS = [
    "setup_trainer_runpod.sh",
    "train_mariano_runpod.sh",
    "teardown_runpod_trainer.sh",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _to_bash_path(path: Path | str) -> str:
    """Windows Path → path that WSL/Git bash can open (avoid backslash escapes)."""
    resolved = Path(path).resolve()
    posix = resolved.as_posix()
    if os.name == "nt" and len(posix) >= 2 and posix[1] == ":":
        return f"/mnt/{posix[0].lower()}{posix[2:]}"
    return posix


def _run(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    script_path = _to_bash_path(script)
    extra: dict[str, str] = {}
    if env:
        for key, value in env.items():
            if key.startswith("MWW_") and (":" in value or "\\" in value or value.startswith("/")):
                extra[key] = _to_bash_path(value) if ":" in value or "\\" in value else value
            else:
                extra[key] = value
    if extra:
        assignments = " ".join(f"{k}={shlex.quote(v)}" for k, v in extra.items())
        argv = " ".join(shlex.quote(a) for a in args)
        inner = f"{assignments} exec {shlex.quote(script_path)} {argv}".rstrip()
        cmd = ["bash", "-c", inner]
    else:
        cmd = ["bash", script_path, *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(WAKE_WORD_DIR),
        check=False,
        timeout=60,
    )


class TestRunpodScriptsExist:
    @pytest.mark.parametrize("script_name", RUNPOD_SCRIPTS)
    def test_posix_script_exists_and_executable(self, script_name: str) -> None:
        script = WAKE_WORD_DIR / script_name
        assert script.is_file(), f"Missing script: {script_name}"
        if os.name == "nt":
            return
        mode = script.stat().st_mode
        assert mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH), (
            f"Script not executable: {script_name}"
        )


class TestSetupTrainerRunpod:
    def test_help_mentions_dry_run_and_omits_cpu_flag(self) -> None:
        result = _run(SETUP, "--help")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "--dry-run" in out
        assert "--help" in out or "-h" in out
        assert "--cpu" not in out
        assert "Spot" in out or "spot" in out.lower()

    def test_unknown_arg_fails(self) -> None:
        result = _run(SETUP, "--cpu")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "Uso:" in combined or "ERROR" in combined

    def test_dry_run_prints_tater_image_data_mount_and_stop_after(self) -> None:
        result = _run(SETUP, "--dry-run")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "ghcr.io/tatertotterson/microwakeword" in out
        assert "/data" in out
        assert "--stop-after" in out
        assert "COMMUNITY" in out or "Community" in out
        assert "8789" in out
        assert "personal_samples" in out
        assert "runpodctl" in out
        assert "--spot" not in out.lower()
        assert "pod create" in out or "Pod" in out

    def test_dry_run_does_not_create_a_pod(self) -> None:
        result = _run(SETUP, "--dry-run")
        assert result.returncode == 0, result.stderr
        out = result.stdout.lower()
        assert "dry-run" in out
        assert "no se ha creado" in out or "no crea" in out or "no se crea" in out


class TestTrainMarianoRunpod:
    def test_help_mentions_samples_and_omits_cpu_flag(self) -> None:
        result = _run(TRAIN, "--help")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "--dry-run" in out
        assert "personal_samples" in out
        assert "--cpu" not in out
        assert "mariano" in out.lower()

    def test_dry_run_documents_send_and_cli_train(self) -> None:
        result = _run(TRAIN, "--dry-run")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "runpodctl send" in out
        assert "train_wake_word" in out
        assert "Spanish" in out
        assert "mariano" in out
        assert "personal_samples" in out
        assert "tmux" in out or "nohup" in out

    def test_dry_run_syncs_wav_count_from_personal_src(
        self, tmp_path: Path
    ) -> None:
        src = tmp_path / "personal_samples"
        src.mkdir()
        (src / "clip.wav").write_bytes(b"RIFF")
        result = _run(
            TRAIN,
            "--dry-run",
            env={"MWW_PERSONAL_SRC": src.as_posix()},
        )
        assert result.returncode == 0, result.stderr
        assert "1 WAV" in result.stdout or "1 wav" in result.stdout.lower()


class TestTeardownRunpodTrainer:
    def test_help_mentions_flags_and_omits_cpu(self) -> None:
        result = _run(TEARDOWN, "--help")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "--dry-run" in out
        assert "--delete-volume" in out
        assert "--watch" in out
        assert "--cpu" not in out

    def test_unknown_arg_fails(self) -> None:
        result = _run(TEARDOWN, "--cpu")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "Uso:" in combined or "ERROR" in combined

    def test_dry_run_prints_receive_and_stop_without_volume_delete(self) -> None:
        result = _run(TEARDOWN, "--dry-run")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "pod stop" in out
        assert "receive" in out or "scp" in out
        assert "/data/trained_wake_words" in out
        assert "copy_model_from_trainer.sh" in out
        lower = out.lower()
        assert "network-volume delete" not in lower or "omit" in lower
        if "network-volume delete" in lower:
            assert "omit" in lower or "no se borra" in lower or "--delete-volume" in out

    def test_dry_run_delete_volume_prints_network_volume_delete(self) -> None:
        result = _run(
            TEARDOWN,
            "--dry-run",
            "--delete-volume",
            env={"MWW_RUNPOD_VOLUME_ID": "vol-test"},
        )
        assert result.returncode == 0, result.stderr
        assert "network-volume delete" in result.stdout
        assert "vol-test" in result.stdout

    def test_delete_volume_without_volume_id_fails(self) -> None:
        result = _run(
            TEARDOWN,
            "--delete-volume",
            env={"MWW_RUNPOD_VOLUME_ID": "", "MWW_RUNPOD_POD_ID": "pod-test"},
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "VOLUME" in combined or "volume" in combined.lower()

    def test_dry_run_watch_mentions_wait(self) -> None:
        result = _run(TEARDOWN, "--dry-run", "--watch")
        assert result.returncode == 0, result.stderr
        out = result.stdout.lower()
        assert "watch" in out or "espera" in out or "artefacto" in out
        assert "60" in result.stdout or "poll" in out or "intervalo" in out

    def test_missing_local_artifacts_does_not_stop_pod(self, tmp_path: Path) -> None:
        dest = tmp_path / "mww-runpod"
        result = _run(
            TEARDOWN,
            env={
                "MWW_RUNPOD_POD_ID": "pod-test",
                "MWW_RUNPOD_DATA_DIR": dest.as_posix(),
            },
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "pod stop" not in combined or "no" in combined.lower()
        assert "tflite" in combined.lower() or "artefacto" in combined.lower()

    def test_zsh_help_and_dry_run(self) -> None:
        zsh = shutil.which("zsh")
        if zsh is None:
            pytest.skip("zsh no está en PATH (sí en macOS Tahoe)")
        script = _to_bash_path(TEARDOWN)
        help_r = subprocess.run(
            [zsh, script, "--help"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert help_r.returncode == 0, help_r.stderr
        assert "--dry-run" in help_r.stdout
        dry = subprocess.run(
            [zsh, script, "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert dry.returncode == 0, dry.stderr
        assert "pod stop" in dry.stdout
        assert "copy_model_from_trainer.sh" in dry.stdout


class TestCopyModelLooksAtRunpodDownload:
    def test_copy_model_includes_runpod_data_candidate(self) -> None:
        text = _read(COPY_MODEL)
        assert "MWW_RUNPOD_DATA_DIR" in text or "mww-runpod" in text

    def test_copy_model_resolves_script_dir_under_zsh(self) -> None:
        text = _read(COPY_MODEL)
        assert 'BASH_VERSION' in text
        assert '_this="$0"' in text or "_this='$0'" in text


class TestRunbookAndAgentsRunpod:
    def test_runbook_documents_gpu_pod_not_instant_cluster(self) -> None:
        text = _read(DOCS)
        assert "RunPod" in text or "runpod" in text
        assert "GPU Pod" in text or "gpu pod" in text.lower()
        assert "setup_trainer_runpod.sh" in text
        assert "train_mariano_runpod.sh" in text
        assert "auto-pay" in text.lower() or "Auto-pay" in text
        assert "--stop-after" in text
        assert "personal_samples" in text
        assert "Spot" in text
        assert "Instant Cluster" in text

    def test_agents_documents_runpod_gpu_path(self) -> None:
        text = _read(AGENTS)
        assert "setup_trainer_runpod.sh" in text
        assert "train_mariano_runpod.sh" in text
        assert "teardown_runpod_trainer.sh" in text
        assert "RunPod" in text or "runpod" in text

    def test_docs_mention_teardown_script(self) -> None:
        guide = _read(RUNPOD_GUIDE)
        runbook = _read(DOCS)
        assert "teardown_runpod_trainer.sh" in guide
        assert "--delete-volume" in guide
        assert "teardown_runpod_trainer.sh" in runbook

    def test_mobile_guide_covers_console_flow_without_runpodctl_send(self) -> None:
        text = _read(RUNPOD_MOBILE_GUIDE)
        assert "console.runpod.io" in text
        assert "ghcr.io/tatertotterson/microwakeword" in text
        assert "/data" in text
        assert "8789" in text
        assert "mariano" in text.lower()
        assert "Spanish" in text
        assert "Spot" in text
        assert "Instant Cluster" in text
        assert "Samples" in text
        assert "trained_wake_words" in text
        assert "runpodctl send" not in text
        desktop = _read(RUNPOD_GUIDE)
        assert "runpod-train-mariano-movil.md" in desktop
        assert "runpod-train-mariano-movil.md" in _read(DOCS)
        assert "runpod-train-mariano-movil.md" in _read(AGENTS)
