import logging
import re
from datetime import datetime, timezone
from pathlib import PurePath
from uuid import uuid4

import magic
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from app import config
from app.database import get_db, query_documents
from app.models import DocumentListResponse, DocumentMetadata

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/documents")


def _sanitize_filename(filename: str) -> str:
    name = PurePath(filename).name  # strip directory components
    name = re.sub(r"[^\w.\-]", "_", name)  # keep alphanumeric, dot, hyphen, underscore
    if len(name) > 255:
        name = name[:255]
    return name


@router.post("", response_model=DocumentMetadata, status_code=201)
@limiter.limit("30/minute")
async def upload_document(request: Request, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    suffix = PurePath(file.filename).suffix.lower()
    if suffix not in config.ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(config.ALLOWED_TYPES)}",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File must not be empty")

    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {config.MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Magic byte validation
    detected_mime = magic.from_buffer(content, mime=True)
    allowed_mimes = config.ALLOWED_MAGIC.get(suffix, set())
    if detected_mime not in allowed_mimes:
        logger.warning(
            "Magic byte mismatch: filename=%s extension=%s detected=%s",
            file.filename, suffix, detected_mime,
        )
        raise HTTPException(
            status_code=415,
            detail=f"File content does not match extension '{suffix}' (detected: {detected_mime})",
        )

    safe_filename = _sanitize_filename(file.filename)
    content_type = config.ALLOWED_TYPES[suffix]
    storage_name = f"{uuid4()}_{safe_filename}"
    storage_path = config.UPLOAD_DIR / storage_name

    # Write file, then insert DB row. Clean up file if DB fails.
    storage_path.write_bytes(content)
    timestamp = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO documents (filename, size, content_type, upload_timestamp, storage_path) VALUES (?, ?, ?, ?, ?)",
            (safe_filename, len(content), content_type, timestamp, storage_name),
        )
        conn.commit()
        doc_id = cursor.lastrowid
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise
    finally:
        conn.close()

    logger.info("Uploaded document id=%d filename=%s size=%d", doc_id, safe_filename, len(content))

    return DocumentMetadata(
        id=doc_id,
        filename=safe_filename,
        size=len(content),
        content_type=content_type,
        upload_timestamp=timestamp,
    )


@router.get("", response_model=DocumentListResponse)
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    rows, total = query_documents(page, page_size)

    documents = [
        DocumentMetadata(
            id=row["id"],
            filename=row["filename"],
            size=row["size"],
            content_type=row["content_type"],
            upload_timestamp=row["upload_timestamp"],
        )
        for row in rows
    ]

    return DocumentListResponse(
        documents=documents, page=page, page_size=page_size, total=total
    )


@router.get("/{document_id}", response_model=DocumentMetadata)
@limiter.limit("60/minute")
async def get_document(request: Request, document_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentMetadata(
        id=row["id"],
        filename=row["filename"],
        size=row["size"],
        content_type=row["content_type"],
        upload_timestamp=row["upload_timestamp"],
    )


@router.get("/{document_id}/download")
@limiter.limit("60/minute")
async def download_document(request: Request, document_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = config.UPLOAD_DIR / row["storage_path"]
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type=row["content_type"],
        filename=row["filename"],
    )


@router.delete("/{document_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_document(request: Request, document_id: int):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete file from disk (ignore if already gone)
        file_path = config.UPLOAD_DIR / row["storage_path"]
        file_path.unlink(missing_ok=True)

        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
    finally:
        conn.close()

    logger.info("Deleted document id=%d", document_id)
    return Response(status_code=204)
