"""Manager-controlled proposal workflow."""

from app.workflow.router import build_workflow_router
from app.workflow.service import WorkflowService

__all__ = ["WorkflowService", "build_workflow_router"]
