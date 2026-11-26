"""Tests for the SQLite storage layer."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from knowledge.models import KnowledgeItem, StorageError
from knowledge.storage import SqliteStorage, get_default_db_path


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "kb.db"


@pytest.fixture
def storage(db_path: Path) -> SqliteStorage:
    return SqliteStorage(db_path)


def test_add_and_get_by_id_roundtrip(storage: SqliteStorage) -> None:
    item = storage.add("Title", "Some content")

    assert isinstance(item.id, int)
    assert storage.get_by_id(item.id) == KnowledgeItem(item.id, "Title", "Some content")


def test_list_all_is_ordered_by_id(storage: SqliteStorage) -> None:
    ids = [storage.add(f"t{i}", f"c{i}").id for i in range(3)]

    items = storage.list_all()

    assert [item.id for item in items] == sorted(ids)
    assert [item.title for item in items] == ["t0", "t1", "t2"]


def test_list_all_empty(storage: SqliteStorage) -> None:
    assert storage.list_all() == []


def test_get_by_id_missing_returns_none(storage: SqliteStorage) -> None:
    assert storage.get_by_id(999) is None


def test_delete_existing_and_missing(storage: SqliteStorage) -> None:
    item = storage.add("To delete", "x")

    assert storage.delete(item.id) is True
    assert storage.get_by_id(item.id) is None
    assert storage.list_all() == []
    assert storage.delete(item.id) is False
    assert storage.delete(12345) is False


def test_update_existing_persists(storage: SqliteStorage, db_path: Path) -> None:
    item = storage.add("Old title", "Old content")
    other = storage.add("Other", "untouched")

    updated = storage.update(item.id, "New title", "New content")

    expected = KnowledgeItem(item.id, "New title", "New content")
    assert updated == expected
    assert SqliteStorage(db_path).get_by_id(item.id) == expected
    assert storage.get_by_id(other.id) == other


def test_update_missing_returns_none(storage: SqliteStorage) -> None:
    assert storage.update(999, "t", "c") is None
    assert storage.list_all() == []


def test_search_matches_title(storage: SqliteStorage) -> None:
    hit = storage.add("Python tips", "use venv")
    storage.add("Cooking", "boil water")

    assert storage.search("tips") == [hit]


def test_search_matches_content(storage: SqliteStorage) -> None:
    storage.add("Python tips", "use venv")
    hit = storage.add("Cooking", "boil water")

    assert storage.search("water") == [hit]


def test_search_is_case_insensitive_for_ascii(storage: SqliteStorage) -> None:
    hit = storage.add("Python Tips", "Use VENV")

    assert storage.search("python") == [hit]
    assert storage.search("PYTHON") == [hit]
    assert storage.search("venv") == [hit]


def test_search_no_match_returns_empty_list(storage: SqliteStorage) -> None:
    storage.add("Python tips", "use venv")

    assert storage.search("rust") == []


def test_search_results_ordered_by_id(storage: SqliteStorage) -> None:
    first = storage.add("note one", "a")
    storage.add("other", "b")
    third = storage.add("x", "another note")

    assert storage.search("note") == [first, third]


def test_search_treats_percent_and_underscore_literally(storage: SqliteStorage) -> None:
    percent = storage.add("100% done", "a")
    underscore = storage.add("snake_case", "b")
    storage.add("1000 done", "c")
    storage.add("snakeXcase", "d")

    assert storage.search("100%") == [percent]
    assert storage.search("%") == [percent]
    assert storage.search("snake_case") == [underscore]
    assert storage.search("_") == [underscore]


def test_search_treats_backslash_literally(storage: SqliteStorage) -> None:
    hit = storage.add(r"C:\path", "a")
    storage.add("C:path", "b")

    assert storage.search("\\") == [hit]
    assert storage.search(r":\p") == [hit]


def test_data_persists_across_instances(db_path: Path) -> None:
    item = SqliteStorage(db_path).add("Persistent", "still here")

    assert SqliteStorage(db_path).get_by_id(item.id) == item


def test_random_text_file_raises_storage_error(tmp_path: Path) -> None:
    bad = tmp_path / "not_a_db.db"
    original = "this is definitely not a sqlite database\n" * 100
    bad.write_text(original)

    with pytest.raises(StorageError, match="not_a_db.db"):
        SqliteStorage(bad)
    assert bad.read_text() == original  # never overwritten


def test_table_with_wrong_columns_raises_storage_error(tmp_path: Path) -> None:
    path = tmp_path / "other.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE items (foo TEXT)")
        conn.commit()

    with pytest.raises(StorageError, match="not a valid knowledge base database"):
        SqliteStorage(path)


def test_missing_parent_directory_is_created(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "kb.db"

    storage = SqliteStorage(path)

    assert path.parent.is_dir()
    assert storage.add("t", "c").id == 1


def test_parent_is_regular_file_raises_storage_error(tmp_path: Path) -> None:
    parent = tmp_path / "a_file"
    parent.write_text("not a directory")

    with pytest.raises(StorageError):
        SqliteStorage(parent / "kb.db")


def test_default_db_path_uses_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "custom.db"
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", str(target))

    assert get_default_db_path() == target


def test_default_db_path_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("KNOWLEDGE_DB_PATH", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert get_default_db_path() == tmp_path / ".knowledge_base.db"
