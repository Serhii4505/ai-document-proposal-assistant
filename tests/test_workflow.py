from decimal import Decimal
import json
from pathlib import Path
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.database import Database
from app.workflow.repository import WorkflowRepository
from app.workflow.router import build_workflow_router
from app.workflow.service import WorkflowService


class FakeGenerator:
    def generate(self, data, docx_path: Path, pdf_path: Path):
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        docx_path.write_bytes(b"PK\x03\x04synthetic-docx")
        pdf_path.write_bytes(b"%PDF-1.4 synthetic-pdf")
        return docx_path, pdf_path


@pytest.fixture()
def workflow(tmp_path: Path):
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "service_code,service_name,unit,unit_price,minimum_quantity,active,currency\n"
        "AUTO_SETUP,Customer Request Automation,project,1500.00,1,true,EUR\n"
        "TRAINING,Staff Training,session,250.00,1,true,EUR\n",
        encoding="utf-8",
    )
    database = Database(tmp_path / "workflow.db")
    repository = WorkflowRepository(database)
    repository.initialize()
    service = WorkflowService(
        repository=repository,
        catalog_path=catalog,
        output_dir=tmp_path / "output",
        vat_rate=Decimal("0.23"),
        discount_threshold=Decimal("3000.00"),
        discount_rate=Decimal("0.10"),
        generator=FakeGenerator(),
    )
    app = FastAPI()
    app.include_router(build_workflow_router(service))
    return TestClient(app), repository, database


def payload(service_code: str = "AUTO_SETUP") -> dict:
    return {
        "company_name": "Example Manufacturing Ltd",
        "contact_name": "Alex Morgan",
        "contact_email": "alex@example.com",
        "requirements": "We need a controlled customer request automation workflow.",
        "project_title": "Customer Request Automation Implementation",
        "executive_summary": "Northstar Automation proposes a controlled workflow based only on confirmed requirements.",
        "scope_items": ["Configure validated request intake and manager review."],
        "evidence": [{"statement": "The client requested a controlled request workflow.", "source_id": "request-001", "source_location": "request form"}],
        "requested_services": [{"service_code": service_code, "quantity": "1"}],
    }


def create(client: TestClient) -> dict:
    response = client.post("/api/v1/requests", json=payload())
    assert response.status_code == 201, response.text
    return response.json()


def test_created_proposal_is_pending_and_not_finalizable(workflow):
    client, _, _ = workflow
    created = create(client)
    assert created["status"] == "pending_approval"
    status = client.get(f"/api/v1/proposals/{created['proposal_id']}").json()
    assert status["status"] == "pending_approval"
    assert status["can_finalize"] is False
    assert status["client_delivery_enabled"] is False


def test_review_token_is_hashed_and_controls_draft_download(workflow):
    client, _, database = workflow
    created = create(client)
    with database.connect() as connection:
        row = connection.execute("SELECT review_token_hash FROM workflow_proposals").fetchone()
    assert row["review_token_hash"] != created["review_token"]
    assert len(row["review_token_hash"]) == 64
    denied = client.get(f"/api/v1/proposals/{created['proposal_id']}/draft.pdf", params={"review_token": "x" * 32})
    assert denied.status_code == 403
    allowed = client.get(f"/api/v1/proposals/{created['proposal_id']}/draft.pdf", params={"review_token": created["review_token"]})
    assert allowed.status_code == 200
    assert allowed.content.startswith(b"%PDF")


def test_approve_is_idempotent_and_creates_one_decision(workflow):
    client, _, database = workflow
    created = create(client)
    body = {"review_token": created["review_token"], "manager_name": "Demo Manager", "comment": "Approved", "idempotency_key": "approval-001"}
    first = client.post(f"/api/v1/proposals/{created['proposal_id']}/approve", json=body)
    second = client.post(f"/api/v1/proposals/{created['proposal_id']}/approve", json=body)
    third = client.post(f"/api/v1/proposals/{created['proposal_id']}/approve", json={**body, "idempotency_key": "approval-002"})
    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json()["idempotent_replay"] is False
    assert second.json()["idempotent_replay"] is True
    assert third.json()["idempotent_replay"] is True
    assert third.json()["can_finalize"] is True
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) AS count FROM manager_decisions").fetchone()["count"] == 1
        assert connection.execute("SELECT COUNT(*) AS count FROM workflow_events WHERE event_type = 'manager_approve'").fetchone()["count"] == 1


