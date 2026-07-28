import pytest
from typer.testing import CliRunner

import main
from database import database_proxy

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_cli(tmp_path):
    """Point the CLI at a throwaway database and reset module state."""
    original = database_proxy.obj
    main._ready = False
    main._database_path = str(tmp_path / "cli.db")
    yield main._database_path
    main._ready = False
    database_proxy.initialize(original)


def invoke(*args, db=None):
    argv = ["--database", db or main._database_path, *args]
    return runner.invoke(main.app, argv)


def test_help_does_not_touch_the_database(tmp_path):
    """--help must not create a database file as a side effect."""
    db_path = tmp_path / "untouched.db"
    result = runner.invoke(main.app, ["--database", str(db_path), "--help"])

    assert result.exit_code == 0
    assert not db_path.exists()


def test_subcommand_help_does_not_touch_the_database(tmp_path):
    db_path = tmp_path / "untouched.db"
    result = runner.invoke(main.app, ["--database", str(db_path), "create", "--help"])

    assert result.exit_code == 0
    assert not db_path.exists()


def test_create_then_list():
    assert invoke("create", "Alice", "30").exit_code == 0
    assert invoke("create", "Bob", "25").exit_code == 0

    result = invoke("list")
    assert result.exit_code == 0
    assert "Alice" in result.stdout
    assert "Bob" in result.stdout


def test_list_on_empty_database():
    result = invoke("list")
    assert result.exit_code == 0
    assert "No persons found" in result.stdout


def test_list_respects_limit_and_offset():
    for name, age in [("Alice", 30), ("Bob", 25), ("Carol", 41)]:
        assert invoke("create", name, str(age)).exit_code == 0

    result = invoke("list", "--limit", "1", "--offset", "1")
    assert result.exit_code == 0
    assert "Bob" in result.stdout
    assert "Alice" not in result.stdout
    assert "Carol" not in result.stdout


@pytest.mark.parametrize("name, age", [("", "30"), ("Valid", "-1")])
def test_create_rejects_invalid_input(name, age):
    result = invoke("create", "--", name, age)
    assert result.exit_code == 1
    assert "Invalid input" in result.stdout

    listing = invoke("list")
    assert "No persons found" in listing.stdout


def test_list_command_is_registered_under_its_cli_name():
    """The function is list_persons so it stops shadowing the builtin."""
    assert main.list_persons.__name__ == "list_persons"
    result = runner.invoke(main.app, ["--help"])
    assert "list" in result.stdout
