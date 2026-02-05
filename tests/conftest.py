import pytest
from fastapi.testclient import TestClient

from app import config
from app.database import init_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_PATH", tmp_path / "test.db")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(config, "UPLOAD_DIR", upload_dir)
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_pdf():
    return ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")


@pytest.fixture
def sample_txt():
    return ("test.txt", b"Hello, world!", "text/plain")


@pytest.fixture
def sample_docx():
    return ("test.docx", b"PK\x03\x04 fake docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