def test_opposite_decision_and_reused_key_are_conflicts(workflow):
    client, _, _ = workflow
    one = create(client)
    approval = {"review_token": one["review_token"], "manager_name": "Demo Manager", "idempotency_key": "shared-key-001"}
    assert client.post(f"/api/v1/proposals/{one['proposal_id']}/approve", json=approval).status_code == 200
    rejected = client.post(f"/api/v1/proposals/{one['proposal_id']}/reject", json={**approval, "comment": "Changed mind", "idempotency_key": "reject-001"})
    assert rejected.status_code == 409

    two = create(client)
    reused = client.post(f"/api/v1/proposals/{two['proposal_id']}/approve", json={**approval, "review_token": two["review_token"]})
    assert reused.status_code == 409


def test_rejection_requires_comment_and_is_finalization_blocked(workflow):
    client, _, _ = workflow
    created = create(client)
    missing = client.post(f"/api/v1/proposals/{created['proposal_id']}/reject", json={"review_token": created["review_token"], "manager_name": "Demo Manager", "idempotency_key": "reject-002"})
    assert missing.status_code == 422
    valid = client.post(f"/api/v1/proposals/{created['proposal_id']}/reject", json={"review_token": created["review_token"], "manager_name": "Demo Manager", "comment": "Please revise the scope", "idempotency_key": "reject-003"})
    assert valid.status_code == 200
    assert valid.json()["status"] == "rejected"
    assert valid.json()["can_finalize"] is False

    approval_after_rejection = client.post(
        f"/api/v1/proposals/{created['proposal_id']}/approve",
        json={
            "review_token": created["review_token"],
            "manager_name": "Demo Manager",
            "comment": "Attempted reversal",
            "idempotency_key": "approve-after-reject-001",
        },
    )
    assert approval_after_rejection.status_code == 409
    assert approval_after_rejection.json()["detail"]["code"] == "decision_conflict"


def test_failure_is_audited_and_never_creates_pending_or_approved_record(workflow):
    client, _, database = workflow
    response = client.post("/api/v1/requests", json=payload("UNKNOWN_SERVICE"))
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Unknown service code: UNKNOWN_SERVICE"
    with database.connect() as connection:
        proposal = connection.execute("SELECT * FROM workflow_proposals").fetchone()
        events = connection.execute("SELECT event_type, status FROM workflow_events ORDER BY event_id").fetchall()
    assert proposal["status"] == "failed"
    assert proposal["error_code"] == "unknownserviceerror"
    assert [(row["event_type"], row["status"]) for row in events] == [("generation_failed", "failed"), ("generation_failed", "failed")]


def test_audit_endpoint_requires_token_and_returns_decision(workflow):
    client, _, _ = workflow
    created = create(client)
    client.post(f"/api/v1/proposals/{created['proposal_id']}/approve", json={"review_token": created["review_token"], "manager_name": "Demo Manager", "idempotency_key": "audit-approve-001"})
    denied = client.get(f"/api/v1/proposals/{created['proposal_id']}/events", params={"review_token": "z" * 32})
    allowed = client.get(f"/api/v1/proposals/{created['proposal_id']}/events", params={"review_token": created["review_token"]})
    assert denied.status_code == 403
    assert [event["event_type"] for event in allowed.json()] == ["draft_generated", "manager_approve"]


def test_n8n_export_has_no_credentials_secrets_or_client_delivery_node():
    path = Path(__file__).parents[1] / "n8n" / "phase-6-manager-approval.workflow.json"
    workflow = json.loads(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    assert workflow["active"] is False
    assert "credentials" not in text
    assert "GEMINI_API_KEY" not in text
    assert "@gmail.com" not in text
    assert "@example.com" not in text
    assert "$env.FASTAPI_BASE_URL" in text
    assert "$env.MANAGER_EMAIL" in text
    assert all("client" not in node["name"].casefold() for node in workflow["nodes"])
