"""Relevance ranking of knowledge items using TF-IDF and cosine similarity.

Matching is on whole words only, with no stemming ("orchestrates" does not
match "orchestration"). The ranking is lexical, not semantic.
"""

import math
import re
from collections import Counter

from knowledge.models import KnowledgeItem

TITLE_WEIGHT = 2.0


def tokenize(text: str) -> list[str]:
    """Lowercase the text and split it into word tokens."""
    return re.findall(r"\w+", text.lower())


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Return the cosine similarity of two sparse vectors (0.0 if either is empty)."""
    if not vec_a or not vec_b:
        return 0.0
    norm_a = math.sqrt(sum(w * w for w in vec_a.values()))
    norm_b = math.sqrt(sum(w * w for w in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    dot = sum(w * vec_b[term] for term, w in vec_a.items() if term in vec_b)
    return min(1.0, dot / (norm_a * norm_b))


def _weighted_counts(item: KnowledgeItem) -> dict[str, float]:
    """Return term counts where title occurrences weigh TITLE_WEIGHT and content 1.0."""
    counts: dict[str, float] = {}
    for token in tokenize(item.title):
        counts[token] = counts.get(token, 0.0) + TITLE_WEIGHT
    for token in tokenize(item.content):
        counts[token] = counts.get(token, 0.0) + 1.0
    return counts


def rank_items(query: str, items: list[KnowledgeItem]) -> list[tuple[KnowledgeItem, float]]:
    """Rank items by relevance to the query, best first; non-matching items are dropped."""
    query_tokens = tokenize(query)
    if not query_tokens or not items:
        return []

    n = len(items)
    df: Counter[str] = Counter()
    item_counts: list[tuple[KnowledgeItem, dict[str, float]]] = []
    for item in items:
        counts = _weighted_counts(item)
        if not counts:
            continue
        df.update(counts.keys())
        item_counts.append((item, counts))

    def idf(term: str) -> float:
        return math.log((n + 1) / (df.get(term, 0) + 1)) + 1.0

    query_vec = {term: count * idf(term) for term, count in Counter(query_tokens).items()}

    results: list[tuple[KnowledgeItem, float]] = []
    for item, counts in item_counts:
        item_vec = {term: count * idf(term) for term, count in counts.items()}
        score = cosine_similarity(query_vec, item_vec)
        if score > 0.0:
            results.append((item, score))

    results.sort(key=lambda pair: (-pair[1], pair[0].id))
    return results
