import logging
import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.database import engine, Base
from app.core.config import settings
from app.core.limiter import limiter
from app.routes import auth, game, stats

# Configure structured JSON logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(message)s",
)
logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "game_id"):
            log_data["game_id"] = record.game_id
        if hasattr(record, "bet_amount"):
            log_data["bet_amount"] = record.bet_amount
        if hasattr(record, "game_result"):
            log_data["game_result"] = record.game_result
        if hasattr(record, "request_path"):
            log_data["request_path"] = record.request_path
        if hasattr(record, "response_time"):
            log_data["response_time"] = record.response_time
        return json.dumps(log_data)


# Apply JSON formatter to root logger
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger().handlers = [handler]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Blackjack API")
    if settings.ENVIRONMENT.lower() in {"development", "dev", "testing", "test"}:
        # NOTE: create_all is acceptable for local and test workflows.
        Base.metadata.create_all(bind=engine)
    else:
        logger.info(
            "Skipping schema auto-creation in non-dev environment; run migrations instead"
        )
    yield
    # Shutdown
    logger.info("Shutting down Blackjack API")


app = FastAPI(
    title="Blackjack Game Engine API",
    description="Production-grade Blackjack game with clean architecture",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting — per-IP throttle on auth endpoints
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware — origins driven by CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    log_record = logging.LogRecord(
        name="api",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"{request.method} {request.url.path}",
        args=(),
        exc_info=None,
    )
    log_record.request_path = str(request.url.path)
    log_record.response_time = f"{process_time:.3f}s"

    logger.handle(log_record)

    return response


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(game.router, prefix="/game", tags=["Game"])
app.include_router(stats.router, prefix="/stats", tags=["Statistics"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "blackjack-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/ready")
async def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "service": "blackjack-api",
            "environment": settings.ENVIRONMENT,
        }
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
