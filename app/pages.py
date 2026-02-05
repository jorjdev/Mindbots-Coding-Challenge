import math
from pathlib import PurePath

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.database import get_db
from app.routes import upload_document

templates = Jinja2Templates(
    directory=str(config.BASE_DIR / "app" / "templates")
)

router = APIRouter()


def _get_page_context(page: int, page_size: int):
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

    documents = [dict(row) for row in rows]
    total_pages = max(1, math.ceil(total / page_size))

    return {
        "documents": documents,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    ctx = _get_page_context(page, page_size)
    return templates.TemplateResponse(
        request, "index.html", {**ctx, "message": None, "success": True}
    )


@router.post("/", response_class=HTMLResponse)
async def index_upload(
    request: Request,
    file: UploadFile = File(...),
):
    suffix = PurePath(file.filename or "").suffix.lower()

    if not file.filename or suffix not in config.ALLOWED_TYPES:
        ctx = _get_page_context(1, 10)
        msg = f"Unsupported file type. Allowed: PDF, TXT, DOCX"
        return templates.TemplateResponse(
            request, "index.html", {**ctx, "message": msg, "success": False}
        )

    content = await file.read()
    if len(content) == 0:
        ctx = _get_page_context(1, 10)
        return templates.TemplateResponse(
            request, "index.html",
            {**ctx, "message": "File must not be empty.", "success": False},
        )

    # Reset file position and delegate to the API handler
    await file.seek(0)
    await upload_document(file)

    ctx = _get_page_context(1, 10)
    return templates.TemplateResponse(
        request, "index.html",
        {**ctx, "message": f"Uploaded '{file.filename}' successfully.", "success": True},
    )
