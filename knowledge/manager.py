"""Business logic for the knowledge base: validation on top of storage."""

from knowledge.models import ItemNotFoundError, KnowledgeItem, ValidationError
from knowledge.storage import SqliteStorage


class KnowledgeManager:
    """Validates input and coordinates knowledge base operations.

    StorageError from the storage layer is intentionally not caught here.
    """

    def __init__(self, storage: SqliteStorage | None = None) -> None:
        self.storage = storage if storage is not None else SqliteStorage()

    def add_item(self, title: str, content: str) -> KnowledgeItem:
        """Validate and store a new item."""
        title, content = title.strip(), content.strip()
        if not title:
            raise ValidationError("Title cannot be empty.")
        if not content:
            raise ValidationError("Content cannot be empty.")
        return self.storage.add(title, content)

    def list_items(self) -> list[KnowledgeItem]:
        """Return all items ordered by ID."""
        return self.storage.list_all()

    def get_item(self, item_id: int) -> KnowledgeItem:
        """Return the item with the given ID or raise ItemNotFoundError."""
        item = self.storage.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError(f"Item with id {item_id} not found.")
        return item

    def search_items(self, query: str) -> list[KnowledgeItem]:
        """Return items whose title or content contains the query."""
        query = query.strip()
        if not query:
            raise ValidationError("Search query cannot be empty.")
        return self.storage.search(query)

    def delete_item(self, item_id: int) -> None:
        """Delete the item with the given ID or raise ItemNotFoundError."""
        if not self.storage.delete(item_id):
            raise ItemNotFoundError(f"Item with id {item_id} not found.")
