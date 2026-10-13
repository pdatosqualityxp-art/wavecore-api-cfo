from dataclasses import dataclass

import fitz


@dataclass(frozen=True)
class PDFChunk:
    page_number: int
    text: str


def _split_text(text: str, chunk_size: int) -> list[str]:
    chunks: list[str] = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break

        split_at = remaining.rfind(" ", 0, chunk_size + 1)
        if split_at <= 0:
            split_at = chunk_size

        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    return chunks


def extract_pdf_chunks(
    pdf_bytes: bytes,
    chunk_size: int = 800,
) -> list[PDFChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    chunks: list[PDFChunk] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text")
            chunks.extend(
                PDFChunk(page_number=page_number, text=text)
                for text in _split_text(page_text, chunk_size)
            )

    return chunks
