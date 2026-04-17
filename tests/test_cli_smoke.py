from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("args", "expected_text"),
    [
        (["--help"], "audit"),
        (["audit", "--help"], "--output"),
        (["prepare", "--help"], "Prepare canonical corpus tables"),
        (["train", "--help"], "--run-id"),
        (["evaluate", "--help"], "--compare-variants"),
    ],
)
def test_cli_help_surfaces_registered_commands(cli_runner, args, expected_text) -> None:
    result = cli_runner(*args)

    assert result.returncode == 0, result.stderr
    assert expected_text in result.stdout


def test_audit_command_writes_markdown_report(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "data_audit.md"

    result = cli_runner("audit", "--output", str(output_path))

    assert result.returncode == 0, result.stderr
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("# Data Audit")
