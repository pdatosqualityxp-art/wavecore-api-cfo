from datetime import date
from uuid import uuid4

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.auth import get_registered_user
from app.services.pdf_service import extract_pdf_chunks
from app.services.storage_service import upload_pdf
from app.services.vector_service import (
    DocumentMetadata,
    store_document_with_chunks,
)


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(get_registered_user)],
)


@router.post("/ingest", status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    tipo_documento: str = Form(...),
    departamento_origen: str = Form(...),
    fecha_emision: date = Form(...),
    resumen_ejecutivo: str | None = Form(default=None),
) -> dict[str, str]:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="The uploaded file must have application/pdf content type",
        )

    pdf_bytes = await file.read()
    try:
        chunks = await run_in_threadpool(extract_pdf_chunks, pdf_bytes)
    except fitz.FileDataError as error:
        raise HTTPException(
            status_code=422,
            detail="The uploaded file is not a valid PDF",
        ) from error

    await file.seek(0)
    storage_reference = await upload_pdf(file)
    metadata = DocumentMetadata(
        id_documento=str(uuid4()),
        titulo=titulo,
        tipo_documento=tipo_documento,
        departamento_origen=departamento_origen,
        fecha_emision=fecha_emision,
        resumen_ejecutivo=resumen_ejecutivo,
    )
    await store_document_with_chunks(metadata, storage_reference, chunks)

    return {
        "id_documento": metadata.id_documento,
        "url_storage": storage_reference,
    }
