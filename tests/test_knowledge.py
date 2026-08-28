import pytest
from app.services.embedding import chunk_text, cosine_similarity


class TestChunkText:
    def test_empty_text(self):
        assert chunk_text("") == []

    def test_short_text(self):
        result = chunk_text("Hello world")
        assert len(result) == 1
        assert result[0] == "Hello world"

    def test_long_text(self):
        text = "word " * 200
        result = chunk_text(text, chunk_size=50, overlap=10)
        assert len(result) > 1

    def test_whitespace_only(self):
        assert chunk_text("   ") == []


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine_similarity(a, b) == 0.0

    def test_partial_similarity(self):
        a = [1.0, 1.0, 0.0]
        b = [1.0, 0.0, 0.0]
        sim = cosine_similarity(a, b)
        assert 0.0 < sim < 1.0
