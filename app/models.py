from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    id: int
    filename: str
    size: int
    content_type: str
    upload_timestamp: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentMetadata]
    page: int
    page_size: int
    total: int
