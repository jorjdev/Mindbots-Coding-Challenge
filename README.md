# Document API

A REST API for uploading, listing, retrieving, downloading, and deleting documents (PDF, TXT, DOCX).

Built with **Python**, **FastAPI**, and **SQLite**.

## Setup

```bash
pip install -r requirements.txt
brew install libmagic  # required by python-magic for file content validation
```

## Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.
Web UI at `http://localhost:8000/`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents` | Upload a document (multipart form, field: `file`) |
| GET | `/documents` | List documents (`?page=1&page_size=10`) |
| GET | `/documents/{id}` | Get document metadata |
| GET | `/documents/{id}/download` | Download the file |
| DELETE | `/documents/{id}` | Delete a document |

## Examples

```bash
# Upload a PDF
curl -X POST -F "file=@report.pdf" http://localhost:8000/documents

# List documents
curl http://localhost:8000/documents?page=1&page_size=5

# Get metadata
curl http://localhost:8000/documents/1

# Download
curl -OJ http://localhost:8000/documents/1/download

# Delete
curl -X DELETE http://localhost:8000/documents/1
```

## Configuration

All settings are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `./documents.db` | SQLite database path |
| `UPLOAD_DIR` | `./uploads` | File storage directory |
| `CORS_ORIGINS` | _(empty)_ | Comma-separated allowed origins |
| `MAX_FILE_SIZE` | `10485760` | Max upload size in bytes (10 MB) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `false` | Show detailed errors in 500 responses |
| `CSRF_SECRET` | _(auto-generated)_ | Secret for CSRF token signing |

## Security

The API implements multiple layers of security:

- **CSRF protection** on web UI forms (signed tokens with expiration)
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`
- **File content validation** via magic bytes (not just extension checking)
- **Filename sanitization** (strips path traversal attempts, special characters)
- **10 MB upload size limit** (configurable)
- **Rate limiting** via slowapi (30 req/min for uploads, 60 req/min for reads)
- **CORS policy** (configurable allowed origins)
- **Input validation** on all endpoints

## Run tests

```bash
pytest tests/ -v
```
