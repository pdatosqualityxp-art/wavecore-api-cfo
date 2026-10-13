from uuid import uuid4

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool
from supabase import create_client

from app.core.config import settings


_supabase = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key,
)
_bucket = _supabase.storage.from_("waveStorageTest")


async def upload_pdf(file: UploadFile) -> str:
    path = f"CFO_PDFs/{uuid4()}.pdf"
    content = await file.read()

    await run_in_threadpool(
        _bucket.upload,
        path,
        content,
        file_options={"content-type": "application/pdf"},
    )
    return path
