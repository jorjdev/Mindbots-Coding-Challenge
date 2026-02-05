import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_PATH = Path(os.environ.get("DATABASE_URL", str(BASE_DIR / "documents.db")))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(BASE_DIR / "uploads")))

API_KEY = os.environ.get("API_KEY")  # None = auth disabled
CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "").split(",")
    if o.strip()
]

MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10 MB

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")

CSRF_SECRET = os.environ.get("CSRF_SECRET", "dev-csrf-secret-change-in-production")

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Magic byte validation: maps extension to acceptable detected MIME types
ALLOWED_MAGIC = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "text/x-c", "text/x-c++", "text/x-script.python", "text/html", "application/csv", "text/csv"},
    ".docx": {"application/zip", "application/octet-stream", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
}
