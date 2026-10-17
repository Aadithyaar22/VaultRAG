"""Text extraction (PDF/TXT/DOCX) and chunking."""
import io
import re


class UnsupportedFile(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    if name.endswith(".docx"):
        import docx
        return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
    raise UnsupportedFile("only PDF, TXT and DOCX are supported")


def chunk_text(text: str, max_chars: int = 600) -> list[str]:
    """Paragraph-aware chunking; long paragraphs are split on sentence boundaries."""
    chunks, cur = [], ""
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        parts = [para] if len(para) <= max_chars else re.split(r"(?<=[.!?])\s+", para)
        for part in parts:
            if cur and len(cur) + len(part) + 1 > max_chars:
                chunks.append(cur)
                cur = ""
            cur = f"{cur} {part}".strip() if cur else part
        if cur and len(cur) > max_chars * 0.6:
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    return chunks
