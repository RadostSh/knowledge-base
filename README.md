# Knowledge Base CLI

A small command-line application for storing, retrieving, searching and managing short pieces of text. Items are kept in a local SQLite database, so they are still there after the application is restarted.

Besides the required commands (`add`, `list`, `show`, `search`, `delete`), the project has one optional feature: **relevance-ranked search** (`search --ranked`), based on TF-IDF and cosine similarity in pure Python. It also includes a small `edit` command.

---

## Project structure

```
knowledge-base/
├── knowledge/
│   ├── __init__.py     # package marker and version
│   ├── __main__.py     # entry point for `python -m knowledge`
│   ├── cli.py          # argparse CLI: parsing, output formatting
│   ├── manager.py      # core logic: validation and use cases
│   ├── storage.py      # persistence: SQLite access only (SqliteStorage)
│   ├── ranking.py      # TF-IDF + cosine similarity, pure functions
│   └── models.py       # KnowledgeItem dataclass and exception hierarchy
├── tests/
│   ├── test_cli.py
│   ├── test_manager.py
│   ├── test_ranking.py
│   └── test_storage.py
├── pyproject.toml      # packaging, `knowledge` entry point, dev dependency
└── README.md
```

---

## Commands

| Command | Description |
| --- | --- |
| `knowledge add TITLE CONTENT` | Add a new item. |
| `knowledge list` | List all items (ID and title). |
| `knowledge show ID` | Show the title and content of an item. |
| `knowledge edit ID [-t TITLE] [-c CONTENT]` | Change the title and/or content of an item. |
| `knowledge search QUERY [-r]` | Search by title and content (`-r` / `--ranked` for ranked search). |
| `knowledge delete ID` | Delete an item. |

Use `knowledge <command> --help` for the details of one command. Arguments that contain spaces must be quoted.

---

### Example session

```
$ knowledge add "Python" "Python is a high-level programming language."
Added item 1: Python

$ knowledge add "Docker" "Docker is used to package applications into containers."
Added item 2: Docker

$ knowledge add "Kubernetes" "Kubernetes orchestrates containers across many machines."
Added item 3: Kubernetes

$ knowledge list
1 Python
2 Docker
3 Kubernetes

$ knowledge show 2
Title: Docker
Docker is used to package applications into containers.

$ knowledge edit 1 --title "Python 3"
Updated item 1: Python 3

$ knowledge delete 3
Deleted item 3.

$ knowledge list
1 Python 3
2 Docker
```

`edit` changes only the fields you pass; the other field stays unchanged. At least one of `--title` / `--content` is required.

---

## Optional feature: ranked search

`knowledge search QUERY --ranked` (or `-r`) returns the items ordered by how relevant they are to the query, with a relative score.

**How it works**:

1. The query and each item are split into lowercase words.
2. For each item, words are counted. A word in the **title counts twice** as much as a word in the content.
3. **IDF** (inverse document frequency) gives rare words more weight than words that occur in every item.
4. Each item and the query become sparse vectors of `count * idf`.
5. The score is the **cosine similarity** of the query vector and the item vector. Items with score 0 are dropped, and ties are ordered by ID so results are deterministic.

**Why this feature.** A relevance-ranked list is the "retrieve" step of a retrieval pipeline (for example RAG): find the pieces of text most relevant to a question. TF-IDF with cosine similarity is a lightweight, well-understood way to do it that works instantly and offline, with no API keys, no model downloads and no new dependencies. It also makes the search clearly more useful than plain substring matching, because results are ordered and multi-word queries work.

## Plain vs. ranked search

There are two search modes. They answer slightly different questions, so the results can differ.

|  | `knowledge search QUERY` | `knowledge search QUERY --ranked` |
| --- | --- | --- |
| Matches | any **substring** of the title or content, case-insensitive | **whole words** of the title or content, case-insensitive |
| Order | by ID | by relevance, best first |
| Output | `<id> <title>` | `<id> <title> (<score>)` |
| Multi-word query | the exact phrase must appear | words may appear anywhere, not next to each other |

Examples, with the three items from the session above (Python, Docker, Kubernetes):

