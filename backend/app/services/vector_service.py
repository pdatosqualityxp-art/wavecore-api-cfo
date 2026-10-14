from dataclasses import dataclass
from datetime import date
from typing import Sequence

from google import genai
from google.genai import types
from starlette.concurrency import run_in_threadpool
from supabase import create_client

from app.core.config import settings
from app.services.pdf_service import PDFChunk


_EMBEDDING_MODEL = "gemini-embedding-001"
_EMBEDDING_DIMENSIONS = 768
_gemini = genai.Client(api_key=settings.gemini_api_key)
_supabase = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)


@dataclass(frozen=True)
class DocumentMetadata:
    id_documento: str
    titulo: str
    tipo_documento: str
    departamento_origen: str
    fecha_emision: date
    resumen_ejecutivo: str | None = None


def _embed_chunks(chunks: Sequence[PDFChunk]) -> list[list[float]]:
    embeddings: list[list[float]] = []

    for chunk in chunks:
        response = _gemini.models.embed_content(
            model=_EMBEDDING_MODEL,
            contents=chunk.text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=_EMBEDDING_DIMENSIONS,
            ),
        )
        if not response.embeddings or not response.embeddings[0].values:
            raise ValueError("Gemini returned an empty embedding")

        values = response.embeddings[0].values
        if len(values) != _EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected {_EMBEDDING_DIMENSIONS} embedding dimensions, "
                f"received {len(values)}"
            )
        embeddings.append(values)

    return embeddings


def search_document_chunks(
    query: str,
    match_count: int = 5,
    document_title: str | None = None,
    page_number: int | None = None,
) -> list[dict[str, object]]:
    response = _gemini.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=_EMBEDDING_DIMENSIONS,
        ),
    )
    if not response.embeddings or not response.embeddings[0].values:
        raise ValueError("Gemini returned an empty query embedding")

    embedding = response.embeddings[0].values
    if len(embedding) != _EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected {_EMBEDDING_DIMENSIONS} embedding dimensions, "
            f"received {len(embedding)}"
        )

    result = _supabase.rpc(
        "match_document_chunks_filtered",
        {
            "query_embedding": embedding,
            "match_count": max(1, min(match_count, 10)),
            "p_document_title": document_title,
            "p_page_number": page_number,
        },
    ).execute()
    return result.data or []


def _insert_document_and_chunks(
    metadata: DocumentMetadata,
    storage_url: str,
    chunks: Sequence[PDFChunk],
) -> str:
    embeddings = _embed_chunks(chunks)

    document_record = {
        "id_documento": metadata.id_documento,
        "titulo": metadata.titulo,
        "tipo_documento": metadata.tipo_documento,
        "departamento_origen": metadata.departamento_origen,
        "fecha_emision": metadata.fecha_emision.isoformat(),
        "resumen_ejecutivo": metadata.resumen_ejecutivo,
        "url_storage": storage_url,
    }
    _supabase.table("documentos").insert(document_record).execute()

    if chunks:
        chunk_records = [
            {
                "document_id": metadata.id_documento,
                "chunk_text": chunk.text,
                "page_number": chunk.page_number,
                "embedding": embedding,
            }
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        _supabase.table("document_chunks").insert(chunk_records).execute()

    return metadata.id_documento


async def store_document_with_chunks(
    metadata: DocumentMetadata,
    storage_url: str,
    chunks: Sequence[PDFChunk],
) -> str:
    return await run_in_threadpool(
        _insert_document_and_chunks,
        metadata,
        storage_url,
        chunks,
    )
