"""Domain models and exceptions for the knowledge base."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeItem:
    """A single entry in the knowledge base."""

    id: int
    title: str
    content: str


class KnowledgeBaseError(Exception):
    """Base class for all knowledge base errors."""


class ValidationError(KnowledgeBaseError):
    """Raised when user input is invalid (e.g. empty title, content, or query)."""


class ItemNotFoundError(KnowledgeBaseError):
    """Raised when no item exists with the given ID."""


class StorageError(KnowledgeBaseError):
    """Raised when the database cannot be opened, initialized, read, or written, or is corrupted."""
