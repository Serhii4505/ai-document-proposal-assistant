"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from app.config import get_settings
from app.database import Database
from app.domain import HealthResponse
from app.workflow import WorkflowService, build_workflow_router
from app.workflow.repository import WorkflowRepository


settings = get_settings()
database = Database(settings.database_path)
workflow_repository = WorkflowRepository(database)
workflow_service = WorkflowService(
    repository=workflow_repository,
    catalog_path=settings.service_catalog_path,
    output_dir=settings.proposal_output_dir,
    vat_rate=settings.vat_rate,
    discount_threshold=settings.volume_discount_threshold,
    discount_rate=settings.volume_discount_rate,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-assisted commercial proposal workflow with deterministic pricing.",
    lifespan=lifespan,
)
app.include_router(build_workflow_router(workflow_service))


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Verify that the API and its SQLite database are operational."""

    if not database.healthcheck():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database health check failed",
        )

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database="ok",
    )
