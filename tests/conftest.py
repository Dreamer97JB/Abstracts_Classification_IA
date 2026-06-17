from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

CliRunner = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_PATH)
        if not pythonpath
        else os.pathsep.join((str(SRC_PATH), pythonpath))
    )
    return env


@pytest.fixture
def cli_runner(project_root: Path, cli_env: dict[str, str]) -> CliRunner:
    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "abstract_classifier.cli", *args],
            cwd=project_root,
            env=cli_env,
            capture_output=True,
            text=True,
            check=False,
        )

    return run
