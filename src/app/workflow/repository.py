"""Transactional SQLite repository for Phase 6 state and decisions."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import UUID, uuid4

from app.database import Database
from app.domain import ProposalStatus
from app.workflow.errors import DecisionConflictError, IdempotencyConflictError, ProposalNotFoundError


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def initialize(self) -> None:
        self.database.initialize()

    @staticmethod
    def _event(
        connection: sqlite3.Connection,
        *,
        entity_type: str,
        entity_id: str,
        event_type: str,
        status: str,
        details: dict[str, object] | None = None,
    ) -> None:
        connection.execute(
            "INSERT INTO workflow_events "
            "(entity_type, entity_id, event_type, status, details_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entity_type, entity_id, event_type, status, json.dumps(details or {}, sort_keys=True), utc_now()),
        )

    def create_pending(
        self,
        *,
        request_id: UUID,
        proposal_id: UUID,
        company_name: str,
        contact_name: str,
        contact_email: str,
        requirements: str,
        currency: str,
        total: str,
        docx_path: Path,
        pdf_path: Path,
        review_token_hash: str,
    ) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO workflow_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(request_id), company_name, contact_name, contact_email, requirements, "processing", now, now),
            )
            connection.execute(
                "INSERT INTO workflow_proposals "
                "(proposal_id, request_id, status, currency, total, docx_path, pdf_path, review_token_hash, "
                "error_code, error_message, created_at, updated_at, decided_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, NULL)",
                (str(proposal_id), str(request_id), ProposalStatus.PENDING_APPROVAL, currency, total,
                 str(docx_path), str(pdf_path), review_token_hash, now, now),
            )
            connection.execute(
                "UPDATE workflow_requests SET status = ?, updated_at = ? WHERE request_id = ?",
                ("received", now, str(request_id)),
            )
            self._event(connection, entity_type="request", entity_id=str(request_id), event_type="request_received", status="received")
            self._event(
                connection,
                entity_type="proposal",
                entity_id=str(proposal_id),
                event_type="draft_generated",
                status=ProposalStatus.PENDING_APPROVAL,
                details={"currency": currency, "total": total},
            )
            connection.commit()

    def record_failure(
        self,
        *,
        request_id: UUID,
        proposal_id: UUID,
        company_name: str,
        contact_name: str,
        contact_email: str,
        requirements: str,
        error_code: str,
        error_message: str,
    ) -> None:
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO workflow_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(request_id), company_name, contact_name, contact_email, requirements, "failed", now, now),
            )
            connection.execute(
                "INSERT INTO workflow_proposals "
                "(proposal_id, request_id, status, currency, total, docx_path, pdf_path, review_token_hash, "
                "error_code, error_message, created_at, updated_at, decided_at) "
                "VALUES (?, ?, ?, NULL, NULL, NULL, NULL, NULL, ?, ?, ?, ?, NULL)",
                (str(proposal_id), str(request_id), ProposalStatus.FAILED, error_code, error_message, now, now),
            )
            self._event(connection, entity_type="request", entity_id=str(request_id), event_type="generation_failed", status="failed", details={"error_code": error_code})
            self._event(connection, entity_type="proposal", entity_id=str(proposal_id), event_type="generation_failed", status="failed", details={"error_code": error_code})
            connection.commit()

    def get_proposal(self, proposal_id: UUID | str) -> sqlite3.Row:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM workflow_proposals WHERE proposal_id = ?", (str(proposal_id),)
            ).fetchone()
        if row is None:
            raise ProposalNotFoundError("Proposal was not found")
        return row

    def get_decision_by_key(self, idempotency_key: str) -> sqlite3.Row | None:
        with self.database.connect() as connection:
            return connection.execute(
                "SELECT * FROM manager_decisions WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()

    def decide(
        self,
        *,
        proposal_id: UUID,
        action: str,
        manager_name: str,
        comment: str | None,
        idempotency_key: str,
    ) -> tuple[sqlite3.Row, bool, sqlite3.Row]:
        target_status = ProposalStatus.APPROVED if action == "approve" else ProposalStatus.REJECTED
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM manager_decisions WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if existing is not None:
                if existing["proposal_id"] != str(proposal_id) or existing["action"] != action:
                    connection.rollback()
                    raise IdempotencyConflictError("Idempotency key was already used for another decision")
                proposal = connection.execute(
                    "SELECT * FROM workflow_proposals WHERE proposal_id = ?", (str(proposal_id),)
                ).fetchone()
                connection.rollback()
                return proposal, True, existing

            proposal = connection.execute(
                "SELECT * FROM workflow_proposals WHERE proposal_id = ?", (str(proposal_id),)
            ).fetchone()
            if proposal is None:
                connection.rollback()
                raise ProposalNotFoundError("Proposal was not found")
            if proposal["status"] == target_status:
                prior = connection.execute(
                    "SELECT * FROM manager_decisions WHERE proposal_id = ? AND action = ? ORDER BY created_at LIMIT 1",
                    (str(proposal_id), action),
                ).fetchone()
                connection.rollback()
                return proposal, True, prior
            if proposal["status"] != ProposalStatus.PENDING_APPROVAL:
                connection.rollback()
                raise DecisionConflictError(f"Proposal is already {proposal['status']}")

            decision_id = str(uuid4())
            connection.execute(
                "INSERT INTO manager_decisions VALUES (?, ?, ?, ?, ?, ?, ?)",
                (decision_id, str(proposal_id), action, manager_name, comment, idempotency_key, now),
            )
            connection.execute(
                "UPDATE workflow_proposals SET status = ?, updated_at = ?, decided_at = ? WHERE proposal_id = ?",
                (target_status, now, now, str(proposal_id)),
            )
            self._event(
                connection,
                entity_type="proposal",
                entity_id=str(proposal_id),
                event_type=f"manager_{action}",
                status=target_status,
                details={"decision_id": decision_id, "manager_name": manager_name, "comment": comment},
            )
            connection.commit()
            updated = connection.execute(
                "SELECT * FROM workflow_proposals WHERE proposal_id = ?", (str(proposal_id),)
            ).fetchone()
            decision = connection.execute(
                "SELECT * FROM manager_decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
            return updated, False, decision

    def get_events(self, proposal_id: UUID) -> list[dict[str, Any]]:
        self.get_proposal(proposal_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workflow_events WHERE entity_type = 'proposal' AND entity_id = ? ORDER BY event_id",
                (str(proposal_id),),
            ).fetchall()
        return [dict(row) for row in rows]
