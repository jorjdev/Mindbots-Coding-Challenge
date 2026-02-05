from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app import config

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)):
    if config.API_KEY is None:
        return  # Auth disabled
    if api_key != config.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
