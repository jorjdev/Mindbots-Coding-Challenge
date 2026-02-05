import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import config
from app.auth import verify_api_key
from app.database import init_db
from app.pages import router as pages_router
from app.routes import router as api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config.UPLOAD_DIR.mkdir(exist_ok=True)
    init_db()
    logger.info("Document API started")
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Document API", lifespan=lifespan)
app.state.limiter = limiter


# --- Middleware ---


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# --- Exception handlers ---


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    detail = str(exc) if config.DEBUG else "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


# --- Routers ---

# API routes: auth required (when API_KEY is set), rate-limited
api_router_with_auth = api_router
app.include_router(api_router_with_auth, dependencies=[Depends(verify_api_key)])

# SSR pages: no auth (local testing UI)
app.include_router(pages_router)
