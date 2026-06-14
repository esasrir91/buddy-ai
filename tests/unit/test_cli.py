"""
Unit tests for CLI entrypoint — version callback and structure.
"""

from typer.testing import CliRunner

from buddy.cli.entrypoint import BUDDY_cli

runner = CliRunner()


def test_version_flag_exits_zero():
    result = runner.invoke(BUDDY_cli, ["--version"])
    assert result.exit_code == 0


def test_version_output_contains_version_string():
    import buddy

    result = runner.invoke(BUDDY_cli, ["--version"])
    assert buddy.__version__ in result.output


def test_version_output_not_dev_local():
    result = runner.invoke(BUDDY_cli, ["--version"])
    assert "dev-local" not in result.output


def test_help_flag_exits_zero():
    result = runner.invoke(BUDDY_cli, ["--help"])
    assert result.exit_code == 0


def test_help_contains_buddy_description():
    result = runner.invoke(BUDDY_cli, ["--help"])
    assert "Buddy" in result.output or "buddy" in result.output
