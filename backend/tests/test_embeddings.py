"""Unit tests for cosine similarity; these do not need an OpenAI API key."""

import pytest

from app.embeddings import cosine_similarity


def test_identical_vectors_have_similarity_one():
    assert cosine_similarity([1.0, 0.0, 2.0], [1.0, 0.0, 2.0]) == pytest.approx(1.0)


def test_orthogonal_vectors_have_similarity_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_invalid_vectors_are_safe():
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
