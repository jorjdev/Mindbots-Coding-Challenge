# Document API

A REST API for uploading, listing, retrieving, and downloading documents (PDF, TXT, DOCX).

Built with **Python**, **FastAPI**, and **SQLite**.

## Setup

```bash
pip install -r requirements.txt
```

## Run the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents` | Upload a document (multipart form, field: `file`) |
| GET | `/documents` | List documents (`?page=1&page_size=10`) |
| GET | `/documents/{id}` | Get document metadata |
| GET | `/documents/{id}/download` | Download the file |

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
```

## Run tests

```bash
pytest tests/ -v
```
