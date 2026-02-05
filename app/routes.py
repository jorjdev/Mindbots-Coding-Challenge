from datetime import datetime, timezone
from pathlib import PurePath
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app import config
from app.database import get_db
from app.models import DocumentListResponse, DocumentMetadata

router = APIRouter()


@router.post("/documents", response_model=DocumentMetadata, status_code=201)
async def upload_document(file: UploadFile = File(...)):
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

    content_type = config.ALLOWED_TYPES[suffix]
    storage_name = f"{uuid4()}_{file.filename}"
    storage_path = config.UPLOAD_DIR / storage_name

    storage_path.write_bytes(content)

    timestamp = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO documents (filename, size, content_type, upload_timestamp, storage_path) VALUES (?, ?, ?, ?, ?)",
            (file.filename, len(content), content_type, timestamp, storage_name),
        )
        conn.commit()
        doc_id = cursor.lastrowid
    finally:
        conn.close()

    return DocumentMetadata(
        id=doc_id,
        filename=file.filename,
        size=len(content),
        content_type=content_type,
        upload_timestamp=timestamp,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    offset = (page - 1) * page_size
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
    finally:
        conn.close()

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


@router.get("/documents/{document_id}", response_model=DocumentMetadata)
async def get_document(document_id: int):
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


@router.get("/documents/{document_id}/download")
async def download_document(document_id: int):
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
