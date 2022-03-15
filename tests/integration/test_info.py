from balena.exceptions import ApplicationNotFound
from click.testing import CliRunner
from resin_release_tool.cli import cli


def test_show_help_message(monkeypatch):
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Usage: cli [OPTIONS] COMMAND [ARGS]..." in result.output


def test_info_raises_application_not_found(monkeypatch):
    import os

    monkeypatch.setenv("RESIN_TOKEN", "fake")
    monkeypatch.setenv("RESIN_APP", "123")
    monkeypatch.setenv("TEST", "true")
    assert os.getenv("RESIN_TOKEN") == "fake"
    assert os.getenv("RESIN_APP") == "123"

    runner = CliRunner()

    result = runner.invoke(cli, ["info"])

    assert result.exit_code == 1
    assert type(result.exception) == ApplicationNotFound
