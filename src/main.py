"""Main application entry point for Elastic RAG."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api import documents, health, query
from src.api.exceptions import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from src.config.settings import get_settings
from src.resilience.health_probes import HealthProbes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("🚀 Starting Elastic RAG API...")
    logger.info(f"📦 Version: {__version__}")

    settings = get_settings()
    logger.info(f"🌍 Environment: {settings.app.environment}")
    logger.info(f"📝 Log level: {settings.app.log_level}")

    # Perform startup health check
    health_probes = HealthProbes()
    startup_result = await health_probes.startup()

    if startup_result["status"] != "healthy":
        logger.error("⚠️  Startup health check failed!")
        logger.error(f"Details: {startup_result}")
    else:
        logger.info("✅ Startup health check passed")

    yield

    # Shutdown
    logger.info("👋 Shutting down Elastic RAG API...")


# Create FastAPI application
app = FastAPI(
    title="Elastic RAG API",
    description="A containerized RAG system using Elasticsearch and Google ADK with stateless agent architecture",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Configure appropriately for production (e.g., ["http://localhost:7860"] for UI)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their response times."""
    start_time = time.time()

    # Log request
    logger.info(
        f"Incoming request: {request.method} {request.url.path} "
        f"- Client: {request.client.host if request.client else 'unknown'}"
    )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Duration: {duration:.3f}s"
    )

    return response


# Register exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Register routers
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(query.router)

logger.info("✅ Routers registered: health, documents, query")


@app.get("/")
async def root() -> dict[str, str | dict[str, str]]:
    """Root endpoint with API information.

    Returns basic information about the API and links to
    documentation and key endpoints.

    Returns:
        Dictionary with API information:
            - name: API name
            - version: Current version
            - status: Running status
            - docs: Link to Swagger documentation
            - endpoints: Key endpoint paths
    """
    return {
        "name": "Elastic RAG API",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health/live, /health/ready, /health/startup",
            "upload": "/documents/upload",
            "batch_upload": "/documents/upload/batch",
            "query": "/query/",
            "batch_query": "/query/batch",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
