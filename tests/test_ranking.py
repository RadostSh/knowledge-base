"""Unit tests for the relevance-ranking module."""

import pytest

from knowledge.models import KnowledgeItem
from knowledge.ranking import cosine_similarity, rank_items, tokenize


def ids(results: list[tuple[KnowledgeItem, float]]) -> list[int]:
    """Return the item ids from ranking results, in order."""
    return [item.id for item, _ in results]


def test_tokenize_lowercases_and_strips_punctuation() -> None:
    assert tokenize("Hello, World! Docker-compose") == ["hello", "world", "docker", "compose"]


def test_multi_word_query_matches_non_adjacent_words() -> None:
    items = [
        KnowledgeItem(1, "Kubernetes", "Kubernetes orchestrates every container in the cluster"),
        KnowledgeItem(2, "Orchestration", "Service orchestration with a container scheduler"),
        KnowledgeItem(3, "Cooking", "Boil water for pasta"),
    ]
    results = rank_items("container orchestration", items)
    # Item 1 matches only "container" (no stemming), item 2 matches both words.
    assert ids(results) == [2, 1]


def test_title_match_ranks_higher_than_content_match() -> None:
    items = [
        KnowledgeItem(1, "Notes", "docker images"),
        KnowledgeItem(2, "Docker", "notes images"),
    ]
    results = rank_items("docker", items)
    assert ids(results) == [2, 1]
    assert results[0][1] > results[1][1]


def test_rare_term_scores_higher_than_common_term() -> None:
    items = [
        KnowledgeItem(1, "Alpha", "python venv"),
        KnowledgeItem(2, "Beta", "python pip"),
        KnowledgeItem(3, "Gamma", "python tips"),
    ]
    # "python" and "venv" occur once each in item 1; only IDF differs.
    rare = rank_items("venv", items)
    common = rank_items("python", items)
    assert ids(rare) == [1]
    common_score_item1 = dict((item.id, score) for item, score in common)[1]
    assert rare[0][1] > common_score_item1


def test_case_insensitive() -> None:
    items = [
        KnowledgeItem(1, "Docker", "Containers with Docker"),
        KnowledgeItem(2, "Cooking", "Boil water"),
    ]
    assert rank_items("DOCKER", items) == rank_items("docker", items)
    assert ids(rank_items("DOCKER", items)) == [1]


def test_non_matching_items_excluded_and_no_matches_returns_empty() -> None:
    items = [
        KnowledgeItem(1, "Docker", "Containers"),
        KnowledgeItem(2, "Cooking", "Boil water"),
    ]
    assert ids(rank_items("water", items)) == [2]
    assert rank_items("kubernetes", items) == []


def test_empty_items_returns_empty() -> None:
    assert rank_items("docker", []) == []


@pytest.mark.parametrize("query", ["", "   ", "!!! ?? ..."])
def test_empty_or_punctuation_query_returns_empty(query: str) -> None:
    items = [KnowledgeItem(1, "Docker", "Containers")]
    assert rank_items(query, items) == []


def test_ties_ordered_by_id() -> None:
    items = [
        KnowledgeItem(5, "Docker", "Containers"),
        KnowledgeItem(2, "Docker", "Containers"),
    ]
    results = rank_items("docker", items)
    assert ids(results) == [2, 5]
    assert results[0][1] == results[1][1]


def test_scores_in_valid_range() -> None:
    items = [
        KnowledgeItem(1, "Docker", "docker"),
        KnowledgeItem(2, "Docker basics", "Containers with Docker and images"),
        KnowledgeItem(3, "Kubernetes", "Orchestrates docker containers"),
    ]
    results = rank_items("docker containers", items)
    assert results
    for _, score in results:
        assert 0.0 < score <= 1.0 + 1e-9
    exact = rank_items("docker", [KnowledgeItem(1, "Docker", "docker")])
    assert exact[0][1] == pytest.approx(1.0)


def test_cosine_identical_vectors() -> None:
    vec = {"a": 1.5, "b": 2.0, "c": 0.3}
    assert cosine_similarity(vec, dict(vec)) == pytest.approx(1.0)


def test_cosine_no_shared_keys() -> None:
    assert cosine_similarity({"a": 1.0}, {"b": 1.0}) == 0.0


def test_cosine_empty_vector() -> None:
    assert cosine_similarity({}, {"a": 1.0}) == 0.0
    assert cosine_similarity({"a": 1.0}, {}) == 0.0
    assert cosine_similarity({"a": 0.0}, {"a": 1.0}) == 0.0
