import logging
import math
import secrets

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app import config
from app.database import query_documents

logger = logging.getLogger(__name__)

templates = Jinja2Templates(
    directory=str(config.BASE_DIR / "app" / "templates")
)

router = APIRouter()

_csrf_serializer = URLSafeTimedSerializer(config.CSRF_SECRET, salt="csrf")

CSRF_MAX_AGE = 3600  # 1 hour


def _generate_csrf_token() -> str:
    return _csrf_serializer.dumps(secrets.token_hex(16))


def _validate_csrf_token(token: str) -> bool:
    try:
        _csrf_serializer.loads(token, max_age=CSRF_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def _get_page_context(page: int, page_size: int):
    rows, total = query_documents(page, page_size)
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "documents": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# --- Main UI ---


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    msg: str | None = Query(None),
):
    ctx = _get_page_context(page, page_size)
    message = None
    success = True
    if msg == "ok":
        message = "Document uploaded successfully."
    elif msg == "deleted":
        message = "Document deleted."
    elif msg == "err":
        message = "Upload failed. Please try again."
    elif msg == "del_err":
        message = "Delete failed. Please try again."
        success = False

    csrf_token = _generate_csrf_token()
    return templates.TemplateResponse(
        request, "index.html",
        {
            **ctx,
            "message": message,
            "success": success,
            "csrf_token": csrf_token,
        },
    )


@router.post("/", response_class=HTMLResponse)
async def index_upload(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(""),
):
    if not _validate_csrf_token(csrf_token):
        ctx = _get_page_context(1, 10)
        new_csrf = _generate_csrf_token()
        return templates.TemplateResponse(
            request, "index.html",
            {
                **ctx,
                "message": "Invalid or expired CSRF token. Please try again.",
                "success": False,
                "csrf_token": new_csrf,
            },
        )

    # Delegate to the API upload handler
    from app.routes import upload_document
    try:
        await upload_document(request, file)
    except Exception as e:
        logger.error("Upload failed via UI: %s", e)
        return RedirectResponse("/?msg=err", status_code=303)

    return RedirectResponse("/?msg=ok", status_code=303)


@router.post("/delete/{document_id}")
async def index_delete(request: Request, document_id: int, csrf_token: str = Form("")):
    if not _validate_csrf_token(csrf_token):
        return RedirectResponse("/", status_code=303)

    from app.routes import delete_document
    try:
        await delete_document(request, document_id)
    except Exception as e:
        logger.error("Delete failed via UI: %s", e)
        return RedirectResponse("/?msg=del_err", status_code=303)

    return RedirectResponse("/?msg=deleted", status_code=303)
