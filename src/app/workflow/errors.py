"""Explicit workflow errors suitable for API responses."""


class WorkflowError(RuntimeError):
    code = "workflow_error"


class ProposalNotFoundError(WorkflowError):
    code = "proposal_not_found"


class InvalidReviewTokenError(WorkflowError):
    code = "invalid_review_token"


class DecisionConflictError(WorkflowError):
    code = "decision_conflict"


class IdempotencyConflictError(WorkflowError):
    code = "idempotency_conflict"


class DraftUnavailableError(WorkflowError):
    code = "draft_unavailable"
