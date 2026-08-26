from app.ingest import chunk_text, clean_text


def test_clean_text_collapses_whitespace():
    assert clean_text("a  \t b\n\n\n\nc") == "a b\n\nc"


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_text_single_small():
    assert chunk_text("hello world") == ["hello world"]


def test_chunk_text_packs_paragraphs():
    paras = [f"paragraph {i} " + "x" * 100 for i in range(10)]
    chunks = chunk_text("\n\n".join(paras), max_chars=300)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 300
    # Nothing lost: all paragraphs appear across the chunks
    joined = "\n\n".join(chunks)
    for i in range(10):
        assert f"paragraph {i}" in joined


def test_chunk_text_hard_splits_oversized_paragraph():
    chunks = chunk_text("y" * 1000, max_chars=300)
    assert all(len(c) <= 300 for c in chunks)
    assert sum(len(c) for c in chunks) == 1000
