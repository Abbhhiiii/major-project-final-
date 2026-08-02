import pytest

from packages.surveillance.knowledge.embeddings import LocalHashEmbedding


def test_related_policy_is_ranked_above_unrelated_text() -> None:
    embeddings = LocalHashEmbedding()
    query = embeddings.embed("road accident emergency vehicle response")
    related = embeddings.embed("Emergency response procedure for a road vehicle accident")
    unrelated = embeddings.embed("Office cafeteria opening hours and lunch menu")
    assert embeddings.similarity(query, related) > embeddings.similarity(query, unrelated)


def test_embeddings_are_normalized_and_deterministic() -> None:
    embeddings = LocalHashEmbedding()
    first = embeddings.embed("Accident response policy")
    assert first == embeddings.embed("Accident response policy")
    assert embeddings.similarity(first, first) == pytest.approx(1)
