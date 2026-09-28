"""FastAPI application entry point.

Run locally from the `backend/` directory:

    uvicorn api.main:app --reload --port 8000

Only the health endpoint lives here for now. Audit, project and auth routes
land in Phase 2, once the extraction pipeline has been validated against real
Material Test Certificates.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Complyx API",
    description="Automated compliance verification for critical assets.",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _tesseract_status() -> dict[str, str | bool]:
    """Report whether the Tesseract binary is reachable.

    Tesseract is a system package rather than a pip dependency, so it is the
    local-setup step most likely to be missing. Without it, scanned
    certificates cannot be read at all.
    """
    try:
        import pytesseract

        if settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        return {"available": True, "version": str(pytesseract.get_tesseract_version())}
    except Exception as exc:
        return {"available": False, "detail": type(exc).__name__}


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness probe and local-environment report.

    Reports only whether each credential is *present*, never its value.
    """
    return {
        "status": "ok",
        "service": "complyx-api",
        "version": app.version,
        "environment": settings.APP_ENV,
        "checks": {
            "tesseract": _tesseract_status(),
            "nvidia_key_configured": bool(settings.NVIDIA_API_KEY),
            "nvidia_model": settings.NVIDIA_MODEL,
            "supabase_configured": bool(
                settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY
            ),
        },
    }


@app.get("/", tags=["system"])
async def root() -> dict:
    """Point callers at the interactive docs."""
    return {"service": "complyx-api", "docs": "/docs", "health": "/health"}


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Complyx API starting in %s mode", settings.APP_ENV)
    if not settings.NVIDIA_API_KEY:
        logger.warning("NVIDIA_API_KEY is not set - extraction will not run")
    if not _tesseract_status()["available"]:
        logger.warning("Tesseract not found - scanned documents cannot be parsed")
