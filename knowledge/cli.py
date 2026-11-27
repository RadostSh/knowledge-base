"""Command-line interface for the knowledge base."""

import argparse
import sys
from collections.abc import Callable

from knowledge.manager import KnowledgeManager
from knowledge.models import KnowledgeBaseError, KnowledgeItem

Handler = Callable[[KnowledgeManager, argparse.Namespace], None]
MAX_ID = 2**63 - 1  # largest value SQLite can store as INTEGER


def _positive_int(value: str) -> int:
    """Parse an ID argument; it must be an integer greater than zero."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("ID must be a positive integer.") from None
    if not 0 < number <= MAX_ID:
        raise argparse.ArgumentTypeError("ID must be a positive integer.")
    return number


def _print_items(items: list[KnowledgeItem], empty_message: str) -> None:
    """Print one '<id> <title>' line per item, or a message if there are none."""
    if not items:
        print(empty_message)
        return
    for item in items:
        print(f"{item.id} {item.title}")


def _cmd_add(manager: KnowledgeManager, args: argparse.Namespace) -> None:
    item = manager.add_item(args.title, args.content)
    print(f"Added item {item.id}: {item.title}")


def _cmd_list(manager: KnowledgeManager, args: argparse.Namespace) -> None:
    _print_items(manager.list_items(), "No items found.")


def _cmd_show(manager: KnowledgeManager, args: argparse.Namespace) -> None:
    item = manager.get_item(args.id)
    print(f"Title: {item.title}")
    print(item.content)


def _cmd_edit(manager: KnowledgeManager, args: argparse.Namespace) -> None:
    item = manager.update_item(args.id, title=args.title, content=args.content)
    print(f"Updated item {item.id}: {item.title}")


def _cmd_search(manager: KnowledgeManager, args: argparse.Namespace) -> None:
    if args.ranked:
        results = manager.search_ranked(args.query)
        if not results:
            print("No matching items found.")
            return
        for item, score in results:
            print(f"{item.id} {item.title} ({score:.2f})")
        return
    _print_items(manager.search_items(args.query), "No matching items found.")


def _cmd_delete(manager: KnowledgeManager, args: argparse.Namespace) -> None:
    manager.delete_item(args.id)
    print(f"Deleted item {args.id}.")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="knowledge",
        description=(
            "A simple personal knowledge base stored in a local SQLite database. "
            "The database location defaults to ~/.knowledge_base.db and can be "
            "changed with the KNOWLEDGE_DB_PATH environment variable."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    add = subparsers.add_parser(
        "add", help="add a new item", description="Add a new item with a title and content."
    )
    add.add_argument("title", help="item title")
    add.add_argument("content", help="item content")
    add.set_defaults(handler=_cmd_add)

    list_ = subparsers.add_parser(
        "list", help="list all items", description="List all items as '<id> <title>'."
    )
    list_.set_defaults(handler=_cmd_list)

    show = subparsers.add_parser(
        "show", help="show a single item", description="Show the title and content of an item."
    )
    show.add_argument("id", type=_positive_int, help="item ID")
    show.set_defaults(handler=_cmd_show)

    edit = subparsers.add_parser(
        "edit",
        help="edit an existing item",
        description="Change the title and/or content of an item. Fields not given stay unchanged.",
    )
    edit.add_argument("id", type=_positive_int, help="item ID")
    edit.add_argument("-t", "--title", default=None, help="new item title")
    edit.add_argument("-c", "--content", default=None, help="new item content")
    edit.set_defaults(handler=_cmd_edit)

    search = subparsers.add_parser(
        "search",
        help="search items by title or content",
        description=(
            "Find items whose title or content contains the query as any substring "
            "(case-insensitive). With --ranked, match whole words only and order "
            "results by relevance."
        ),
    )
    search.add_argument("query", help="text to search for")
    search.add_argument(
        "-r",
        "--ranked",
        action="store_true",
        help="rank results by relevance (matches whole words)",
    )
    search.set_defaults(handler=_cmd_search)

    delete = subparsers.add_parser(
        "delete", help="delete an item", description="Delete an item by its ID."
    )
    delete.add_argument("id", type=_positive_int, help="item ID")
    delete.set_defaults(handler=_cmd_delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    args = build_parser().parse_args(argv)
    handler: Handler = args.handler
    try:
        handler(KnowledgeManager(), args)
    except KnowledgeBaseError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0
