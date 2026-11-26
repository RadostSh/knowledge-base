"""End-to-end tests for the command-line interface."""

from pathlib import Path
import pytest
from knowledge.cli import main


@pytest.fixture(autouse=True)
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "kb.db"
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(path))
    return path


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    """Run the CLI and return (exit code, stdout, stderr)."""
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_happy_path(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "add", "Python", "Use venv") == (0, "Added item 1: Python\n", "")
    assert run(capsys, "add", "Cooking", "Boil water") == (0, "Added item 2: Cooking\n", "")
    assert run(capsys, "list") == (0, "1 Python\n2 Cooking\n", "")
    assert run(capsys, "show", "1") == (0, "Title: Python\nUse venv\n", "")
    assert run(capsys, "search", "water") == (0, "2 Cooking\n", "")
    assert run(capsys, "delete", "1") == (0, "Deleted item 1.\n", "")
    assert run(capsys, "list") == (0, "2 Cooking\n", "")


def test_empty_states(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "list") == (0, "No items found.\n", "")
    assert run(capsys, "search", "anything") == (0, "No matching items found.\n", "")


@pytest.mark.parametrize("command", ["show", "delete"])
def test_missing_id(capsys: pytest.CaptureFixture[str], command: str) -> None:
    code, out, err = run(capsys, command, "999")

    assert code == 1
    assert out == ""
    assert err == "Error: Item with id 999 not found.\n"


def test_validation_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(capsys, "add", "   ", "content")

    assert code == 1
    assert out == ""
    assert err == "Error: Title cannot be empty.\n"


@pytest.mark.parametrize("argv", [["show", "abc"], ["show", "0"], ["delete", "-1"]])
def test_invalid_id_argument(capsys: pytest.CaptureFixture[str], argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(argv)

    err = capsys.readouterr().err
    assert exc_info.value.code == 2
    assert "ID must be a positive integer." in err
    assert "Traceback" not in err


def test_corrupted_database(capsys: pytest.CaptureFixture[str], db_path: Path) -> None:
    db_path.write_text("this is not a sqlite database\n" * 100)

    code, out, err = run(capsys, "list")

    assert code == 1
    assert out == ""
    assert err.startswith("Error: ")
    assert str(db_path) in err
    assert "Traceback" not in err


def test_help_lists_all_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    out = capsys.readouterr().out
    assert exc_info.value.code == 0
    for command in ("add", "list", "show", "search", "delete"):
        assert command in out
