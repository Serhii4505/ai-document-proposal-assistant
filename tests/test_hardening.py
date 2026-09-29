from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.database import Database
from app.proposals.errors import PDFConversionError
from app.workflow.repository import WorkflowRepository
from app.workflow.router import build_workflow_router
from app.workflow.service import WorkflowService
from scripts.security_scan import scan_tree


def _payload() -> dict:
    return {
        "company_name": "Example Manufacturing Ltd",
        "contact_name": "Alex Morgan",
        "contact_email": "alex@example.com",
        "requirements": "We need a controlled customer request automation workflow.",
        "project_title": "Customer Request Automation Implementation",
        "executive_summary": "Northstar Automation proposes a controlled workflow using confirmed requirements.",
        "scope_items": ["Configure validated intake and manager review."],
        "evidence": [{"statement": "The request requires manager review.", "source_id": "request-001", "source_location": "request form"}],
        "requested_services": [{"service_code": "AUTO_SETUP", "quantity": "1"}],
    }


class PartialFailureGenerator:
    def generate(self, data, docx_path: Path, pdf_path: Path):
        del data, pdf_path
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        docx_path.write_bytes(b"partial output")
        raise PDFConversionError("Synthetic conversion failure")


def _client(tmp_path: Path, generator) -> tuple[TestClient, Database, Path]:
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "service_code,service_name,unit,unit_price,minimum_quantity,active,currency\n"
        "AUTO_SETUP,Customer Request Automation,project,1500.00,1,true,EUR\n",
        encoding="utf-8",
    )
    database = Database(tmp_path / "workflow.db")
    repository = WorkflowRepository(database)
    repository.initialize()
    output = tmp_path / "output"
    service = WorkflowService(
        repository=repository,
        catalog_path=catalog,
        output_dir=output,
        vat_rate=Decimal("0.23"),
        discount_threshold=Decimal("3000.00"),
        discount_rate=Decimal("0.10"),
        generator=generator,
    )
    app = FastAPI()
    app.include_router(build_workflow_router(service))
    return TestClient(app), database, output


def test_failed_generation_removes_partial_artifacts_and_records_failure(tmp_path: Path) -> None:
    client, database, output = _client(tmp_path, PartialFailureGenerator())

    response = client.post("/api/v1/requests", json=_payload())

    assert response.status_code == 422
    assert not list(output.glob("*/proposal-draft.docx"))
    with database.connect() as connection:
        proposal = connection.execute("SELECT status, error_code FROM workflow_proposals").fetchone()
        decisions = connection.execute("SELECT COUNT(*) AS count FROM manager_decisions").fetchone()["count"]
    assert dict(proposal) == {"status": "failed", "error_code": "pdf_conversion_failed"}
    assert decisions == 0


def test_public_project_tree_passes_security_scan() -> None:
    root = Path(__file__).parents[1]
    assert scan_tree(root) == []


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        ("leak.env", "CLIENT_" + "SECRET=actual-secret-value-1234567890", "possible assigned secret"),
        ("notes.txt", "Contact manager" + "@real-company.test", "non-demo email address"),
    ],
)
def test_security_scan_detects_unsafe_public_content(tmp_path: Path, filename: str, content: str, expected: str) -> None:
    (tmp_path / filename).write_text(content, encoding="utf-8")
    assert any(expected in finding for finding in scan_tree(tmp_path))
