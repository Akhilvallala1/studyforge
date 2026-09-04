"""Source documents for the eval, loaded through the app's own ingestion path.

URL and PDF sources deliberately go through `app.ingest`, so the eval measures the
text the generator actually receives (crude tag-stripping artifacts included)
rather than a cleaned-up version the app would never see.
"""


# Lifted into app.ingest, which is where this harness already got its text from. Imported
# rather than redefined so the eval and the app cannot disagree about what a source is.
from app.ingest import Source, from_pdf_bytes, from_text, from_url

__all__ = ["Source", "build_pdf", "from_pdf_bytes", "from_text", "from_url"]

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 60
FONT_SIZE = 11
LEADING = 15
LINES_PER_PAGE = (PAGE_HEIGHT - 2 * MARGIN) // LEADING
WRAP_COLUMNS = 88


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(text: str, columns: int = WRAP_COLUMNS) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) > columns and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def build_pdf(text: str) -> bytes:
    """Minimal multi-page PDF with selectable Helvetica text.

    Hand-rolled because the eval must not add a dependency just to exercise the
    PDF ingestion path, and pypdf (already a dependency) only reads. Uncompressed
    content streams keep it readable and keep pypdf's text extraction honest.
    """
    lines = _wrap(text)
    pages = [
        lines[i : i + LINES_PER_PAGE] for i in range(0, max(len(lines), 1), LINES_PER_PAGE)
    ] or [[]]

    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # 1-based object number

    catalog_num = add(b"")  # placeholder, filled once Pages is numbered
    pages_num = add(b"")
    font_num = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_nums: list[int] = []
    for page_lines in pages:
        parts = [
            b"BT",
            f"/F1 {FONT_SIZE} Tf".encode("latin-1"),
            f"{LEADING} TL".encode("latin-1"),
            f"{MARGIN} {PAGE_HEIGHT - MARGIN} Td".encode("latin-1"),
        ]
        for line in page_lines:
            parts.append(f"({_escape(line)}) Tj".encode("latin-1", "replace"))
            parts.append(b"T*")
        parts.append(b"ET")
        stream = b"\n".join(parts)
        content_num = add(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
        page_num = add(
            f"<< /Type /Page /Parent {pages_num} 0 R /MediaBox "
            f"[0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Resources << /Font << /F1 {font_num} 0 R >> >> "
            f"/Contents {content_num} 0 R >>".encode("latin-1")
        )
        page_nums.append(page_num)

    kids = " ".join(f"{n} 0 R" for n in page_nums)
    objects[catalog_num - 1] = f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode("latin-1")
    objects[pages_num - 1] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_nums)} >>".encode("latin-1")
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"
    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_num} 0 R >>\n".encode("latin-1")
    out += f"startxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    return bytes(out)
