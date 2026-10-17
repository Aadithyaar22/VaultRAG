"""Text extraction (PDF/TXT/DOCX) and chunking."""
import io
import logging
import re

logging.getLogger("pypdf").setLevel(logging.ERROR)  # real-world PDFs emit many font warnings


class UnsupportedFile(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        return _pdf_text(data)[0]
    if name.endswith(".docx"):
        return _docx_text(data)
    raise UnsupportedFile("only PDF, TXT and DOCX are supported")


def chunk_text(text: str, max_chars: int = 600, overlap: int = 140) -> list[str]:
    """Paragraph-aware chunking; long paragraphs are split on sentence boundaries. Each chunk after the first starts
    with the tail of the previous one (~`overlap` chars, at a word boundary) so a fact split across a boundary
    (e.g. 'call the helpline at' / '1-800-...') stays retrievable."""
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
    if overlap <= 0 or len(chunks) < 2:
        return chunks
    out = [chunks[0]]
    for prev, c in zip(chunks, chunks[1:]):
        tail = prev[-overlap:]
        cut = tail.find(" ")
        tail = tail[cut + 1:] if 0 <= cut < len(tail) - 1 and len(prev) > overlap else tail
        out.append(f"{tail} {c}".strip())
    return out


_WORDLIKE = re.compile(r"^(?:[A-Za-z][a-z]+|[A-Z]+|[A-Za-z]|\d+(?:[.,]\d+)*|[A-Za-z][a-z]+(?:['’-][A-Za-z]+)+)$")


def text_quality(text: str) -> float | None:
    """Share of word-like tokens (language-agnostic for Latin scripts). Garbled font-encoding output such as
    'F0zNO2b0wNF CzN0Sb0wNF' scores ~0.3; normal prose ~0.95+. Returns None when the text is not mostly
    Latin letters (cannot judge, e.g. CJK), so such documents are not rejected on a heuristic."""
    toks = re.findall(r"[^\s]+", text)
    toks = [t.strip(".,;:!?()[]{}\"'“”‘’•■|-–—/") for t in toks]
    toks = [t for t in toks if t]
    if len(toks) < 8:
        return None
    letters = sum(c.isalpha() for c in text)
    latin = sum(("a" <= c.lower() <= "z") or c in "äöüßéèêàáâçñíóúøåæœ" for c in text)
    if letters == 0 or latin / letters < 0.8:
        return None
    return sum(bool(_WORDLIKE.match(t)) for t in toks) / len(toks)


def _clean(text: str) -> str:
    text = re.sub(r"\(cid:\d+\)", " ", text)           # unmapped glyphs (bullets etc.) from pdfminer
    return re.sub(r"[ \t]+", " ", text)


def _pdf_text(data: bytes) -> tuple[str, dict]:
    """pypdf first (fast); when its output looks corrupted (custom font encodings), retry with pdfminer.six."""
    from pypdf import PdfReader
    report = {"method": "pypdf"}
    text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    q = text_quality(text)
    report["quality"] = q
    if q is not None and q < 0.85:
        try:
            from pdfminer.high_level import extract_text as _pm
            alt = _clean(_pm(io.BytesIO(data)))
            qa = text_quality(alt)
            if qa is not None and qa > q:
                text, report = alt, {"method": "pdfminer", "quality": qa, "pypdf_quality": q}
        except Exception:  # pdfminer not installed or failed: keep the pypdf text; chunk filter still applies
            report["fallback"] = "unavailable"
    return text, report


_MEMO: dict[str, tuple[str, dict]] = {}


def extract_with_report(filename: str, data: bytes) -> tuple[str, dict]:
    """Extract text + a small report. Memoised (last few files) because one upload extracts the same bytes several times."""
    import hashlib
    key = hashlib.sha256(data).hexdigest() + filename.lower()[-5:]
    if key in _MEMO:
        return _MEMO[key]
    name = filename.lower()
    if name.endswith(".pdf"):
        out = _pdf_text(data)
    else:
        text = extract_text(filename, data)
        out = (text, {"method": name.rsplit(".", 1)[-1], "quality": text_quality(text)})
    if len(_MEMO) >= 4:
        _MEMO.pop(next(iter(_MEMO)))
    _MEMO[key] = out
    return out


def readable_chunks(chunks: list[str], min_quality: float = 0.6) -> tuple[list[str], int]:
    """Drop chunks whose text is unreadable (garbled fonts / OCR noise). Returns (kept, dropped_count)."""
    kept = [c for c in chunks if (text_quality(c) is None or text_quality(c) >= min_quality)]
    return kept, len(chunks) - len(kept)


def _docx_text(data: bytes) -> str:
    """Read the document body in order, including tables (one row per line, cells joined by ' | '),
    hyperlinks, content controls and text boxes — python-docx's `paragraphs` alone skips most real-world content."""
    import docx
    from docx.oxml.ns import qn

    def para(p) -> str:
        out = []
        for el in p.iter():
            if el.tag == qn("w:t") and el.text:
                out.append(el.text)
            elif el.tag in (qn("w:tab"), qn("w:br")):
                out.append(" ")
        return "".join(out).strip()

    lines: list[str] = []

    def walk(parent) -> None:
        for el in parent.iterchildren():
            if el.tag == qn("w:p"):
                t = para(el)
                if t:
                    lines.append(t)
            elif el.tag == qn("w:tbl"):
                for tr in el.iterchildren(qn("w:tr")):
                    cells = []
                    for tc in tr.iterchildren(qn("w:tc")):
                        cells.append(" ".join(t for t in (para(p) for p in tc.iter(qn("w:p"))) if t))
                    row = " | ".join(c for c in cells if c)
                    if row:
                        lines.append(row)
            elif el.tag == qn("w:sdt"):
                for content in el.iterchildren(qn("w:sdtContent")):
                    walk(content)

    walk(docx.Document(io.BytesIO(data)).element.body)
    return "\n\n".join(lines)
