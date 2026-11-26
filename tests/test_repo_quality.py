"""Repo-wide quality gates: yamllint, shellcheck and the single test entrypoint."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
# Out of scope for this suite (own tooling / paused projects / vendored code).
EXCLUDED_PREFIXES = ("job-finder/", "weather-intelligence/", "Xiaomi-cloud-tokens-extractor/")


def _tracked(*patterns: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", *patterns],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return sorted({p for p in out if not p.startswith(EXCLUDED_PREFIXES) and (REPO_ROOT / p).is_file()})


def test_run_all_entrypoint_exists_and_is_executable() -> None:
    run_all = REPO_ROOT / "tests" / "run_all.sh"
    assert run_all.is_file(), "tests/run_all.sh must exist (single suite entrypoint)"
    assert os.access(run_all, os.X_OK), "tests/run_all.sh must be executable"
    text = run_all.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "pytest" in text


def test_yamllint_config_present() -> None:
    assert (REPO_ROOT / ".yamllint.yaml").is_file()


def test_yaml_files_pass_yamllint() -> None:
    yamllint = shutil.which("yamllint") or str(Path(os.sys.executable).with_name("yamllint"))
    files = _tracked("*.yaml", "*.yml")
    assert files
    res = subprocess.run(
        [yamllint, "-c", str(REPO_ROOT / ".yamllint.yaml"), "-f", "parsable", *files],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    errors = [ln for ln in res.stdout.splitlines() if "[error]" in ln]
    assert res.returncode == 0 and not errors, "\n".join(errors) or res.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_shell_scripts_pass_shellcheck() -> None:
    files = _tracked("*.sh")
    assert files
    res = subprocess.run(
        ["shellcheck", "-S", "warning", "-f", "gcc", *files],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout
