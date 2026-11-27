"""Business logic for the knowledge base: validation on top of storage."""

from knowledge.models import ItemNotFoundError, KnowledgeItem, ValidationError
from knowledge.ranking import rank_items
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

    def search_ranked(self, query: str) -> list[tuple[KnowledgeItem, float]]:
        """Return (item, score) pairs ordered by relevance to the query, best first."""
        query = query.strip()
        if not query:
            raise ValidationError("Search query cannot be empty.")
        return rank_items(query, self.list_items())

    def update_item(
        self, item_id: int, title: str | None = None, content: str | None = None
    ) -> KnowledgeItem:
        """Update the title and/or content of an existing item."""
        if title is None and content is None:
            raise ValidationError("At least one of title or content must be provided.")
        if title is not None:
            title = title.strip()
            if not title:
                raise ValidationError("Title cannot be empty.")
        if content is not None:
            content = content.strip()
            if not content:
                raise ValidationError("Content cannot be empty.")

        existing = self.get_item(item_id)
        new_title = title if title is not None else existing.title
        new_content = content if content is not None else existing.content
        updated = self.storage.update(item_id, new_title, new_content)
        if updated is None:
            raise ItemNotFoundError(f"Item with id {item_id} not found.")
        return updated

    def delete_item(self, item_id: int) -> None:
        """Delete the item with the given ID or raise ItemNotFoundError."""
        if not self.storage.delete(item_id):
            raise ItemNotFoundError(f"Item with id {item_id} not found.")
