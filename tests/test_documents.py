import io

import magic

from app import config


# --- Upload tests ---


def test_upload_pdf(client, sample_pdf):
    filename, content, expected_type = sample_pdf
    response = client.post(
        "/documents", files={"file": (filename, io.BytesIO(content), "application/octet-stream")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == filename
    assert data["size"] == len(content)
    assert data["content_type"] == expected_type
    assert "id" in data
    assert "upload_timestamp" in data


def test_upload_txt(client, sample_txt):
    filename, content, expected_type = sample_txt
    response = client.post(
        "/documents", files={"file": (filename, io.BytesIO(content), "text/plain")}
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == expected_type


def test_upload_docx(client, sample_docx):
    filename, content, expected_type = sample_docx
    response = client.post(
        "/documents", files={"file": (filename, io.BytesIO(content), "application/octet-stream")}
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == expected_type


def test_upload_unsupported_type(client):
    response = client.post(
        "/documents", files={"file": ("photo.jpg", io.BytesIO(b"fake image"), "image/jpeg")}
    )
    assert response.status_code == 415


def test_upload_empty_file(client):
    response = client.post(
        "/documents", files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    )
    assert response.status_code == 400


def test_upload_no_file(client):
    response = client.post("/documents")
    assert response.status_code == 400


def test_upload_file_too_large(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_FILE_SIZE", 100)  # 100 bytes
    content = b"%PDF-1.4 " + b"x" * 200
    response = client.post(
        "/documents", files={"file": ("big.pdf", io.BytesIO(content), "application/pdf")}
    )
    assert response.status_code == 413


def test_upload_magic_byte_mismatch(client):
    """Upload a .pdf file that actually contains plain text — should be rejected."""
    content = b"This is just plain text, not a PDF"
    response = client.post(
        "/documents", files={"file": ("fake.pdf", io.BytesIO(content), "application/pdf")}
    )
    assert response.status_code == 415
    assert "content does not match" in response.json()["detail"]


def test_upload_filename_sanitized(client):
    """Filenames with path traversal or special chars should be sanitized."""
    content = b"%PDF-1.4 data"
    response = client.post(
        "/documents", files={"file": ("../../etc/evil.pdf", io.BytesIO(content), "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert "/" not in data["filename"]
    assert ".." not in data["filename"]


# --- List tests ---


def _upload_file(client, name="test.txt", content=b"Hello, world!"):
    return client.post("/documents", files={"file": (name, io.BytesIO(content), "application/octet-stream")})


def test_list_empty(client):
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["documents"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_list_default_pagination(client):
    for i in range(3):
        _upload_file(client, name=f"file{i}.txt")
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 3
    assert data["total"] == 3


def test_list_with_pagination(client):
    for i in range(5):
        _upload_file(client, name=f"file{i}.txt")

    response = client.get("/documents", params={"page": 2, "page_size": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 2
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["page_size"] == 2


def test_list_page_beyond_data(client):
    _upload_file(client)
    response = client.get("/documents", params={"page": 99})
    assert response.status_code == 200
    assert response.json()["documents"] == []


def test_list_invalid_page(client):
    response = client.get("/documents", params={"page": 0})
    assert response.status_code == 400


def test_list_invalid_page_size(client):
    response = client.get("/documents", params={"page_size": 101})
    assert response.status_code == 400


# --- Get by ID tests ---


def test_get_document(client):
    upload = _upload_file(client)
    doc_id = upload.json()["id"]
    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["filename"] == "test.txt"


def test_get_document_not_found(client):
    response = client.get("/documents/999")
    assert response.status_code == 404


# --- Download tests ---


def test_download_document(client):
    content = b"Hello, this is a test file."
    _upload_file(client, name="hello.txt", content=content)
    doc_id = 1
    response = client.get(f"/documents/{doc_id}/download")
    assert response.status_code == 200
    assert response.content == content
    assert "hello.txt" in response.headers.get("content-disposition", "")


def test_download_not_found(client):
    response = client.get("/documents/999/download")
    assert response.status_code == 404


# --- Delete tests ---


def test_delete_document(client):
    upload = _upload_file(client)
    doc_id = upload.json()["id"]

    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 404


def test_delete_not_found(client):
    response = client.delete("/documents/999")
    assert response.status_code == 404


# --- Auth tests ---


def test_api_key_required_when_set(auth_client):
    response = auth_client.get("/documents")
    assert response.status_code == 401


def test_api_key_accepted(auth_client):
    response = auth_client.get("/documents", headers={"X-API-Key": "test-secret-key"})
    assert response.status_code == 200


def test_api_key_wrong(auth_client):
    response = auth_client.get("/documents", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
