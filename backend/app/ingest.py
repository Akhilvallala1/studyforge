"""Turn source material (PDF bytes, plain text, or a URL) into cleaned text chunks."""

import io
import re

import httpx
from pypdf import PdfReader

MAX_CHUNK_CHARS = 8000


def extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def extract_url(url: str) -> str:
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    html = response.text
    # Crude tag strip — good enough for the MVP; a real HTML-to-text pass is a TODO.
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_text(text)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split on paragraph boundaries, packing paragraphs up to max_chars per chunk."""
    text = clean_text(text)
    if not text:
        return []
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for para in paragraphs:
        # A single paragraph longer than max_chars gets hard-split.
        while len(para) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current, current_len = [], 0
            chunks.append(para[:max_chars])
            para = para[max_chars:]
        if current_len + len(para) + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(para)
        current_len += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks
