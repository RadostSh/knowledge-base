"""Tests for the KnowledgeManager business logic."""

from pathlib import Path

import pytest

from knowledge.manager import KnowledgeManager
from knowledge.models import ItemNotFoundError, KnowledgeItem, StorageError, ValidationError
from knowledge.storage import SqliteStorage

BLANK_VALUES = ["", "   ", "\t\n "]


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "kb.db"


@pytest.fixture
def manager(db_path: Path) -> KnowledgeManager:
    return KnowledgeManager(SqliteStorage(db_path))


def test_add_and_get_roundtrip(manager: KnowledgeManager) -> None:
    item = manager.add_item("Title", "Content")

    assert manager.get_item(item.id) == KnowledgeItem(item.id, "Title", "Content")


def test_add_strips_values(manager: KnowledgeManager) -> None:
    item = manager.add_item("  Title \n", "\t Content  ")

    assert (item.title, item.content) == ("Title", "Content")
    assert manager.get_item(item.id) == item


@pytest.mark.parametrize("title", BLANK_VALUES)
def test_add_blank_title_raises(manager: KnowledgeManager, title: str) -> None:
    with pytest.raises(ValidationError, match="Title cannot be empty."):
        manager.add_item(title, "Content")
    assert manager.list_items() == []


@pytest.mark.parametrize("content", BLANK_VALUES)
def test_add_blank_content_raises(manager: KnowledgeManager, content: str) -> None:
    with pytest.raises(ValidationError, match="Content cannot be empty."):
        manager.add_item("Title", content)
    assert manager.list_items() == []


def test_get_missing_raises(manager: KnowledgeManager) -> None:
    with pytest.raises(ItemNotFoundError, match="Item with id 42 not found."):
        manager.get_item(42)


def test_list_returns_items_in_order(manager: KnowledgeManager) -> None:
    items = [manager.add_item(f"t{i}", f"c{i}") for i in range(3)]

    assert manager.list_items() == items


def test_list_empty(manager: KnowledgeManager) -> None:
    assert manager.list_items() == []


def test_search_by_title(manager: KnowledgeManager) -> None:
    hit = manager.add_item("Python tips", "use venv")
    manager.add_item("Cooking", "boil water")

    assert manager.search_items("python") == [hit]


def test_search_by_content(manager: KnowledgeManager) -> None:
    manager.add_item("Python tips", "use venv")
    hit = manager.add_item("Cooking", "boil water")

    assert manager.search_items("water") == [hit]


def test_search_no_results(manager: KnowledgeManager) -> None:
    manager.add_item("Python tips", "use venv")

    assert manager.search_items("rust") == []


@pytest.mark.parametrize("query", BLANK_VALUES)
def test_search_blank_query_raises(manager: KnowledgeManager, query: str) -> None:
    with pytest.raises(ValidationError, match="Search query cannot be empty."):
        manager.search_items(query)


def test_search_query_is_stripped(manager: KnowledgeManager) -> None:
    hit = manager.add_item("Python tips", "use venv")
    manager.add_item("Other", "tipsy text without the phrase")

    assert manager.search_items("  python tips  ") == [hit]


def test_delete_existing(manager: KnowledgeManager) -> None:
    item = manager.add_item("Title", "Content")

    manager.delete_item(item.id)

    assert manager.list_items() == []
    with pytest.raises(ItemNotFoundError):
        manager.get_item(item.id)


def test_delete_missing_raises(manager: KnowledgeManager) -> None:
    with pytest.raises(ItemNotFoundError, match="Item with id 7 not found."):
        manager.delete_item(7)


def test_storage_error_propagates(manager: KnowledgeManager, db_path: Path) -> None:
    manager.add_item("Title", "Content")
    db_path.write_text("this is not a sqlite database\n" * 100)

    with pytest.raises(StorageError):
        manager.list_items()