```
$ knowledge search container
2 Docker
3 Kubernetes

$ knowledge search contain
2 Docker
3 Kubernetes

$ knowledge search contain --ranked
No matching items found.

$ knowledge search containers --ranked
3 Kubernetes (0.21)
2 Docker (0.20)

$ knowledge search "containers orchestrates"
No matching items found.

$ knowledge search "containers orchestrates" --ranked
3 Kubernetes (0.34)
2 Docker (0.12)
```

Things to know:

- **`--ranked` matches whole words only and does no stemming.** "contain" does not match "containers", and "container" does not match "containers" either. Plain search does match them, because "contain" is a substring of "containers".
- **The score is relative.** It is only meant to order the results of one query, it is not a percentage and is not comparable between different queries.
- **Quote multi-word queries**: `knowledge search "docker containers" --ranked`. Without quotes the shell passes two separate arguments and the command is rejected.

---

## Storage: SQLite

I chose SQLite because it is the best balance of simplicity and reliability for a small, single-user application:

- **Built into Python** (`sqlite3`): no server and no extra dependencies, and all data lives in a single file.
- **Safe writes:** every operation is a transaction, so a crash or interruption cannot leave a half-written file. A JSON file is rewritten as a whole, which needs extra care to stay safe.
- **Automatic IDs** (`AUTOINCREMENT`), so IDs do not have to be managed by hand.
- **Easy to extend:** with more data, an index can be added.

**Trade-offs:** the file is not human-readable like JSON, the database is meant for a single user without heavy concurrent writes, and ranked search loads all items into memory. For a small personal knowledge base this is acceptable.

---

## Error handling

Users get a short message, never a stack trace.

| Situation | Message / behaviour | Exit code |
| --- | --- | --- |
| ID that does not exist (`show`, `edit`, `delete`) | `Error: Item with id 99 not found.` | 1 |
| Empty or blank title / content | `Error: Title cannot be empty.` / `Error: Content cannot be empty.` | 1 |
| Empty or blank search query | `Error: Search query cannot be empty.` | 1 |
| `edit` without `--title` or `--content` | `Error: At least one of title or content must be provided.` | 1 |
| Corrupted, unreadable or unwritable database file | `Error: Cannot open the database at <path>: ...` | 1 |
| Invalid ID (not a number, zero, negative) | argparse usage message: `ID must be a positive integer.` | 2 |
| Missing arguments or no command | argparse usage message | 2 |

A corrupted database file is **never** deleted or overwritten automatically, so the data can still be recovered by hand.

---

## Setup

```bash
git clone https://github.com/RadostSh/knowledge-base.git
cd knowledge-base
```

Create and activate a virtual environment (recommended):

- **macOS / Linux**
    
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    
- **Windows (PowerShell)**
    
    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```
    

Install the application together with the development dependencies (pytest):

```bash
pip install -e ".[dev]"
```

If you only want to use the application, `pip install .` is enough.

## Running the application

After installation the `knowledge` command is available:

```bash
knowledge --help
```

The package can also be run without the entry point:

```bash
python -m knowledge --help
```

### Where the data is stored

By default the database is stored in your home directory: `~/.knowledge_base.db`, so the same items are available no matter where you run the command from.

To use a different file, set the `KNOWLEDGE_DB_PATH` environment variable:

```bash
export KNOWLEDGE_DB_PATH=/path/to/my_knowledge.db     # macOS / Linux
$env:KNOWLEDGE_DB_PATH = "C:\path\to\my_knowledge.db"  # Windows PowerShell
```

The parent directory is created automatically if it does not exist. This is also how the tests use temporary databases.

## Running the tests

```bash
pytest
```

or, with more detail:

```bash
pytest -v
```

All tests use `pytest` fixtures (`tmp_path`, `monkeypatch`) and never touch the real home directory or the real database.

## Use of AI tools

I used AI tools (Claude/Gemini) as a pair-programming assistant while building this project. However, I maintained strict control over the architectural decisions.

The research for the optional feature was done with AI as well: I read the material it pointed me to on retrieval and the retrieval step of RAG before deciding on ranked search, and I chose a lexical, dependency-free approach because it works offline and can be explained and tested. I also used AI as a learning and comparison aid. It helped me understand concepts such as TF-IDF, cosine similarity and the difference between lexical and semantic search, and I compared options (SQLite vs. JSON, argparse vs. Click, unittest vs. pytest) before choosing.

I checked the generated code by reading every diff before committing, running the full pytest suite after each step, and trying the commands by hand, including error cases, to confirm that users never see a stack trace.