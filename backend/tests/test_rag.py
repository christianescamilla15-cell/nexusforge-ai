"""Tests for RAG text chunking."""

from app.rag.indexer import chunk_text


def test_chunk_text_splits_correctly():
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 3
    assert all(len(c) <= 500 for c in chunks)


def test_chunk_text_with_overlap():
    text = "A" * 1000
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    # With stride of 400, we expect: 0-500, 400-900, 800-1000
    assert len(chunks) == 3
    # Verify overlap: the start of chunk 2 should repeat end of chunk 1
    assert chunks[0][-100:] == chunks[1][:100]


def test_chunk_text_short_text():
    text = "Short text here."
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == "Short text here."


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_exact_chunk_size():
    """When text == chunk_size, the stride (chunk_size - overlap) causes a second
    small chunk from the overlap window. Verify both are produced."""
    text = "X" * 500
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    # stride = 450, so positions: 0-500, 450-500 → 2 chunks
    assert len(chunks) == 2
    assert chunks[0] == text
    assert len(chunks[1]) == 50
