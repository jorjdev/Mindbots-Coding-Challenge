import io

from app.config import UPLOAD_DIR


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


# --- List tests ---


def _upload_file(client, name="test.pdf", content=b"%PDF-1.4 data"):
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
        _upload_file(client, name=f"file{i}.pdf")
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 3
    assert data["total"] == 3


def test_list_with_pagination(client):
    for i in range(5):
        _upload_file(client, name=f"file{i}.pdf")

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
    assert data["filename"] == "test.pdf"


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
